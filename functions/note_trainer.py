# General
import numpy as np
from random import choice as rc  # Random note selection
import pickle  # For loading note dictionary
from time import sleep

# Audio
import pyaudio  # Audio input
import aubio  # Note recognition
# For playing sound files. Has to be version 1.2.2 to work
from playsound3 import playsound

class NoteTrainer():
    def __init__(self, input_device):        
        self.input_device = input_device            

        with open('guitar_note_dictionary.pkl', 'rb') as f:
            # pickle.dump(guitar_note_dictionary, f)
            self.guitar_note_dictionary = pickle.load(f)

        with open('all_note_dictionary.pkl', 'rb') as f:
            self.all_note_dictionary = pickle.load(f)

        del f

    def record(self, filename=None, record_duration=3):
        # initialise pyaudio
        p = pyaudio.PyAudio()
        # open stream
        buffer_size = 1024
        pyaudio_format = pyaudio.paFloat32
        n_channels = 1
        samplerate = 44100

        stream = p.open(format=pyaudio_format,
                             channels=n_channels,
                             rate=samplerate,
                             input=True,
                             frames_per_buffer=buffer_size,
                             input_device_index=self.input_device,
                             output_device_index=7)

        outputsink = None
        record_duration = record_duration
        total_frames = 100

        # setup pitch
        tolerance = 0.8
        win_s = 4096  # fft size
        hop_s = buffer_size  # hop size
        pitch_o = aubio.pitch("default", win_s, hop_s, samplerate)
        pitch_o.set_unit("midi")
        pitch_o.set_tolerance(tolerance)
        notes_played = []

        # print("*** starting recording")

        while True:
            try:
                audiobuffer = stream.read(buffer_size)
                signal = np.frombuffer(audiobuffer, dtype=np.float32)

                # confidence = pitch_o.get_confidence()
                pitch = round(pitch_o(signal)[0])

                if pitch >= 40 and pitch <= 85:
                    # print(f"Pitch: {pitch}\nConfidence: {confidence}")
                    notes_played.append(pitch)

                if outputsink:
                    outputsink(signal, len(signal))

                if record_duration:
                    total_frames += len(signal)
                    if record_duration * samplerate < total_frames:
                        break

            except KeyboardInterrupt:
                print("*** Ctrl+C pressed, exiting")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()

        return notes_played

    def find_note(self, val):
        for k, v in self.all_note_dictionary.items():
            if val in v:
                return k
    
    def random_note(self):
        string = rc(list(self.guitar_note_dictionary.keys()))
        low_high = rc(list(self.guitar_note_dictionary[string].keys()))
        note = rc(
            list(self.guitar_note_dictionary[string][low_high].keys()))
        
        return {'string': string, 
                'low_high': low_high,
                'note': note}
    
    def play_game(self, time_per_guess=10, string=None, low_high=None, note=None):
        
        # Replace ♯ and ♭with valid symbols, otherwise difficulty finding the note
        note_sound = note.replace("♯","#").replace("♭","b")                              
        
        print(f"Play {string} string, {low_high} {note}.")
        playsound(f'./sounds/{string}.mp3')
        playsound(f'./sounds/{low_high}.mp3')
        playsound(f'./sounds/{note_sound}.mp3')
        sleep(0.1)
        playsound('./sounds/clack.mp3')
        played_notes = self.record(record_duration=time_per_guess)

        try:
            median_note = int(np.median(played_notes))

            if median_note == self.guitar_note_dictionary[string][low_high][note]:

                playsound('./sounds/correct.mp3')                       
                print("Correct!")
                return {'correct': True,
                        'string': string,
                        'low_high': low_high,
                        'note': note,
                        'played_note': note}
                         
            else:
                playsound('./sounds/incorrect.mp3')
                incorrect_note = self.find_note(median_note)
                # Replace ♯ and ♭with valid symbols, otherwise difficulty finding the note
                incorrect_note_sound = incorrect_note.replace("♯","#").replace("♭","b").replace("/", "or")                    
                
                playsound('./sounds/you_played.mp3')
                playsound(f'./sounds/{incorrect_note_sound}.mp3')                
                print(f"Incorrect. You played {incorrect_note}.")
                return {'correct': False,
                        'string': string,
                        'low_high': low_high,
                        'note': note,
                        'played_note': incorrect_note}
        

        except ValueError:            
            print("No note played.")
            return {'correct': None,
                    'string': string,
                    'low_high': low_high,
                    'note': note,
                    'played_note': None}          
        
