from functions.note_trainer import NoteTrainer
from ui.note_trainer_score_ui import NoteTrainerScoreUI
from ui.note_trainer_missed_ui import NoteTrainerMissedNotesUI
from functions.sql_funcs import get_current_game_id, insert_final_score, insert_trials_bulk, get_best_score
from PIL import Image, ImageTk
import ttkbootstrap as tb
import datetime
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread

class NoteTrainerUI(tb.window.Toplevel):
    def __init__(self, input_device, main_menu):
        # UI window config
        super(NoteTrainerUI, self).__init__(title = "Guitar Trainer: Notes")        
        self.main_menu = main_menu
        self.input_device = input_device
        self.image_path = Path(__file__).resolve().parents[1] / "images"
        
        app_width = 1080
        app_height = 720
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight() 
        
        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)
        
        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")   
        
        ntp_title = tb.Label(self,
                                  text = "Note Trainer",
                                  font = ("Helvetica", 28))
        ntp_title.pack(pady=5)
        
        # Time per guess input
        time_per_guess_label = tb.Label(self, 
                                             text="Select time per guess (seconds)", 
                                             font=("Helvetica", 18))
        time_per_guess_label.pack(pady=5)  # Specify padding

        self.time_per_guess_input = tb.Entry(self)
        self.time_per_guess_input.pack(pady=5)
        self.time_per_guess_input.insert(0, "1")

        # Number of trials input
        trials_label = tb.Label(
            self, text="Select number of trials", font=("Helvetica", 18))
        trials_label.pack(pady=5)  # Specify padding

        self.trials_input = tb.Entry(self)
        self.trials_input.pack(pady=5)
        self.trials_input.insert(0, "10")

        # Play button
        self.play_btn = tb.Button(self,
                                  text="Play",
                                  command=self.play_button_action,
                                  style="success.TButton")
        self.play_btn.pack(pady=5)

        self.cancel_btn = tb.Button(self,
                                    text="Cancel game",
                                    command=self.cancel_game,
                                    style="warning.TButton",
                                    state="disabled")
        self.cancel_btn.pack(pady=5)
        
        # Target note text
        string_frame = tb.Frame(self)
        string_frame.pack(anchor = 'center', pady=5, padx=10)
        
        self.string_num_label = tb.Label(string_frame,
                                         text = "",
                                         font = ("Arial", 30))
        self.string_num_label.pack(side = 'left', padx=5)        
        
        self.low_high_label = tb.Label(string_frame,
                                     text = "",
                                     font = ("Arial", 30))
        self.low_high_label.pack(side = 'left', padx=5)
        
        self.note_label = tb.Label(string_frame,
                                   text = "",
                                   font = ("Arial", 30))
        self.note_label.pack(side = 'left', padx=5)
        
        # Correct/incorrect circles
        self.circle_frame = tb.Frame(self)
        self.circle_frame.pack(anchor='center', pady=5)
                
        # Stats buttons
        self.high_scores_btn = tb.Button(self,
                                         text = "High scores",
                                         command=self.show_highscores,
                                         style = "secondary.TButton")
        self.high_scores_btn.pack(pady=5)
        
        self.worst_notes_btn = tb.Button(self,
                                         text = "Most incorrect notes",
                                         command=self.show_worst_notes,
                                         style = "secondary.TButton")
        self.worst_notes_btn.pack(pady=5)
        
        # Main menu button
        self.mm_btn = tb.Button(self,
                                text = "Main menu",
                                command = self.go_main_menu,
                                style="primary.TButton"
                                )
        self.mm_btn.pack(pady=5)
        
        self.trial_number = 0
        self.circles_exist = False
        self.empty_circle_img = self._load_circle_image("EmptyCircle.png")
        self.green_circle_img = self._load_circle_image("GreenCircle.png")
        self.red_circle_img = self._load_circle_image("RedCircle.png")
        self.status_label = tb.Label(self, text="", font=("Arial", 12))
        self.status_label.pack(pady=2)
        # Threading primitives for non-blocking gameplay.
        self.game_running = False
        self.game_worker = None
        self.ui_event_queue = Queue()
        self.cancel_event = Event()
        self._is_closing = False
        self.poll_job_id = self.after(50, self._poll_game_events)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.bind("<Destroy>", self._on_destroy, add="+")
        
    def play_button_action(self):
        # Validate config and start a background gameplay worker.
        if self.game_running:
            return

        try:
            time_per_guess = int(self.time_per_guess_input.get())
            trials = int(self.trials_input.get())
        except ValueError:
            self.status_label.config(text="Please enter whole numbers for time and trials.")
            return

        if time_per_guess <= 0 or trials <= 0:
            self.status_label.config(text="Time and trials must both be greater than zero.")
            return

        if trials > 100:
            self.status_label.config(text="Please keep trials at 100 or fewer.")
            return

        self.status_label.config(text="Game in progress...")
        self.cancel_event.clear()
        
        self.display_circles(trials)
        self.trial_number = 0
        game_id = get_current_game_id()
        self._set_game_controls_enabled(False)
        self.game_running = True
        self.game_worker = Thread(
            target=self._run_game_worker,
            args=(time_per_guess, trials, game_id),
            daemon=True,
        )
        self.game_worker.start()

    def _run_game_worker(self, time_per_guess, trials, game_id):
        # Run all blocking work (audio prompts, recording, DB writes) off the UI thread.
        num_correct = 0
        trials_attempted = 0
        trials_to_insert = []
        nt = NoteTrainer(self.input_device)
        try:
            for i in range(trials):
                if self.cancel_event.is_set():
                    break

                random_note = nt.random_note()
                self.ui_event_queue.put({
                    "type": "trial_start",
                    "string": random_note["string"],
                    "low_high": random_note["low_high"],
                    "note": random_note["note"],
                    "trial_number": i + 1,
                    "total_trials": trials,
                })
                result = nt.play_game(
                    time_per_guess,
                    string=random_note["string"],
                    low_high=random_note["low_high"],
                    note=random_note["note"],
                )
                is_correct = result["correct"] is True
                if is_correct:
                    num_correct += 1
                trials_attempted += 1
                self.ui_event_queue.put({
                    "type": "trial_result",
                    "is_correct": is_correct,
                    "trial_number": i + 1,
                    "total_trials": trials,
                })
                trials_to_insert.append(
                    (
                        datetime.datetime.now(),
                        game_id,
                        time_per_guess,
                        trials,
                        i + 1,
                        result["string"],
                        result["low_high"],
                        result["note"],
                        result["played_note"],
                        is_correct,
                    )
                )

            if trials_to_insert:
                insert_trials_bulk(trials_to_insert)

            if trials_attempted > 0:
                best_score_message = get_best_score(time_per_guess, trials_attempted, num_correct)
                insert_final_score(game_id, time_per_guess, trials_attempted, num_correct)
            else:
                best_score_message = "No trials completed."

            self.ui_event_queue.put({
                "type": "game_complete",
                "num_correct": num_correct,
                "trials": trials_attempted,
                "cancelled": self.cancel_event.is_set(),
                "best_score_message": best_score_message,
            })
        except Exception as exc:
            self.ui_event_queue.put({"type": "game_error", "message": str(exc)})
        finally:
            nt.close()

    def _poll_game_events(self):
        # Apply worker events on the tkinter thread.
        if self._is_closing:
            return

        try:
            while True:
                event = self.ui_event_queue.get_nowait()
                event_type = event.get("type")

                if event_type == "trial_start":
                    self.change_text(event["string"], event["low_high"], event["note"])
                    self.status_label.config(
                        text=f"Trial {event['trial_number']}/{event['total_trials']} in progress..."
                    )
                elif event_type == "trial_result":
                    if event["is_correct"]:
                        self.correct()
                    else:
                        self.incorrect()
                elif event_type == "game_complete":
                    if event["trials"] > 0:
                        self.show_best_score(
                            event["num_correct"],
                            event["trials"],
                            event["best_score_message"],
                        )
                    else:
                        self.string_num_label.config(text="Game cancelled.", font=("Arial", 20))
                        self.low_high_label.config(text="No trials completed.", font=("Arial", 20))
                        self.note_label.config(text="", font=("Arial", 20))

                    if event.get("cancelled"):
                        self.status_label.config(text="Game cancelled.")
                    else:
                        self.status_label.config(text="Game complete.")
                    self.game_running = False
                    self._set_game_controls_enabled(True)
                elif event_type == "game_error":
                    self.status_label.config(text=f"Game failed: {event['message']}")
                    self.game_running = False
                    self._set_game_controls_enabled(True)
        except Empty:
            pass
        try:
            self.poll_job_id = self.after(50, self._poll_game_events)
        except tk.TclError:
            self.poll_job_id = None

    def display_circles(self, circle_num=10):
        # Rebuild per-trial progress indicators for the current session.
        self.circles_exist
        for widget in self.circle_frame.winfo_children():
            widget.destroy()
            widget.pack_forget()

        for i in range(circle_num):
            ec_label = tb.Label(self.circle_frame, 
                                image=self.empty_circle_img,
                                borderwidth=0)
            ec_label.pack(side='left', padx=0, anchor='center', expand=True)
            
        self.update_idletasks()
        
    def change_text(self, string, low_high, note):
        self.string_num_label.config(text=f"{string} string")        
        self.low_high_label.config(text=f"{low_high}")
        self.note_label.config(text=f"{note}")
        self.update_idletasks()        

    def correct(self):
        # Paint the next progress marker green.
        self.trial_number
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=self.green_circle_img)

        self.trial_number += 1
        
        self.update_idletasks()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0            

    def incorrect(self):
        # Paint the next progress marker red.
        self.trial_number
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=self.red_circle_img)

        self.trial_number += 1
        
        self.update_idletasks()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0
            
    def show_best_score(self, num_correct, trials, best_score_message):
        print(f"Game over.\n{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.\n{best_score_message}")
        self.string_num_label.config(text="Game over.",
                                     font = ("Arial", 20))        
        self.low_high_label.config(text=f"{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.",
                                   font = ("Arial", 20))
        self.note_label.config(text=f"{best_score_message}",
                               font = ("Arial", 20))
        self.update_idletasks()
        
    def show_highscores(self):
        ntsui = NoteTrainerScoreUI(self)
        self.withdraw()        
    
    def show_worst_notes(self):
        ntmnui = NoteTrainerMissedNotesUI(self)
        self.withdraw()        
        pass
    
    def go_main_menu(self):
        if self.game_running:
            self.status_label.config(text="Wait for the current game to finish before leaving.")
            return
        self.main_menu.deiconify()
        self.withdraw()

    def _load_circle_image(self, filename):
        image = Image.open(self.image_path / filename)
        image = image.resize((32, 32))
        return ImageTk.PhotoImage(image)

    def _set_game_controls_enabled(self, enabled):
        # Keep navigation/settings locked while a game is active.
        state = "normal" if enabled else "disabled"
        self.play_btn.configure(state=state)
        self.cancel_btn.configure(state="disabled" if enabled else "normal")
        self.high_scores_btn.configure(state=state)
        self.worst_notes_btn.configure(state=state)
        self.mm_btn.configure(state=state)
        self.time_per_guess_input.configure(state=state)
        self.trials_input.configure(state=state)

    def cancel_game(self):
        # Request cooperative cancellation after the current trial completes.
        if not self.game_running:
            return
        self.cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self.status_label.config(text="Cancelling after current trial...")

    def _on_window_close(self):
        self._is_closing = True
        self.cancel_event.set()
        self._cancel_poll_job()
        self.destroy()

    def _cancel_poll_job(self):
        if self.poll_job_id is None:
            return
        try:
            self.after_cancel(self.poll_job_id)
        except tk.TclError:
            pass
        self.poll_job_id = None

    def _on_destroy(self, event):
        if event.widget is self:
            self._is_closing = True
            self.cancel_event.set()
            self._cancel_poll_job()
        
        

    
