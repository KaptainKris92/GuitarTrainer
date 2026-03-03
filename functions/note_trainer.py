import pickle
from pathlib import Path
from random import choice as rc
from time import sleep

import aubio
import numpy as np
import pyaudio
from playsound3 import playsound


class NoteTrainer:
    def __init__(self, input_device, input_rms_threshold=0.01):
        self.input_device = input_device
        self.input_rms_threshold = max(0.0, float(input_rms_threshold))
        self.base_path = Path(__file__).resolve().parents[1]
        self.sound_path = self.base_path / "sounds"

        with open(self.base_path / "guitar_note_dictionary.pkl", "rb") as f:
            self.guitar_note_dictionary = pickle.load(f)

        with open(self.base_path / "all_note_dictionary.pkl", "rb") as f:
            self.all_note_dictionary = pickle.load(f)

    @staticmethod
    def _safe_callback(callback, *args):
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            # UI callbacks are best-effort and must not interrupt audio capture.
            pass

    def record(
        self,
        record_duration=3,
        stop_event=None,
        expected_midi=None,
        end_on_correct=False,
        end_on_incorrect=False,
        level_callback=None,
        countdown_callback=None,
    ):
        p = pyaudio.PyAudio()
        buffer_size = 1024
        samplerate = 44100
        stream = None
        notes_played = []
        early_end_reason = None
        early_end_pitch = None
        correct_hits = 0
        incorrect_hits = 0
        required_hits = 2

        try:
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=samplerate,
                input=True,
                frames_per_buffer=buffer_size,
                input_device_index=self.input_device,
            )

            tolerance = 0.8
            win_s = 4096
            hop_s = buffer_size
            pitch_o = aubio.pitch("default", win_s, hop_s, samplerate)
            pitch_o.set_unit("midi")
            pitch_o.set_tolerance(tolerance)

            total_frames = 0
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
                if record_duration and ((record_duration * samplerate) <= total_frames):
                    break

                audiobuffer = stream.read(buffer_size, exception_on_overflow=False)
                signal = np.frombuffer(audiobuffer, dtype=np.float32)
                rms = float(np.sqrt(np.mean(np.square(signal)))) if signal.size else 0.0
                input_detected = rms >= self.input_rms_threshold
                self._safe_callback(level_callback, rms, input_detected)

                total_frames += len(signal)
                if record_duration:
                    remaining_seconds = max(0.0, record_duration - (total_frames / samplerate))
                    remaining_fraction = (
                        remaining_seconds / record_duration if record_duration > 0 else 0.0
                    )
                    self._safe_callback(countdown_callback, remaining_seconds, remaining_fraction)

                if not input_detected:
                    continue

                pitch = round(pitch_o(signal)[0])
                if 40 <= pitch <= 85:
                    notes_played.append(pitch)
                    if expected_midi is not None:
                        if pitch == expected_midi:
                            correct_hits += 1
                            incorrect_hits = 0
                            if end_on_correct and correct_hits >= required_hits:
                                early_end_reason = "correct"
                                early_end_pitch = pitch
                                break
                        else:
                            correct_hits = 0
                            incorrect_hits += 1
                            if end_on_incorrect and incorrect_hits >= required_hits:
                                early_end_reason = "incorrect"
                                early_end_pitch = pitch
                                break

        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            p.terminate()

        return {
            "notes_played": notes_played,
            "ended_early_reason": early_end_reason,
            "ended_early_pitch": early_end_pitch,
        }

    def find_note(self, val):
        for key, values in self.all_note_dictionary.items():
            if val in values:
                return key
        return None

    def random_note(self):
        string = rc(list(self.guitar_note_dictionary.keys()))
        low_high = rc(list(self.guitar_note_dictionary[string].keys()))
        note = rc(list(self.guitar_note_dictionary[string][low_high].keys()))
        return {"string": string, "low_high": low_high, "note": note}

    @staticmethod
    def _note_to_sound_name(note):
        return (
            note.replace("â™¯", "#")
            .replace("â™­", "b")
            .replace("♯", "#")
            .replace("♭", "b")
            .replace("/", "or")
        )

    def _play(self, filename, stop_event=None):
        if stop_event is not None and stop_event.is_set():
            return
        playsound(self.sound_path / filename)

    def play_game(
        self,
        time_per_guess=10,
        string=None,
        low_high=None,
        note=None,
        stop_event=None,
        end_on_correct=False,
        end_on_incorrect=False,
        level_callback=None,
        countdown_callback=None,
    ):
        note_sound = self._note_to_sound_name(note)
        expected = self.guitar_note_dictionary[string][low_high][note]

        if stop_event is not None and stop_event.is_set():
            return {
                "cancelled": True,
                "correct": None,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": None,
            }

        print(f"Play {string} string, {low_high} {note}.")
        self._play(f"{string}.mp3", stop_event=stop_event)
        self._play(f"{low_high}.mp3", stop_event=stop_event)
        self._play(f"{note_sound}.mp3", stop_event=stop_event)
        sleep(0.1)
        self._play("clack.mp3", stop_event=stop_event)

        recording = self.record(
            record_duration=time_per_guess,
            stop_event=stop_event,
            expected_midi=expected if (end_on_correct or end_on_incorrect) else None,
            end_on_correct=end_on_correct,
            end_on_incorrect=end_on_incorrect,
            level_callback=level_callback,
            countdown_callback=countdown_callback,
        )
        played_notes = recording["notes_played"]

        if stop_event is not None and stop_event.is_set():
            return {
                "cancelled": True,
                "correct": None,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": None,
            }

        if recording["ended_early_reason"] == "correct":
            self._play("correct.mp3", stop_event=stop_event)
            print("Correct!")
            return {
                "cancelled": False,
                "correct": True,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": note,
            }

        if recording["ended_early_reason"] == "incorrect":
            self._play("incorrect.mp3", stop_event=stop_event)
            wrong_pitch = recording.get("ended_early_pitch")
            incorrect_note = self.find_note(wrong_pitch) if wrong_pitch is not None else None
            if incorrect_note is not None:
                self._play("you_played.mp3", stop_event=stop_event)
                self._play(f"{self._note_to_sound_name(incorrect_note)}.mp3", stop_event=stop_event)
                print(f"Incorrect. You played {incorrect_note}.")
            else:
                print("Incorrect.")
            return {
                "cancelled": False,
                "correct": False,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": incorrect_note,
            }

        if not played_notes:
            print("No note played.")
            return {
                "cancelled": False,
                "correct": None,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": None,
            }

        median_note = int(np.median(played_notes))

        if median_note == expected:
            self._play("correct.mp3", stop_event=stop_event)
            print("Correct!")
            return {
                "cancelled": False,
                "correct": True,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": note,
            }

        self._play("incorrect.mp3", stop_event=stop_event)
        incorrect_note = self.find_note(median_note)
        if incorrect_note is not None:
            self._play("you_played.mp3", stop_event=stop_event)
            self._play(f"{self._note_to_sound_name(incorrect_note)}.mp3", stop_event=stop_event)
            print(f"Incorrect. You played {incorrect_note}.")
        else:
            print("Incorrect.")

        return {
            "cancelled": False,
            "correct": False,
            "string": string,
            "low_high": low_high,
            "note": note,
            "played_note": incorrect_note,
        }
