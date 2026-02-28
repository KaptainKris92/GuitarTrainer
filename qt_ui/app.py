import threading

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from functions.get_device_list import DeviceLister
from functions.note_trainer import NoteTrainer
from functions.sql_funcs import (
    create_incorrect_bar_chart,
    get_best_score,
    get_current_game_id,
    get_highscores,
    get_trial_time_combos,
    insert_final_score,
    insert_trial,
)
from tuner_utils.audio_analyser import AudioAnalyser
from tuner_utils.settings import Settings
from tuner_utils.threading_helper import ProtectedList


CHROMATIC_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_TO_SHARP = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
FRETBOARD_STRING_NOTES = ["E", "B", "G", "D", "A", "E"]  # Top to bottom (high E to low E)


# Convert the selected device combo text into the numeric device index.
def parse_device_id(text: str) -> int:
    return int(text.split(" - ", 1)[0].replace("Input Device ", "").strip())


def normalise_note_name(note: str):
    """Normalise user-entered note text to sharp-based chromatic notation."""
    raw = (note or "").strip()
    if not raw:
        return None
    n = raw.upper().replace("♯", "#").replace("♭", "B")
    if n in FLAT_TO_SHARP:
        return FLAT_TO_SHARP[n]
    return n if n in CHROMATIC_SHARPS else None


def note_at_fret(open_note: str, fret: int):
    """Return the note name at a given fret for a specific open string note."""
    idx = CHROMATIC_SHARPS.index(open_note)
    return CHROMATIC_SHARPS[(idx + fret) % 12]


# Background worker for note-trainer gameplay so the UI thread stays responsive.
class NoteTrainerWorker(QThread):
    """Run note-trainer gameplay off the UI thread and emit progress events."""
    trial_start = Signal(str, str, str, int, int)  # string, low_high, note, trial_idx, total
    trial_result = Signal(bool)
    game_complete = Signal(int, int, str, bool)  # num_correct, trials_attempted, best_score, cancelled
    game_error = Signal(str)

    def __init__(self, input_device: int, time_per_guess: int, total_trials: int):
        """Store game configuration and initialise a cancellation event."""
        super().__init__()
        self.input_device = input_device
        self.time_per_guess = time_per_guess
        self.total_trials = total_trials
        self.cancel_event = threading.Event()

    def request_cancel(self):
        """Signal the worker loop to stop after the current safe checkpoint."""
        self.cancel_event.set()

    def run(self):
        """Execute the trial loop and persist per-trial/final score data."""
        trainer = NoteTrainer(self.input_device)
        num_correct = 0
        trials_attempted = 0
        game_id = get_current_game_id()
        try:
            for i in range(self.total_trials):
                if self.cancel_event.is_set():
                    break

                target = trainer.random_note()
                self.trial_start.emit(
                    target["string"],
                    target["low_high"],
                    target["note"],
                    i + 1,
                    self.total_trials,
                )

                result = trainer.play_game(
                    self.time_per_guess,
                    string=target["string"],
                    low_high=target["low_high"],
                    note=target["note"],
                    stop_event=self.cancel_event,
                )
                if result.get("cancelled"):
                    break

                is_correct = result["correct"] is True
                if is_correct:
                    num_correct += 1
                trials_attempted += 1

                insert_trial(
                    game_id,
                    self.time_per_guess,
                    self.total_trials,
                    i + 1,
                    result["string"],
                    result["low_high"],
                    result["note"],
                    result["played_note"],
                    is_correct,
                )
                self.trial_result.emit(is_correct)

            if trials_attempted > 0:
                best = get_best_score(self.time_per_guess, trials_attempted, num_correct)
                insert_final_score(game_id, self.time_per_guess, trials_attempted, num_correct)
            else:
                best = "No trials completed."

            self.game_complete.emit(num_correct, trials_attempted, best, self.cancel_event.is_set())
        except Exception as exc:
            self.game_error.emit(str(exc))


