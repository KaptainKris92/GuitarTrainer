from note_trainer import NoteTrainer
from get_device_list import DeviceLister
from tkinter import Entry, Frame, Canvas, Label
import ttkbootstrap as tb
from PIL import Image, ImageTk
from sql_funcs import get_current_game_id, insert_trial, insert_final_score, get_best_score


class MainMenu:
    def __init__(self):
        self.dl = DeviceLister()
        self.root = tb.Window(themename="superhero")
        self.input_devices = self.dl.show_devices("input")
        self.root.title("Guitar Trainer")
        self.root.geometry("1000x500")

        self.device_label = tb.Label(
            self.root, text="Select input device", font=("Helvetica", 18))
        self.device_label.pack(pady=30)  # Specify padding

        self.device_combo = tb.Combobox(
            self.root, bootstyle="success", values=self.input_devices)
        self.device_combo.pack(pady=10)

        self.select_device_btn = tb.Button(self.root,
                                           text="Select device",
                                           command=self.device_confirmation,
                                           bootstyle="danger")
        self.select_device_btn.pack(pady=5)

        # Set default device
        self.device_combo.current(2)

        # Bind combobox - Automatically sets the selection when clicked, instead of requiring a button press.
        # device_combo.bind("<<ComboboxSelected>>", click_bind)

        self.time_per_guess_label = tb.Label(
            self.root, text="Select time per guess (seconds)", font=("Helvetica", 18))
        self.time_per_guess_label.pack(pady=5)  # Specify padding

        self.time_per_guess_input = Entry(self.root)
        self.time_per_guess_input.pack(pady=5)
        self.time_per_guess_input.insert(0, "1")

        self.trials_label = tb.Label(
            self.root, text="Select number of trials", font=("Helvetica", 18))
        self.trials_label.pack(pady=5)  # Specify padding

        self.trials_input = Entry(self.root)
        self.trials_input.pack(pady=5)
        self.trials_input.insert(0, "10")

        self.play_btn = tb.Button(self.root,
                                  text="Play",
                                  command=self.play_button_action,
                                  bootstyle="success")
        self.play_btn.pack(pady=5)

        self.circle_frame = Frame(self.root)
        self.circle_frame.pack(anchor='center', pady=10)

        self.button_frame = Frame(self.root)
        self.button_frame.pack(anchor='center', pady=10)

        self.correct_btn = tb.Button(self.button_frame,
                                text="Correct",
                                command=self.correct,
                                bootstyle="success")
        self.correct_btn.pack(side='left', anchor='center', pady=5)

        self.incorrect_btn = tb.Button(self.button_frame,
                                  text="Incorrect",
                                  command=self.incorrect,
                                  bootstyle="danger")
        self.incorrect_btn.pack(side='left', anchor='center', pady=5)

        self.exit_btn = tb.Button(self.root,
                                  text="Quit",
                                  command=self.exit_app,
                                  bootstyle="Danger"
                                  )
        self.exit_btn.pack()

        self.trial_number = 0
        self.circles_exist = False

    def device_confirmation(self):
        # device_label.config(text = f"{device_combo.get()} selected")
        device_id = self.input_devices.index(self.device_combo.get())
        self.device_label.config(text=f"Device {device_id} selected")

    '''
    # Automatic selection binding on click of combobox option.
    # e = event
    def click_bind(self, e):
        self.device_label.config(text = f"{device_combo.get()} selected")
    '''

    def play_button_action(self):
        time_per_guess = int(self.time_per_guess_input.get())
        trials = int(self.trials_input.get())
        device_id = self.input_devices.index(self.device_combo.get())
        
        self.display_circles(trials)
        # Note game logic
        num_correct = 0
        game_id = get_current_game_id()

        nt = NoteTrainer(device_id)
        
        for i in range(trials):
            result = nt.play_game(time_per_guess)
            
            if result['correct']:
                self.correct()
                num_correct += 1
                insert_trial(game_id,
                                  time_per_guess,
                                  trials,
                                  i + 1,
                                  result['string'],
                                  result['low_high'],
                                  result['note'],
                                  result['played_note'],
                                  True)
                
            elif not result['correct']:
                self.incorrect()
                
                insert_trial(game_id,
                             time_per_guess,
                             trials,
                             i + 1,
                             result['string'],
                             result['low_high'],
                             result['note'],
                             result['played_note'],
                             False)
            
            elif result['correct'] is None:
                self.incorrect()
                
                insert_trial(game_id,
                             time_per_guess,
                             trials,
                             i + 1,
                             result['string'],
                             result['low_high'],
                             result['note'],
                             result['played_note'],
                             False)
                            
        print(f"Game over.\n{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.\n{get_best_score(time_per_guess, trials, num_correct)}")
        insert_final_score(game_id, time_per_guess, trials, num_correct)

    def display_circles(self, circle_num=10):
        self.circles_exist

        ec = Image.open("./images/EmptyCircle.png")
        ec = ec.resize((32, 32))
        ec = ImageTk.PhotoImage(ec)

        # Save as reference of image to avoid garbage collection
        ec_reference = Canvas(self.root)
        ec_reference.image = ec

        # Destroy anything existing in circle_frame
        for widget in self.circle_frame.winfo_children():
            widget.destroy()
            widget.pack_forget()

        for i in range(circle_num):
            ec_label = Label(self.circle_frame, image=ec,
                             borderwidth=0, highlightthickness=0)
            ec_label.pack(side='left', padx=0, anchor='center', expand=True)
            
        self.root.update()

        # print(type(circle_frame.winfo_children()[1]))

    def correct(self):
        self.trial_number
        gc = Image.open("./images/GreenCircle.png")
        gc = gc.resize((32, 32))
        gc = ImageTk.PhotoImage(gc)

        gc_reference = Canvas(self.root)
        gc_reference.image = gc
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=gc)
            pass

        print("Correct!")
        self.trial_number += 1
        
        self.root.update()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0
            

    def incorrect(self):
        self.trial_number
        rc = Image.open("./images/RedCircle.png")
        rc = rc.resize((32, 32))
        rc = ImageTk.PhotoImage(rc)

        rc_reference = Canvas(self.root)
        rc_reference.image = rc
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=rc)

        print("Incorrect :(")
        self.trial_number += 1
        
        self.root.update()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0

    def start(self):
        # root.mainloop()
        self.root.mainloop()

    def exit_app(self):
        self.root.destroy()



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
