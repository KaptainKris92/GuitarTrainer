# General
import pickle
from pathlib import Path
from random import choice as rc
from time import sleep

import numpy as np

# Audio
import aubio
import pyaudio
from playsound3 import playsound


class NoteTrainer:
    # Dictionaries are shared across instances to avoid repeated disk loads.
    _dictionaries_loaded = False
    _guitar_note_dictionary = None
    _all_note_dictionary = None

    def __init__(self, input_device):
        self.input_device = input_device
        self.base_path = Path(__file__).resolve().parents[1]
        self.sound_path = self.base_path / "sounds"
        self.py_audio = pyaudio.PyAudio()

        if not NoteTrainer._dictionaries_loaded:
            with open(self.base_path / "guitar_note_dictionary.pkl", "rb") as f:
                NoteTrainer._guitar_note_dictionary = pickle.load(f)
            with open(self.base_path / "all_note_dictionary.pkl", "rb") as f:
                NoteTrainer._all_note_dictionary = pickle.load(f)
            NoteTrainer._dictionaries_loaded = True

        self.guitar_note_dictionary = NoteTrainer._guitar_note_dictionary
        self.all_note_dictionary = NoteTrainer._all_note_dictionary

    def close(self):
        if self.py_audio is not None:
            self.py_audio.terminate()
            self.py_audio = None

    def record(self, record_duration=3):
        # Capture a short audio window and extract detected MIDI pitches.
        buffer_size = 1024
        samplerate = 44100
        stream = None
        notes_played = []

        try:
            stream = self.py_audio.open(
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
            while total_frames < record_duration * samplerate:
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
    def _note_to_sound_filename(note):
        # Normalize note names to match recorded filename convention.
        return note.replace("♯", "#").replace("♭", "b").replace("/", "or")

    def _play_sound(self, filename):
        playsound(self.sound_path / filename)

    def play_game(self, time_per_guess=10, string=None, low_high=None, note=None):
        # Prompt, record, score one trial, and return a structured result payload.
        note_sound = self._note_to_sound_filename(note)

        print(f"Play {string} string, {low_high} {note}.")
        self._play_sound(f"{string}.mp3")
        self._play_sound(f"{low_high}.mp3")
        self._play_sound(f"{note_sound}.mp3")
        sleep(0.1)
        self._play_sound("clack.mp3")
        played_notes = self.record(record_duration=time_per_guess)

        if not played_notes:
            print("No note played.")
            return {
                "correct": None,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": None,
            }

        median_note = int(np.median(played_notes))
        expected_note = self.guitar_note_dictionary[string][low_high][note]

        if median_note == expected_note:
            self._play_sound("correct.mp3")
            print("Correct!")
            return {
                "correct": True,
                "string": string,
                "low_high": low_high,
                "note": note,
                "played_note": note,
            }

        self._play_sound("incorrect.mp3")
        incorrect_note = self.find_note(median_note)
        if incorrect_note is not None:
            incorrect_note_sound = self._note_to_sound_filename(incorrect_note)
            self._play_sound("you_played.mp3")
            self._play_sound(f"{incorrect_note_sound}.mp3")
            print(f"Incorrect. You played {incorrect_note}.")
        else:
            print("Incorrect.")

        return {
            "correct": False,
            "string": string,
            "low_high": low_high,
            "note": note,
            "played_note": incorrect_note,
        }
