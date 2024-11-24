from main import show_devices, play_game
from tkinter import *
import ttkbootstrap as tb
from PIL import Image, ImageTk

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
    #play_game(input_device_id = device_id, time_per_guess = time_per_guess, trials = trials)
    display_circles(trials)

            

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

def correct():
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
    
def incorrect():
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

correct_btn = tb.Button(button_frame, 
                    text = "Correct", 
                    command = correct, 
                    bootstyle = "success")
correct_btn.pack(side = LEFT, anchor = 'center', pady=5)

incorrect_btn = tb.Button(button_frame, 
                    text = "Incorrect", 
                    command = incorrect, 
                    bootstyle = "danger")
incorrect_btn.pack(side = LEFT, anchor = 'center', pady=5)
        
        
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



