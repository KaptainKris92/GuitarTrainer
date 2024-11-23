from main import show_devices, play_game
from tkinter import *
import ttkbootstrap as tb

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


trials_label = tb.Label(root, text = "Select number of trials", font = ("Helvetica", 18))
trials_label .pack(pady=5) # Specify padding

trials_input = Entry(root)
trials_input.pack(pady=5)




play_btn = tb.Button(root, 
                    text = "Play", 
                    command = play_button_action, 
                    bootstyle = "success")
play_btn.pack(pady=5)




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

- Re-write play_game function so that it turns UI background green if correct & red if wrong.

'''



