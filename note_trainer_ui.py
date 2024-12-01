from note_trainer import NoteTrainer
from sql_funcs import get_current_game_id, insert_trial, insert_final_score, get_best_score
from PIL import Image, ImageTk
import ttkbootstrap as tb

class NoteTrainerUI(tb.window.Toplevel):
    def __init__(self, input_device, main_menu):
        super(NoteTrainerUI, self).__init__(title = "Guitar Trainer: Notes")        
        self.main_menu = main_menu
        self.input_device = input_device
        
        app_width = 1000
        app_height = 500
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight() 
        
        # Calculating where to put top-left corner of window
        # Middle point of screen minus (w & h of app / 2)
        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)
        
        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")   
        #self.geometry(f"{app_width}x{app_height}")
        
        self.time_per_guess_label = tb.Label(self, 
                                             text="Select time per guess (seconds)", 
                                             font=("Helvetica", 18))
        self.time_per_guess_label.pack(pady=5)  # Specify padding

        self.time_per_guess_input = tb.Entry(self)
        self.time_per_guess_input.pack(pady=5)
        self.time_per_guess_input.insert(0, "1")

        self.trials_label = tb.Label(
            self, text="Select number of trials", font=("Helvetica", 18))
        self.trials_label.pack(pady=5)  # Specify padding

        self.trials_input = tb.Entry(self)
        self.trials_input.pack(pady=5)
        self.trials_input.insert(0, "10")

        self.play_btn = tb.Button(self,
                                  text="Play",
                                  command=self.play_button_action,
                                  style="success.TButton")
        self.play_btn.pack(pady=5)

        self.circle_frame = tb.Frame(self)
        self.circle_frame.pack(anchor='center', pady=10)

        self.button_frame = tb.Frame(self)
        self.button_frame.pack(anchor='center', pady=10)

        self.correct_btn = tb.Button(self.button_frame,
                                text="Correct",
                                command=self.correct,
                                style="success.TButton")
        self.correct_btn.pack(side='left', anchor='center', pady=5)

        self.incorrect_btn = tb.Button(self.button_frame,
                                  text="Incorrect",
                                  command=self.incorrect,
                                  style="danger.TButton")
        self.incorrect_btn.pack(side='left', anchor='center', pady=5)
        
        self.mm_btn = tb.Button(self,
                                text = "Main menu",
                                command = self.go_main_menu,
                                style="primary.TButton"
                                )
        self.mm_btn.pack()
        
        self.trial_number = 0
        self.circles_exist = False
        
    def play_button_action(self):
        time_per_guess = int(self.time_per_guess_input.get())
        trials = int(self.trials_input.get())
        device_id = self.input_device
        
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
        ec_reference = tb.Label(self)
        ec_reference.image = ec

        # Destroy anything existing in circle_frame
        for widget in self.circle_frame.winfo_children():
            widget.destroy()
            widget.pack_forget()

        for i in range(circle_num):
            ec_label = tb.Label(self.circle_frame, 
                                image=ec,
                                borderwidth=0)
            ec_label.pack(side='left', padx=0, anchor='center', expand=True)
            
        self.update()

        # print(type(circle_frame.winfo_children()[1]))

    def correct(self):
        self.trial_number
        gc = Image.open("./images/GreenCircle.png")
        gc = gc.resize((32, 32))
        gc = ImageTk.PhotoImage(gc)

        gc_reference = tb.Label(self)
        gc_reference.image = gc
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=gc)
            pass

        print("Correct!")
        self.trial_number += 1
        
        self.update()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0
            

    def incorrect(self):
        self.trial_number
        rc = Image.open("./images/RedCircle.png")
        rc = rc.resize((32, 32))
        rc = ImageTk.PhotoImage(rc)

        rc_reference = tb.Label(self)
        rc_reference.image = rc
        # Get number of circles
        total_trials = len(self.circle_frame.winfo_children())

        if self.trial_number < total_trials:
            self.circle_frame.winfo_children(
            )[self.trial_number].configure(image=rc)

        print("Incorrect :(")
        self.trial_number += 1
        
        self.update()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0
        
    def go_main_menu(self):
        self.main_menu.deiconify()
        self.withdraw()
        
        

    