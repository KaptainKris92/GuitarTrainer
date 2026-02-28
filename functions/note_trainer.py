import pickle
from pathlib import Path
from random import choice as rc
from time import sleep

import aubio
import numpy as np
import pyaudio
from playsound3 import playsound


class NoteTrainer:
    def __init__(self, input_device):
        self.input_device = input_device
        self.base_path = Path(__file__).resolve().parents[1]
        self.sound_path = self.base_path / "sounds"

        with open(self.base_path / "guitar_note_dictionary.pkl", "rb") as f:
            self.guitar_note_dictionary = pickle.load(f)

        with open(self.base_path / "all_note_dictionary.pkl", "rb") as f:
            self.all_note_dictionary = pickle.load(f)

    def record(self, record_duration=3, stop_event=None):
        p = pyaudio.PyAudio()
        buffer_size = 1024
        samplerate = 44100
        stream = None
        notes_played = []

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
                if record_duration and (record_duration * samplerate < total_frames):
                    break

                audiobuffer = stream.read(buffer_size, exception_on_overflow=False)
                signal = np.frombuffer(audiobuffer, dtype=np.float32)
                pitch = round(pitch_o(signal)[0])

                if 40 <= pitch <= 85:
                    notes_played.append(pitch)

                total_frames += len(signal)

        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            p.terminate()

        return notes_played

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

    def play_game(self, time_per_guess=10, string=None, low_high=None, note=None, stop_event=None):
        note_sound = self._note_to_sound_name(note)

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

        played_notes = self.record(record_duration=time_per_guess, stop_event=stop_event)

        if stop_event is not None and stop_event.is_set():
            return {
                "cancelled": True,
                "correct": None,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": None,
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
        expected = self.guitar_note_dictionary[string][low_high][note]

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