class TunerWindow(QMainWindow):
    """Live guitar tuner window backed by the audio analyser thread."""
    closed = Signal()

    def __init__(self, input_device: int):
        """Initialise analyser state, build the UI and start polling updates."""
        super().__init__()
        self.setWindowTitle("Guitar Trainer: Tuner")
        self.resize(1080, 720)

        self.frequency_queue = ProtectedList()
        self.audio_analyser = AudioAnalyser(queue=self.frequency_queue, device_index=input_device)
        self.audio_analyser.start()

        self.nearest_note_number_buffered = 69
        self.note_number_counter = 0
        self.a4_frequency = 440
        self.tone_hit_counter = 0
        self.in_tune_threshold_cents = 5.0

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_frequency_queue)
        self.timer.start(max(20, Settings.GUI_UPDATE_INTERVAL_MS))

    def _build_ui(self):
        # Main tuner layout: title + central card with live pitch readout and guidance.
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Guitar Tuner")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.DemiBold))
        layout.addWidget(title)

        subtitle = QLabel("Play one string at a time and center the meter.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        self.note_label = QLabel("A")
        self.note_label.setObjectName("tunerDetectedNote")
        self.note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_label.setFont(QFont("Segoe UI", 128, QFont.Weight.ExtraBold))
        card_layout.addWidget(self.note_label)

        self.freq_label = QLabel("Detected frequency: -- Hz")
        self.freq_label.setObjectName("tunerFrequency")
        self.freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.freq_label.setFont(QFont("Segoe UI", 26, QFont.Weight.DemiBold))
        card_layout.addWidget(self.freq_label)

        self.cents_label = QLabel("0.0 cents")
        self.cents_label.setObjectName("tunerCents")
        self.cents_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cents_label.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        card_layout.addWidget(self.cents_label)

        direction_row = QHBoxLayout()
        direction_row.setSpacing(16)
        self.tune_down_label = QLabel("<< Tune Down")
        self.tune_down_label.setObjectName("tuneHint")
        self.in_tune_label = QLabel("IN TUNE")
        self.in_tune_label.setObjectName("inTuneOff")
        self.tune_up_label = QLabel("Tune Up >>")
        self.tune_up_label.setObjectName("tuneHint")
        direction_row.addWidget(self.tune_down_label)
        direction_row.addStretch(1)
        direction_row.addWidget(self.in_tune_label)
        direction_row.addStretch(1)
        direction_row.addWidget(self.tune_up_label)
        card_layout.addLayout(direction_row)

        self.cents_bar = QProgressBar()
        self.cents_bar.setRange(-50, 50)
        self.cents_bar.setValue(0)
        self.cents_bar.setTextVisible(False)
        self.cents_bar.setFixedHeight(14)
        card_layout.addWidget(self.cents_bar)

        layout.addWidget(card, stretch=1)

    def poll_frequency_queue(self):
        # Pull latest detected frequency and update visual tuning state.
        freq = self.frequency_queue.get()
        if freq is None:
            return

        number = self.audio_analyser.frequency_to_number(freq, self.a4_frequency)
        nearest_note_number = round(number)
        nearest_note_freq = self.audio_analyser.number_to_frequency(nearest_note_number, self.a4_frequency)
        freq_difference = nearest_note_freq - freq
        semitone_step = nearest_note_freq - self.audio_analyser.number_to_frequency(round(number - 1), self.a4_frequency)

        if nearest_note_number != self.nearest_note_number_buffered:
            self.note_number_counter += 1
            if self.note_number_counter >= Settings.HITS_TILL_NOTE_NUMBER_UPDATE:
                self.nearest_note_number_buffered = nearest_note_number
                self.note_number_counter = 0

        diff_cents = (freq_difference / semitone_step) * 100 if semitone_step else 0
        display_cents = round(-diff_cents, 1)
        self.note_label.setText(self.audio_analyser.number_to_note_name(self.nearest_note_number_buffered))
        self.freq_label.setText(f"Detected frequency: {round(freq, 1)} Hz")
        self.cents_label.setText(f"{display_cents:+} cents")
        self.cents_bar.setValue(int(max(-50, min(50, display_cents))))

        in_tune = abs(display_cents) <= self.in_tune_threshold_cents
        is_sharp = display_cents > self.in_tune_threshold_cents
        is_flat = display_cents < -self.in_tune_threshold_cents

        self.in_tune_label.setObjectName("inTuneOn" if in_tune else "inTuneOff")
        self.tune_down_label.setObjectName("tuneHintActive" if is_sharp else "tuneHint")
        self.tune_up_label.setObjectName("tuneHintActive" if is_flat else "tuneHint")

        self.in_tune_label.style().unpolish(self.in_tune_label)
        self.in_tune_label.style().polish(self.in_tune_label)
        self.tune_down_label.style().unpolish(self.tune_down_label)
        self.tune_down_label.style().polish(self.tune_down_label)
        self.tune_up_label.style().unpolish(self.tune_up_label)
        self.tune_up_label.style().polish(self.tune_up_label)

    def closeEvent(self, event: QCloseEvent):
        """Stop timers/threads cleanly before the tuner window closes."""
        if hasattr(self, "timer") and self.timer is not None:
            self.timer.stop()
        if hasattr(self, "audio_analyser") and self.audio_analyser is not None:
            self.audio_analyser.running = False
            self.audio_analyser.join()
        self.closed.emit()
        super().closeEvent(event)


class HighScoresWindow(QMainWindow):
    """Display stored note-trainer high scores for selected game settings."""
    def __init__(self):
        """Load score setting combinations and build the high-score table UI."""
        super().__init__()
        self.setWindowTitle("Note Trainer: High Scores")
        self.resize(900, 620)
        self.past_combos = get_trial_time_combos()
        self._build_ui()

    def _build_ui(self):
        # High-score table for historical game results.
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("High Scores")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.DemiBold))
        layout.addWidget(title)

        self.combo = QComboBox()
        self.combo.addItems([f"Trials: {x[0]} | Time per trial: {x[1]}" for x in self.past_combos])
        self.combo.currentIndexChanged.connect(self.reload_table)
        layout.addWidget(self.combo)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Date", "Game ID", "# Correct"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        self.info = QLabel("")
        self.info.setObjectName("muted")
        layout.addWidget(self.info)

        if self.past_combos:
            self.reload_table()
        else:
            self.combo.setEnabled(False)
            self.info.setText("No scores recorded yet.")

    def reload_table(self):
        """Refresh table rows for the currently selected trial/time combination."""
        if not self.past_combos:
            return
        trials, time_per_guess = self.past_combos[self.combo.currentIndex()]
        rows = get_highscores(trials, time_per_guess)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row[0].strftime("%Y/%m/%d %H:%M")))
            self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row[4])))
        self.info.setText(f"Showing {len(rows)} game(s).")


