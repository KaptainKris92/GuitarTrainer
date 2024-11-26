from tkinter import *
import ttkbootstrap as tb
from PIL import Image, ImageTk

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

def show_devices(device_type = None):
    p = pyaudio.PyAudio()
    
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    input_device_list = []
    output_device_list = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            input_device_list.append("Input Device " + str(i) + " - " + p.get_device_info_by_host_api_device_index(0, i).get('name'))            
        if (p.get_device_info_by_index(i).get('maxOutputChannels')) > 0:
            output_device_list.append("Output Device " + str(i) + " - " + p.get_device_info_by_index(i).get('name'))
            
    
    if device_type == "input":
        return input_device_list
    elif device_type == "output":
        return output_device_list
    elif device_type is None: 
        return input_device_list + output_device_list
    elif device_type not in ["input", "output", None]:
        return "Invalid device type. Please select 'input', 'output', or None"
    

def record(filename = None, record_duration = 3, input_device_id = 3):
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
                    input_device_index=input_device_id,
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



with open('guitar_note_dictionary.pkl', 'rb') as f:
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

def get_best_score(time_per_guess, trials, num_correct):
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    
    previous_best = cur.execute(f"SELECT MAX(TotalCorrect) FROM final_score_log_v1\
                WHERE TimerPerGuess = {time_per_guess} AND TotalTrials = {trials}").fetchall()[0][0]
                                
    cur.close()
    con.close()
    
    if num_correct > previous_best:
        return "New high score!"
    elif num_correct == previous_best:
        return "Matched previous best."
    else: 
        return f"Previous best: {previous_best}/{trials}"

