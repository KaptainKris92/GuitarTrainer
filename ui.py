from main import show_devices, play_game
from tkinter import *
import ttkbootstrap as tb
from PIL import Image, ImageTk

class MainMenu:
    def __init__(self):
        self.root = tb.Window(themename = "superhero")
        self.input_devices = show_devices("input")
        self.root.title("Guitar Trainer")
        self.root.geometry("1000x500")
        
        self.device_label = tb.Label(self.root, text = "Select input device", font = ("Helvetica", 18))
        self.device_label.pack(pady=30) # Specify padding
        
        self.device_combo = tb.Combobox(self.root, bootstyle = "success", values = self.input_devices)
        self.device_combo.pack(pady=10)

        self.select_device_btn = tb.Button(self.root, 
                                      text = "Select device", 
                                      command = self.device_confirmation, 
                                      bootstyle = "danger")
        self.select_device_btn.pack(pady=5)
        
        # Set default device
        self.device_combo.current(2)

        # Bind combobox - Automatically sets the selection when clicked, instead of requiring a button press.
        #device_combo.bind("<<ComboboxSelected>>", click_bind)

        self.time_per_guess_label = tb.Label(self.root, text = "Select time per guess (seconds)", font = ("Helvetica", 18))
        self.time_per_guess_label.pack(pady=5) # Specify padding

        self.time_per_guess_input = Entry(self.root)
        self.time_per_guess_input.pack(pady=5)
        self.time_per_guess_input.insert(0, "1")
        
        
        self.trials_label = tb.Label(self.root, text = "Select number of trials", font = ("Helvetica", 18))
        self.trials_label.pack(pady=5) # Specify padding
        
        self.trials_input = Entry(self.root)
        self.trials_input.pack(pady=5)
        self.trials_input.insert(0, "10")
        
        self.play_btn = tb.Button(self.root, 
                            text = "Play", 
                            command = self.play_button_action, 
                            bootstyle = "success")
        self.play_btn.pack(pady=5)
        
        self.circle_frame = Frame(self.root)
        self.circle_frame.pack(anchor = 'center', pady = 10)
        
        
        
        self.button_frame = Frame(self.root)
        self.button_frame.pack(anchor = 'center', pady = 10)

        correct_btn = tb.Button(self.button_frame, 
                            text = "Correct", 
                            command = self.correct, 
                            bootstyle = "success")
        correct_btn.pack(side = LEFT, anchor = 'center', pady=5)

        incorrect_btn = tb.Button(self.button_frame, 
                            text = "Incorrect", 
                            command = self.incorrect, 
                            bootstyle = "danger")
        incorrect_btn.pack(side = LEFT, anchor = 'center', pady=5)
        
        self.trial_number = 0
        self.circles_exist = False
                
    def device_confirmation(self):
        #device_label.config(text = f"{device_combo.get()} selected")
        device_id = self.input_devices.index(self.device_combo.get())
        self.device_label.config(text = f"Device {device_id} selected")
        
    # Automatic selection binding on click of combobox option.
    # e = event
    def click_bind(self, e):
        self.device_label.config(text = f"{device_combo.get()} selected")
        
    def play_button_action(self):
        time_per_guess = int(self.time_per_guess_input.get())
        trials = int(self.trials_input.get())
        device_id = self.input_devices.index(self.device_combo.get())
        #play_game(input_device_id = device_id, time_per_guess = time_per_guess, trials = trials)
        self.display_circles(trials)

    
    def display_circles(self, circle_num = 10):  
        self.circles_exist
        
        ec = Image.open("./images/EmptyCircle.png")
        ec = ec.resize((32,32))
        ec = ImageTk.PhotoImage(ec)
        
        # Save as reference of image to avoid garbage collection
        ec_reference = Canvas(self.root)
        ec_reference.image = ec 
        
        # Destroy anything existing in circle_frame
        for widget in self.circle_frame.winfo_children():
            widget.destroy()
            widget.pack_forget()
        
        for i in range(circle_num):        
            ec_label = Label(self.circle_frame, image = ec, borderwidth = 0, highlightthickness = 0)
            ec_label.pack(side = LEFT, padx=0, anchor = 'center', expand = True)
            
        #print(type(circle_frame.winfo_children()[1]))    
    
    def correct(self):
        self.trial_number
        gc = Image.open("./images/GreenCircle.png")
        gc = gc.resize((32,32))
        gc = ImageTk.PhotoImage(gc)
        
        gc_reference = Canvas(self.root)
        gc_reference.image = gc 
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())
        
        if self.trial_number < total_trials:
            self.circle_frame.winfo_children()[self.trial_number].configure(image = gc)
            pass
        
        print("Correct!")
        self.trial_number += 1
        
        if self.trial_number == total_trials:
            print ("Done")
            self.trial_number = 0
        
    def incorrect(self):
        self.trial_number
        rc = Image.open("./images/RedCircle.png")
        rc = rc.resize((32,32))
        rc = ImageTk.PhotoImage(rc)
        
        rc_reference = Canvas(self.root)
        rc_reference.image = rc 
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())
        
        if self.trial_number < total_trials:
            self.circle_frame.winfo_children()[self.trial_number].configure(image = rc)
            
        print("Incorrect :(")
        self.trial_number += 1
        
        if self.trial_number == total_trials:
            print ("Done")
            self.trial_number = 0
            
    def start(self):
        #root.mainloop()
        self.root.mainloop()
        
        
if __name__ == '__main__':
    app = MainMenu()
    app.start()
        
    



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