class MissedNotesWindow(QMainWindow):
    """Display a chart of the most frequently missed target notes."""
    def __init__(self):
        """Create the missed-notes window and render the initial chart."""
        super().__init__()
        self.setWindowTitle("Note Trainer: Missed Notes")
        self.resize(980, 680)
        self._build_ui()

    def _build_ui(self):
        # Matplotlib view showing most frequently missed notes.
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Most Missed Notes")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.DemiBold))
        layout.addWidget(title)

        controls = QHBoxLayout()
        top_label = QLabel("Top")
        top_label.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        controls.addWidget(top_label)
        self.top_n = QSpinBox()
        self.top_n.setObjectName("topNSpin")
        self.top_n.setRange(1, 20)
        self.top_n.setValue(10)
        self.top_n.setMinimumWidth(88)
        self.top_n.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        self.top_n.valueChanged.connect(self.replot)
        controls.addWidget(self.top_n)
        tail_label = QLabel("missed notes")
        tail_label.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        controls.addWidget(tail_label)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.figure = create_incorrect_bar_chart(10)
        self._style_chart(self.figure)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        layout.addWidget(self.canvas, stretch=1)

    def replot(self):
        """Recreate and restyle the chart when the top-N value changes."""
        self.canvas.setParent(None)
        self.figure = create_incorrect_bar_chart(self.top_n.value())
        self._style_chart(self.figure)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.centralWidget().layout().addWidget(self.canvas, stretch=1)

    def _style_chart(self, fig):
        # Restyle matplotlib output to match the app's dark palette.
        fig.patch.set_facecolor("#1b2430")
        fig.patch.set_edgecolor("#1b2430")
        if not fig.axes:
            return
        ax = fig.axes[0]
        ax.set_facecolor("#1b2430")
        ax.tick_params(colors="#d3dfeb")
        ax.xaxis.label.set_color("#d3dfeb")
        ax.yaxis.label.set_color("#d3dfeb")
        ax.xaxis.grid(True, color="#2e3f55", alpha=0.35, linestyle="-", linewidth=0.6)
        ax.yaxis.grid(False)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for bar in ax.patches:
            bar.set_facecolor("#2f81f7")
            bar.set_edgecolor("#2f81f7")


