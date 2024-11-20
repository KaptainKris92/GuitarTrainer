# General
import numpy as np
from random import choice as rc # Random note selection
import pickle # For loading note dictionary
from time import sleep

# Audio 
import pyaudio # Audio input
import aubio # Note recognition
from playsound import playsound # For playing sound files. Has to be version 1.2.2 to work


# Database
import datetime
import sqlite3


def print_devices():
    p = pyaudio.PyAudio()
    
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
        if (p.get_device_info_by_index(i).get('maxOutputChannels')) > 0:
            print("Output Device id ", i, " - ", p.get_device_info_by_index(i).get('name'))

def record(filename = None, record_duration = 3):
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
                    input_device_index=3,
                    output_device_index=7)
    

    outputsink = None
    record_duration = record_duration
    total_frames = 100
    
    # setup pitch
    tolerance = 0.8
    win_s = 4096 # fft size
    hop_s = buffer_size # hop size
    pitch_o = aubio.pitch("default", win_s, hop_s, samplerate)
    pitch_o.set_unit("midi")
    pitch_o.set_tolerance(tolerance)
    notes_played = []
    
    #print("*** starting recording")

    while True:
        try:
            audiobuffer = stream.read(buffer_size)
            signal = np.frombuffer(audiobuffer, dtype=np.float32)
            
            #confidence = pitch_o.get_confidence()
            pitch = round(pitch_o(signal)[0])
            
            if pitch >= 40 and pitch <= 85:
                #print(f"Pitch: {pitch}\nConfidence: {confidence}")    
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



with open('guitar_note_dictionary_nums.pkl', 'rb') as f:
    #pickle.dump(guitar_note_dictionary, f)
    guitar_note_dictionary = pickle.load(f)
    
with open('all_note_dictionary.pkl', 'rb') as f:
    all_note_dictionary = pickle.load(f)
    
del f

def find_note(val):
    for k, v in all_note_dictionary.items():
        if val in v:
            return k    

# Simplify connection to SQL database and inserting into fewer functions to avoid repeating code!    
def get_current_gameid():
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    
    return cur.execute("SELECT MAX(GameID) FROM score_log_v1").fetchone()[0] + 1
    

def insert_trial(game_id, time_per_guess, trials, trial_number, target_string, target_lowhigh, target_note, played_note, is_correct):    
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    insertQuery = "INSERT INTO score_log_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"    
    
    cur.execute(insertQuery,
                (datetime.datetime.now(), 
                 game_id, 
                 time_per_guess, 
                 trials, 
                 trial_number, 
                 target_string, 
                 target_lowhigh, 
                 target_note, 
                 played_note, 
                 is_correct))
    
    con.commit()
    cur.close()
    con.close()
    
def insert_final_score(game_id, time_per_guess, trials, num_correct):
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    insertQuery = "INSERT INTO final_score_log_v1 VALUES (?, ?, ?, ?, ?);"    
    
    cur.execute(insertQuery,
                (datetime.datetime.now(), 
                 game_id, 
                 time_per_guess, 
                 trials, 
                 num_correct))
    
    con.commit()
    cur.close()
    con.close()



def play_game(time_per_guess = 10, trials = 10):
    
    num_correct = 0
    game_id = get_current_gameid()
    
    for i in range(trials):
        string = rc(list(guitar_note_dictionary.keys()))
        low_high = rc(list(guitar_note_dictionary[string].keys()))
        note = rc(list(guitar_note_dictionary[string][low_high].keys()))
        
        print(f"Play {string} string, {low_high} {note}.")
        playsound(f'./sounds/{string}.mp3')
        playsound(f'./sounds/{low_high}.mp3')
        playsound(f'./sounds/{note}.mp3')        
        sleep(0.1)
        playsound('./sounds/clack.mp3')
        played_notes = record(record_duration = time_per_guess)
        
        try:
            median_note = int(np.median(played_notes))
        
            if median_note == guitar_note_dictionary[string][low_high][note]:
                
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
                incorrect_note = find_note(median_note)
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
                
            
        except ValueError :
            print("No note played.")
            
    insert_final_score(game_id, time_per_guess, trials, num_correct)    
    print(f"Game over.\n{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.")
           
play_game(5, 15)
'''
# Saving to database
con = sqlite3.connect("score_database.db")
cur = con.cursor()
cur.execute("CREATE TABLE score_log_v1(Date, GameID, TimePerGuess, TotalTrials,\
            TrialNumber, TargetNote, PlayedNote, IsCorrect)")

# Checking that database exists using sqlite_master
res = cur.execute("SELECT name FROM sqlite_master")
res.fetchone()


cur.execute("CREATE TABLE score_log_v1(Date TIMESTAMP, GameID INTEGER, TimePerGuess INTEGER, TotalTrials INTEGER,\
            TrialNumber INTEGER, TargetString VARCHAR(3), TargetLowHigh VARCHAR(4), TargetNote VARCHAR(2), PlayedNote VARCHAR(2), IsCorrect BOOLEAN)")

cur.execute("CREATE TABLE final_score_log_v1(Date TIMESTAMP, GameID INTEGER, TimerPerGuess INTEGER, TotalTrials INTEGER, TotalCorrect INTEGER)")
    
'''
'''
#############
### TO DO ###
#############

- Make a UI
- Separate into files
    - Main (contains game logic?)    
    - Audio (contains recording and device stuff)
        - Possibly turn into a class so uses the same pyaudio initialisation?
    - Database (all SQL stuff)
- Fix 'The system cannot find the path specified.' error
- Re-record 1st to 5th without saying 'string'
    
    


    


----------------------------
| Create app for arpeggios |
----------------------------


    
'''
