# General
import numpy as np
from random import choice as rc  # Random note selection
import pickle  # For loading note dictionary
from time import sleep

# Audio
import pyaudio  # Audio input
import aubio  # Note recognition
# For playing sound files. Has to be version 1.2.2 to work
from playsound import playsound

# Database
from sql_funcs import get_current_game_id, insert_trial, insert_final_score, get_best_score


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

    def play_game(self, time_per_guess=10, trials=10):
                
        num_correct = 0
        game_id = get_current_game_id()

        for i in range(trials):
            string = rc(list(self.guitar_note_dictionary.keys()))
            low_high = rc(list(self.guitar_note_dictionary[string].keys()))
            note = rc(
                list(self.guitar_note_dictionary[string][low_high].keys()))

            print(f"Play {string} string, {low_high} {note}.")
            playsound(f'./sounds/{string}.mp3')
            playsound(f'./sounds/{low_high}.mp3')
            playsound(f'./sounds/{note}.mp3')
            sleep(0.1)
            playsound('./sounds/clack.mp3')
            played_notes = self.record(record_duration=time_per_guess)

            try:
                median_note = int(np.median(played_notes))

                if median_note == self.guitar_note_dictionary[string][low_high][note]:

                    playsound('./sounds/correct.mp3')                    
                    print("Correct!")
                    num_correct += 1
                    insert_trial(game_id,
                                      time_per_guess,
                                      trials,
                                      i + 1,
                                      string,
                                      low_high,
                                      note,
                                      note,
                                      True)
                else:
                    playsound('./sounds/incorrect.mp3')
                    incorrect_note = self.find_note(median_note)
                    playsound('./sounds/you_played.mp3')
                    playsound(f'./sounds/{incorrect_note}.mp3')
                    print(f"Incorrect. You played {incorrect_note}.")
                    insert_trial(game_id,
                                      time_per_guess,
                                      trials,
                                      i + 1,
                                      string,
                                      low_high,
                                      note,
                                      incorrect_note,
                                      False)

            except ValueError:
                print("No note played.")
                insert_trial(game_id,
                                  time_per_guess,
                                  trials,
                                  i + 1,
                                  string,
                                  low_high,
                                  note,
                                  None,
                                  False)
        
        print(f"Game over.\n{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.\n{get_best_score(time_per_guess, trials, num_correct)}")
        insert_final_score(game_id, time_per_guess, trials, num_correct)
    



    '''
    #############
    ### TO DO ###
    #############
    
    - Make a UI
    - Separate into files/modules
        - Main     
        - Games (contains game logic)
        - Audio (contains recording and device stuff)
            - Possibly turn into a class so uses the same pyaudio initialisation?
        - Database (all SQL stuff)
    - Fix 'The system cannot find the path specified.' error
    - Re-record 1st to 5th without saying 'string'
    - Clean up the functions using SQL so there is less repetition.
    - If database doesn't exist in folder, write code to create one. 
    - Write function for plotting how many times got each note incorrect (as a proportion/percentage of total times note was targeted?)
    - Other statistics, e.g. total times played, average percentage correct, most correct notes.
    
    
    ------------------
    | Arpeggios game |
    ------------------
    
    ------------------
    | Intervals game |
    ------------------
    
    ------------------
    | Scales game ?? |
    ------------------
    
    
        
    '''