class NoteTrainerWindow(QMainWindow):
    """Interactive note-trainer session window with threaded gameplay."""
    closed = Signal()

    def __init__(self, input_device: int):
        """Store selected input device and set up note-trainer controls."""
        super().__init__()
        self.setWindowTitle("Guitar Trainer: Note Trainer")
        self.resize(1080, 720)
        self.input_device = input_device
        self.worker = None
        self.progress_markers = []
        self.trial_index = 0
        self._build_ui()

    def _build_ui(self):
        # Two-column note-trainer layout: controls on left, live prompt/progress on right.
        root = QWidget()
        self.setCentralWidget(root)
        layout = QGridLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 3)
        layout.setRowStretch(1, 1)

        title = QLabel("Note Trainer")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.DemiBold))
        layout.addWidget(title, 0, 0, 1, 2)

        left = QFrame()
        left.setObjectName("card")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)
        layout.addWidget(left, 1, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Time per trial (seconds)"))
        self.time_per_guess = QSpinBox()
        self.time_per_guess.setRange(1, 30)
        self.time_per_guess.setValue(1)
        row1.addWidget(self.time_per_guess)
        row1.addStretch(1)
        left_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Total trials"))
        self.total_trials = QSpinBox()
        self.total_trials.setRange(1, 100)
        self.total_trials.setValue(10)
        row2.addWidget(self.total_trials)
        row2.addStretch(1)
        left_layout.addLayout(row2)

        self.start_btn = QPushButton("Start Session")
        self.start_btn.clicked.connect(self.start_session)
        left_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel Session")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_session)
        left_layout.addWidget(self.cancel_btn)

        stats_row = QHBoxLayout()
        self.high_btn = QPushButton("High Scores")
        self.high_btn.clicked.connect(self.open_high_scores)
        self.missed_btn = QPushButton("Missed Notes")
        self.missed_btn.clicked.connect(self.open_missed_notes)
        stats_row.addWidget(self.high_btn)
        stats_row.addWidget(self.missed_btn)
        left_layout.addLayout(stats_row)

        self.status = QLabel("Configure your session and press Start Session.")
        self.status.setObjectName("muted")
        left_layout.addWidget(self.status)
        left_layout.addStretch(1)

        right = QFrame()
        right.setObjectName("card")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(14)
        layout.addWidget(right, 1, 1)

        prompt_row = QHBoxLayout()
        self.string_label = QLabel("String")
        self.string_label.setObjectName("trainerPrompt")
        self.low_high_label = QLabel("Position")
        self.low_high_label.setObjectName("trainerPrompt")
        self.note_label = QLabel("Note")
        self.note_label.setObjectName("trainerPrompt")
        for w in (self.string_label, self.low_high_label, self.note_label):
            w.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
            prompt_row.addWidget(w)
        prompt_row.addStretch(1)
        right_layout.addLayout(prompt_row)

        self.progress_row = QHBoxLayout()
        self.progress_row.setSpacing(8)
        right_layout.addLayout(self.progress_row)
        right_layout.addStretch(1)

    def set_busy(self, busy: bool):
        """Toggle controls to prevent conflicting actions while a session runs."""
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.high_btn.setEnabled(not busy)
        self.missed_btn.setEnabled(not busy)
        self.time_per_guess.setEnabled(not busy)
        self.total_trials.setEnabled(not busy)

    def _clear_progress(self):
        """Remove all progress markers from the current session row."""
        while self.progress_row.count():
            item = self.progress_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.progress_markers = []

    def _setup_progress(self, total_trials: int):
        # Create one progress marker per trial (empty state).
        self._clear_progress()
        self.trial_index = 0
        for _ in range(total_trials):
            marker = QLabel("")
            marker.setFixedSize(20, 20)
            marker.setStyleSheet(
                "background: #223244; border: 2px solid #8aa0b6; border-radius: 10px;"
            )
            self.progress_row.addWidget(marker)
            self.progress_markers.append(marker)
        self.progress_row.addStretch(1)

    def start_session(self):
        """Create and start a worker thread for a new trainer session."""
        if self.worker is not None and self.worker.isRunning():
            return

        time_per_guess = self.time_per_guess.value()
        total_trials = self.total_trials.value()
        self._setup_progress(total_trials)
        self.set_busy(True)
        self.status.setText("Session in progress...")

        self.worker = NoteTrainerWorker(self.input_device, time_per_guess, total_trials)
        self.worker.trial_start.connect(self.on_trial_start)
        self.worker.trial_result.connect(self.on_trial_result)
        self.worker.game_complete.connect(self.on_game_complete)
        self.worker.game_error.connect(self.on_game_error)
        self.worker.start()

    def cancel_session(self):
        """Request cancellation and disable repeated cancel clicks."""
        if self.worker is None or not self.worker.isRunning():
            return
        self.worker.request_cancel()
        self.cancel_btn.setEnabled(False)
        self.status.setText("Cancelling after current trial...")

    def on_trial_start(self, string: str, low_high: str, note: str, trial_idx: int, total: int):
        """Update prompt labels when a new trial begins."""
        display_note = note.replace("â™¯", "#").replace("â™­", "b").replace("♯", "#").replace("♭", "b")
        self.string_label.setText(f"{string} string")
        self.low_high_label.setText(low_high)
        self.note_label.setText(display_note)
        self.status.setText(f"Trial {trial_idx}/{total} in progress...")

    def on_trial_result(self, is_correct: bool):
        # Fill marker green/red based on trial outcome.
        if self.trial_index < len(self.progress_markers):
            color = "#2aa36b" if is_correct else "#cc4b4b"
            self.progress_markers[self.trial_index].setStyleSheet(
                f"background: {color}; border: 2px solid {color}; border-radius: 10px;"
            )
        self.trial_index += 1

    def on_game_complete(self, num_correct: int, trials_attempted: int, best_score: str, cancelled: bool):
        """Display end-of-session summary and restore interactive controls."""
        if trials_attempted > 0:
            self.string_label.setText("Session complete")
            self.low_high_label.setText(f"{num_correct}/{trials_attempted} correct")
            self.note_label.setText(best_score)
        self.status.setText("Session cancelled." if cancelled else "Session complete.")
        self.set_busy(False)

    def on_game_error(self, message: str):
        """Surface worker errors in the status area and unlock controls."""
        self.status.setText(f"Session failed: {message}")
        self.set_busy(False)

    def open_high_scores(self):
        """Open the high-score history window."""
        self.hs = HighScoresWindow()
        self.hs.show()

    def open_missed_notes(self):
        """Open the missed-notes chart window."""
        self.mn = MissedNotesWindow()
        self.mn.show()

    def closeEvent(self, event: QCloseEvent):
        """Attempt graceful worker shutdown before closing the window."""
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait(3000)
        self.closed.emit()
        super().closeEvent(event)


class FretboardGrid(QFrame):
    """Render a 6x12 fretboard grid showing either notes or scale degrees."""
    def __init__(self, scale_notes, degree_by_note, display_mode: str):
        """Capture scale data and render the requested fretboard mode."""
        super().__init__()
        self.scale_notes = set(scale_notes)
        self.degree_by_note = degree_by_note
        self.display_mode = display_mode  # "note" or "degree"
        self._build_ui()

    def _build_ui(self):
        """Build fretboard cells, open-string labels, and highlighted markers."""
        self.setObjectName("fretboardCard")
        layout = QGridLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)

        title = QLabel("Note Positions" if self.display_mode == "note" else "Scale Degrees")
        title.setObjectName("fretboardTitle")
        layout.addWidget(title, 0, 0, 1, 14)

        # Fret numbers row (1..12), with left-most column reserved for open strings.
        for fret in range(1, 13):
            fret_label = QLabel(str(fret))
            fret_label.setObjectName("fretNum")
            fret_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fret_label, 1, fret, 1, 1)

        for row, open_note in enumerate(FRETBOARD_STRING_NOTES, start=2):
            # Open-string marker at fret 0.
            open_marker = QLabel(open_note)
            open_marker.setObjectName("openString")
            open_marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(open_marker, row, 0, 1, 1)

            for fret in range(1, 13):
                note = note_at_fret(open_note, fret)

                cell = QFrame()
                cell.setObjectName("fretCell")
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if note in self.scale_notes:
                    text = note if self.display_mode == "note" else self.degree_by_note[note]
                    marker = QLabel(text)
                    marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    marker.setObjectName("fretMarkerRoot" if self.degree_by_note[note] == "1" else "fretMarker")
                    cell_layout.addWidget(marker)

                layout.addWidget(cell, row, fret, 1, 1)