def get_top_5_incorrect():
    con = sqlite3.connect("score_database.db",
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    
    most_incorrect = cur.execute("SELECT TargetString, TargetLowHigh, TargetNote, COUNT(*) AS total_incorrect FROM\
                                score_log_v1\
                                WHERE IsCorrect = 0\
                                GROUP BY TargetString, TargetLowHigh, TargetNote\
                                ORDER BY total_incorrect DESC\
                                LIMIT 5;"
                                ).fetchall()
                                
    cur.close()
    con.close()
    
    joined_incorrect = []
    for i in most_incorrect:
        joined_incorrect.append("".join(str(i[0:3])).replace("'", "").replace(",", "").replace("(" , "").replace(")", "") + f": {str(i[3])} incorrect")
        
    top_5_incorrect = '\n'.join(joined_incorrect)
        
    print(f"Top 5 incorrect notes:\n{top_5_incorrect}")    
    
    

def play_game(input_device_id = 3, time_per_guess = 10, trials = 10):
    
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
        played_notes = record(record_duration = time_per_guess, input_device_id = input_device_id)
        
        try:
            median_note = int(np.median(played_notes))
        
            if median_note == guitar_note_dictionary[string][low_high][note]:
                correct_circle()
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
                incorrect_circle()
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


input_devices = show_devices("input")

root = tb.Window(themename = "superhero")

root.title("Guitar Trainer")
root.geometry('1000x500')

def device_confirmation():
    #device_label.config(text = f"{device_combo.get()} selected")
    device_id = input_devices.index(device_combo.get())
    device_label.config(text = f"Device {device_id} selected")
    
# Automatic selection binding on click of combobox option.
# e = event
def click_bind(e):
    device_label.config(text = f"{device_combo.get()} selected")
    
def play_button_action():
    time_per_guess = int(time_per_guess_input.get())
    trials = int(trials_input.get())
    device_id = input_devices.index(device_combo.get())    
    display_circles(trials)
    play_game(input_device_id = device_id, time_per_guess = time_per_guess, trials = trials)

            

device_label = tb.Label(root, text = "Select input device", font = ("Helvetica", 18))
device_label.pack(pady=30) # Specify padding

device_combo = tb.Combobox(root, bootstyle = "success", values = input_devices)
device_combo.pack(pady=10)

select_device_btn = tb.Button(root, 
                              text = "Select device", 
                              command = device_confirmation, 
                              bootstyle = "danger")
select_device_btn.pack(pady=5)

# Set default device
device_combo.current(2)

# Bind combobox - Automatically sets the selection when clicked, instead of requiring a button press.
#device_combo.bind("<<ComboboxSelected>>", click_bind)

time_per_guess_label = tb.Label(root, text = "Select time per guess (seconds)", font = ("Helvetica", 18))
time_per_guess_label.pack(pady=5) # Specify padding

time_per_guess_input = Entry(root)
time_per_guess_input.pack(pady=5)
time_per_guess_input.insert(0, "1")


trials_label = tb.Label(root, text = "Select number of trials", font = ("Helvetica", 18))
trials_label .pack(pady=5) # Specify padding

trials_input = Entry(root)
trials_input.pack(pady=5)
trials_input.insert(0, "10")

play_btn = tb.Button(root, 
                    text = "Play", 
                    command = play_button_action, 
                    bootstyle = "success")
play_btn.pack(pady=5)

circle_frame = Frame(root)
circle_frame.pack(anchor = 'center', pady = 10)


def display_circles(circle_num = 10):  
    global circles_exist
    
    ec = Image.open("./images/EmptyCircle.png")
    ec = ec.resize((32,32))
    ec = ImageTk.PhotoImage(ec)
    
    # Save as reference of image to avoid garbage collection
    ec_reference = Canvas(root)
    ec_reference.image = ec 
    
    # Destroy anything existing in circle_frame
    for widget in circle_frame.winfo_children():
        widget.destroy()
        widget.pack_forget()
    
    for i in range(circle_num):        
        ec_label = Label(circle_frame, image = ec, borderwidth = 0, highlightthickness = 0)
        ec_label.pack(side = LEFT, padx=0, anchor = 'center', expand = True)
        
    print(type(circle_frame.winfo_children()[1]))

trial_number = 0

def correct_circle():
    global trial_number
    gc = Image.open("./images/GreenCircle.png")
    gc = gc.resize((32,32))
    gc = ImageTk.PhotoImage(gc)
    
    gc_reference = Canvas(root)
    gc_reference.image = gc 
    # Get number of circles
    total_trials = len(circle_frame.winfo_children())
    
    if trial_number < total_trials:
        circle_frame.winfo_children()[trial_number].configure(image = gc)
        pass
    
    print("Correct!")
    trial_number += 1
    
    if trial_number == total_trials:
        print ("Done")
        trial_number = 0
    
def incorrect_circle():
    global trial_number
    rc = Image.open("./images/RedCircle.png")
    rc = rc.resize((32,32))
    rc = ImageTk.PhotoImage(rc)
    
    rc_reference = Canvas(root)
    rc_reference.image = rc 
    # Get number of circles
    total_trials = len(circle_frame.winfo_children())
    
    if trial_number < total_trials:
        circle_frame.winfo_children()[trial_number].configure(image = rc)
        
    print("Incorrect :(")
    trial_number += 1
    
    if trial_number == total_trials:
        print ("Done")
        trial_number = 0
        
    
button_frame = Frame(root)
button_frame.pack(anchor = 'center', pady = 10)

'''
correct_btn = tb.Button(button_frame, 
                    text = "Correct", 
                    command = correct_circle, 
                    bootstyle = "success")
correct_btn.pack(side = LEFT, anchor = 'center', pady=5)

incorrect_btn = tb.Button(button_frame, 
                    text = "Incorrect", 
                    command = incorrect_circle, 
                    bootstyle = "danger")
incorrect_btn.pack(side = LEFT, anchor = 'center', pady=5)
'''

        
        
root.mainloop()


'''
---------
| TO-DO |
--------
- Map input device to int and use that for play_game() input!
- Input for trials and time_per_guess
- Play button (greys out then plays game with trial & time_per_guess inputs)
- High scores window --> Pop up (?) with list of all trials & time_per_guess combinations, then juts brings up filtered database.
- Commonly missed notes --> Plot? List?

- Re-write play_game function so that it turns UI background green if correct & red if wrong. Split into:
    - Return string + low/high + note
    - Record & judge --> Return correct/incorrect + played note vs target note if incorrect
- Add a circle display of correct/incorrect. 
    - Display number of trials in unfilled circles, then fill each one either green or red depending on if correct/incorrect
    - play_game() function makes empty array and fills with 0 for incorrect, 1 for correct? Or array of 0s and -1 for incorrect, 1 for correct.
        - How to pass to UI?
'''