class ScaleFretboardWindow(QMainWindow):
    """Show stacked fretboard diagrams for notes and corresponding degrees."""
    def __init__(self, scale_name: str, scale_notes):
        """Create a titled fretboard window from a normalised note sequence."""
        super().__init__()
        self.scale_name = scale_name
        self.scale_notes = scale_notes
        self.degree_by_note = {note: str(i + 1) for i, note in enumerate(self.scale_notes)}
        self.setWindowTitle(f"Scale Fretboard: {self.scale_name}")
        self.resize(1100, 720)
        self._build_ui()

    def _build_ui(self):
        """Compose the title, note summary, and two fretboard diagrams."""
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(self.scale_name)
        title.setObjectName("scaleTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"Notes: {', '.join(self.scale_notes)}")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        layout.addWidget(FretboardGrid(self.scale_notes, self.degree_by_note, "note"))
        layout.addWidget(FretboardGrid(self.scale_notes, self.degree_by_note, "degree"))


class ScaleWorkbenchWindow(QMainWindow):
    """PoC workbench for entering custom scales and opening diagram windows."""
    def __init__(self):
        """Initialise controls used to define and open scale fretboards."""
        super().__init__()
        self.setWindowTitle("Scale Notation to Fretboard (PoC)")
        self.resize(760, 300)
        self.fretboard_windows = []
        self._build_ui()

    def _build_ui(self):
        """Build input form and launch action for fretboard windows."""
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Scale Notation to Fretboard")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.DemiBold))
        layout.addWidget(title)

        subtitle = QLabel(
            "Enter scale notes as a comma-separated list (e.g. A, B, C, D, E, F, G). "
            "Each click opens a separate fretboard window."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QGridLayout()
        form.addWidget(QLabel("Scale name"), 0, 0)
        self.scale_name_input = QLineEdit("A Natural Minor")
        form.addWidget(self.scale_name_input, 0, 1)

        form.addWidget(QLabel("Scale notes"), 1, 0)
        self.scale_notes_input = QLineEdit("A, B, C, D, E, F, G")
        form.addWidget(self.scale_notes_input, 1, 1)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open Fretboard Window")
        self.open_btn.clicked.connect(self.open_fretboard_window)
        actions.addWidget(self.open_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.status = QLabel("Ready.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)

    def open_fretboard_window(self):
        """Parse/validate input notes and open a new independent fretboard view."""
        raw_notes = [part.strip() for part in self.scale_notes_input.text().split(",") if part.strip()]
        if not raw_notes:
            self.status.setText("Enter at least one note.")
            return

        normalised = []
        for item in raw_notes:
            n = normalise_note_name(item)
            if n is None:
                self.status.setText(f"Invalid note: {item}")
                return
            if n not in normalised:
                normalised.append(n)

        if not normalised:
            self.status.setText("No valid notes were provided.")
            return

        name = self.scale_name_input.text().strip() or "Custom Scale"
        window = ScaleFretboardWindow(name, normalised)
        window.show()
        self.fretboard_windows.append(window)
        self.status.setText(f"Opened fretboard window: {name}")


class MainWindow(QMainWindow):
    """Application landing window with mode launchers and device selection."""
    def __init__(self):
        """Initialise app-level windows, then build and populate the main view."""
        super().__init__()
        self.setWindowTitle("Guitar Trainer")
        self.resize(1080, 720)
        self.setMinimumSize(940, 620)
        self.device_lister = DeviceLister()
        self.tuner_window = None
        self.note_window = None
        self.scale_window = None
        self._build_ui()
        self.refresh_devices()

    def _build_ui(self):
        # Main landing page with audio-device selection and mode launch buttons.
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Guitar Trainer")
        title.setFont(QFont("Segoe UI", 30, QFont.Weight.DemiBold))
        layout.addWidget(title)

        subtitle = QLabel("Tune accurately and train fretboard recall with guided trials.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        device_card = QFrame()
        device_card.setObjectName("card")
        dlay = QGridLayout(device_card)
        dlay.setContentsMargins(14, 14, 14, 14)
        dlay.setHorizontalSpacing(8)
        layout.addWidget(device_card)

        dlay.addWidget(QLabel("Audio input"), 0, 0)
        self.device_combo = QComboBox()
        dlay.addWidget(self.device_combo, 1, 0)
        dlay.setColumnStretch(0, 1)
        dlay.setColumnStretch(1, 0)
        dlay.setColumnStretch(2, 0)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.refresh_btn.setFixedWidth(140)
        dlay.addWidget(self.refresh_btn, 1, 1)

        self.use_btn = QPushButton("Use Device")
        self.use_btn.clicked.connect(self.confirm_device)
        self.use_btn.setFixedWidth(160)
        dlay.addWidget(self.use_btn, 1, 2)

        self.device_info = QLabel("Scanning devices...")
        self.device_info.setObjectName("muted")
        dlay.addWidget(self.device_info, 2, 0, 1, 3)

        mode_row = QHBoxLayout()
        self.tuner_btn = QPushButton("Open Tuner")
        self.tuner_btn.clicked.connect(self.open_tuner)
        self.trainer_btn = QPushButton("Open Note Trainer")
        self.trainer_btn.clicked.connect(self.open_note_trainer)
        self.scale_btn = QPushButton("Scale Fretboard (PoC)")
        self.scale_btn.clicked.connect(self.open_scale_mapper)
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)
        mode_row.addWidget(self.tuner_btn)
        mode_row.addWidget(self.trainer_btn)
        mode_row.addWidget(self.scale_btn)
        mode_row.addStretch(1)
        mode_row.addWidget(self.quit_btn)
        layout.addLayout(mode_row)

        self.status = QLabel("Select an input device to begin.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        layout.addStretch(1)

    def refresh_devices(self):
        """Reload available audio input devices and update control availability."""
        devices = self.device_lister.show_devices("input")
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        if devices:
            metrics = QFontMetrics(self.device_combo.font())
            popup_width = max(metrics.horizontalAdvance(text) for text in devices) + 48
            self.device_combo.view().setMinimumWidth(popup_width)

        has_devices = len(devices) > 0
        self.use_btn.setEnabled(has_devices)
        self.tuner_btn.setEnabled(has_devices)
        self.trainer_btn.setEnabled(has_devices)
        self.scale_btn.setEnabled(True)

        if has_devices:
            self.device_combo.setCurrentIndex(0)
            self.device_info.setText(f"{len(devices)} input device(s) available.")
            self.status.setText("Ready.")
        else:
            self.device_info.setText("No input devices detected.")
            self.status.setText("Connect an audio input and refresh.")

    def selected_device_id(self):
        """Parse and validate the selected input-device identifier."""
        text = self.device_combo.currentText().strip()
        if not text.startswith("Input Device "):
            raise ValueError("No valid input device selected.")
        return parse_device_id(text)

    def confirm_device(self):
        """Persist user intent by showing the currently selected device in status."""
        try:
            did = self.selected_device_id()
            self.status.setText(f"Input Device {did} selected.")
        except ValueError:
            self.status.setText("Please choose a valid input device.")

    def open_tuner(self):
        """Open the tuner window for the currently selected input device."""
        try:
            did = self.selected_device_id()
        except ValueError:
            QMessageBox.warning(self, "No device", "Select a valid input device first.")
            return
        self.tuner_window = TunerWindow(did)
        self.tuner_window.closed.connect(self.show)
        self.tuner_window.show()
        self.hide()

    def open_note_trainer(self):
        """Open the note-trainer window for the currently selected input device."""
        try:
            did = self.selected_device_id()
        except ValueError:
            QMessageBox.warning(self, "No device", "Select a valid input device first.")
            return
        self.note_window = NoteTrainerWindow(did)
        self.note_window.closed.connect(self.show)
        self.note_window.show()
        self.hide()

    def open_scale_mapper(self):
        """Open the scale-to-fretboard PoC workbench window."""
        self.scale_window = ScaleWorkbenchWindow()
        self.scale_window.show()


def build_app() -> QApplication:
    # Global application theme. Update these style blocks to tune colors, typography, and control styling.
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QMainWindow, QWidget {
            background: #12161d;
            color: #e6edf3;
            font-family: "Segoe UI";
        }
        QFrame#card {
            background: #1b2430;
            border: 1px solid #2d3b4d;
            border-radius: 10px;
        }
        QLabel {
            background: transparent;
        }
        QLabel#muted {
            color: #9cb0c6;
        }
        QLabel#tunerDetectedNote {
            font-size: 160px;
            font-weight: 800;
        }
        QLabel#trainerPrompt {
            font-size: 48px;
            font-weight: 700;
        }
        QLabel#tunerFrequency {
            color: #9cb0c6;
            font-size: 30px;
            font-weight: 600;
        }
        QLabel#tunerCents {
            font-size: 38px;
            font-weight: 700;
        }
        QLabel#scaleTitle {
            font-size: 28px;
            font-weight: 700;
        }
        QLabel#fretboardTitle {
            font-size: 20px;
            font-weight: 700;
            color: #dbe8f4;
            padding-bottom: 4px;
        }
        QLabel#fretNum {
            color: #9cb0c6;
            font-size: 15px;
            font-weight: 600;
            min-width: 52px;
            max-width: 52px;
            min-height: 28px;
        }
        QLabel#openString {
            min-width: 40px;
            max-width: 40px;
            min-height: 40px;
            max-height: 40px;
            border-radius: 20px;
            background: #8192b0;
            color: #eef5ff;
            font-size: 18px;
            font-weight: 700;
        }
        QFrame#fretboardCard {
            background: #1b2430;
            border: 1px solid #2d3b4d;
            border-radius: 10px;
        }
        QFrame#fretCell {
            min-width: 52px;
            max-width: 52px;
            min-height: 44px;
            max-height: 44px;
            border-right: 1px solid #41526a;
            border-bottom: 1px solid #41526a;
            background: transparent;
        }
        QLabel#fretMarker {
            min-width: 34px;
            max-width: 34px;
            min-height: 34px;
            max-height: 34px;
            border-radius: 17px;
            background: #8495b4;
            color: #f2f7ff;
            font-size: 16px;
            font-weight: 700;
        }
        QLabel#fretMarkerRoot {
            min-width: 34px;
            max-width: 34px;
            min-height: 34px;
            max-height: 34px;
            border-radius: 17px;
            background: #2f4b86;
            color: #f6fbff;
            font-size: 16px;
            font-weight: 800;
        }
        QLabel#tuneHint {
            color: #8b9db0;
            font-size: 15px;
            font-weight: 600;
        }
        QLabel#tuneHintActive {
            color: #ffb347;
            font-size: 15px;
            font-weight: 700;
        }
        QLabel#inTuneOff {
            color: #8094aa;
            background: #243142;
            border: 1px solid #384c64;
            border-radius: 12px;
            padding: 4px 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        QLabel#inTuneOn {
            color: #0f2318;
            background: #37c978;
            border: 1px solid #37c978;
            border-radius: 12px;
            padding: 4px 10px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }
        QPushButton {
            background: #2f81f7;
            color: #ffffff;
            border: none;
            border-radius: 7px;
            padding: 8px 12px;
            font-weight: 600;
        }
        QPushButton:disabled {
            background: #3d4d62;
            color: #9baec3;
        }
        QPushButton:hover:!disabled {
            background: #1f6feb;
        }
        QComboBox, QSpinBox, QTableWidget {
            background: #0f141b;
            border: 1px solid #355070;
            border-radius: 6px;
            padding: 4px 6px;
            color: #e6edf3;
        }
        QSpinBox#topNSpin {
            padding-right: 26px;
            font-size: 16px;
            font-weight: 700;
        }
        QSpinBox#topNSpin::up-button, QSpinBox#topNSpin::down-button {
            width: 18px;
            border-left: 1px solid #355070;
            background: #2b3e54;
        }
        QSpinBox#topNSpin::up-button:hover, QSpinBox#topNSpin::down-button:hover {
            background: #355070;
        }
        QSpinBox#topNSpin::up-arrow {
            image: url(images/tuner_images/arrowUp.png);
            width: 10px;
            height: 10px;
        }
        QSpinBox#topNSpin::down-arrow {
            image: url(images/tuner_images/arrowDown.png);
            width: 10px;
            height: 10px;
        }
        QTableWidget {
            gridline-color: #2e3f55;
            selection-background-color: #1f6feb;
            selection-color: #ffffff;
        }
        QHeaderView::section {
            background: #18212d;
            color: #d3dfeb;
            border: 1px solid #2d3b4d;
            padding: 6px;
            font-weight: 600;
        }
        QProgressBar {
            background: #0f141b;
            border: 1px solid #2d3b4d;
            border-radius: 7px;
        }
        QProgressBar::chunk {
            background: #ffb347;
            border-radius: 7px;
        }
        """
    )
    return app
