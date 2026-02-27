from functions.note_trainer import NoteTrainer
from ui.note_trainer_score_ui import NoteTrainerScoreUI
from ui.note_trainer_missed_ui import NoteTrainerMissedNotesUI
from functions.sql_funcs import get_current_game_id, insert_trial, insert_final_score, get_best_score
from PIL import Image, ImageTk
import ttkbootstrap as tb

class NoteTrainerUI(tb.window.Toplevel):
    def __init__(self, input_device, main_menu):
        # UI window config
        super(NoteTrainerUI, self).__init__(title = "Guitar Trainer: Notes")        
        self.main_menu = main_menu
        self.input_device = input_device
        
        app_width = 1080
        app_height = 720
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight() 
        
        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)
        
        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")   
        
        ntp_title = tb.Label(self,
                                  text = "Note Trainer",
                                  font = ("Helvetica", 28))
        ntp_title.pack(pady=5)
        
        # Time per guess input
        time_per_guess_label = tb.Label(self, 
                                             text="Select time per guess (seconds)", 
                                             font=("Helvetica", 18))
        time_per_guess_label.pack(pady=5)  # Specify padding

        self.time_per_guess_input = tb.Entry(self)
        self.time_per_guess_input.pack(pady=5)
        self.time_per_guess_input.insert(0, "1")

        # Number of trials input
        trials_label = tb.Label(
            self, text="Select number of trials", font=("Helvetica", 18))
        trials_label.pack(pady=5)  # Specify padding

        self.trials_input = tb.Entry(self)
        self.trials_input.pack(pady=5)
        self.trials_input.insert(0, "10")

        # Play button
        play_btn = tb.Button(self,
                             text="Play",
                             command=self.play_button_action,
                             style="success.TButton")
        play_btn.pack(pady=5)
        
        # Target note text
        string_frame = tb.Frame(self)
        string_frame.pack(anchor = 'center', pady=5, padx=10)
        
        self.string_num_label = tb.Label(string_frame,
                                         text = "",
                                         font = ("Arial", 30))
        self.string_num_label.pack(side = 'left', padx=5)        
        
        self.low_high_label = tb.Label(string_frame,
                                     text = "",
                                     font = ("Arial", 30))
        self.low_high_label.pack(side = 'left', padx=5)
        
        self.note_label = tb.Label(string_frame,
                                   text = "",
                                   font = ("Arial", 30))
        self.note_label.pack(side = 'left', padx=5)
        
        # Correct/incorrect circles
        self.circle_frame = tb.Frame(self)
        self.circle_frame.pack(anchor='center', pady=5)
                
        # Stats buttons
        high_scores_btn = tb.Button(self,
                                    text = "High scores",
                                    command=self.show_highscores,
                                    style = "secondary.TButton")
        high_scores_btn.pack(pady=5)
        
        worst_notes_btn = tb.Button(self,
                                    text = "Most incorrect notes",
                                    command=self.show_worst_notes,
                                    style = "secondary.TButton")
        worst_notes_btn.pack(pady=5)
        
        # Main menu button
        mm_btn = tb.Button(self,
                           text = "Main menu",
                           command = self.go_main_menu,
                           style="primary.TButton"
                           )
        mm_btn.pack(pady=5)
        
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
            random_note = nt.random_note()
            self.change_text(random_note['string'],
                             random_note['low_high'],
                             random_note['note']
                             )
            result = nt.play_game(time_per_guess, 
                                  string = random_note['string'],
                                  low_high = random_note['low_high'],
                                  note = random_note['note'])
            
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
                            
        self.show_best_score(num_correct, trials, time_per_guess)
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
        
    def change_text(self, string, low_high, note):
        self.string_num_label.config(text=f"{string} string")        
        self.low_high_label.config(text=f"{low_high}")
        self.note_label.config(text=f"{note}")
        self.update()        

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

        self.trial_number += 1
        
        self.update()

        if self.trial_number == total_trials:
            print("Done")
            self.trial_number = 0
            
    def show_best_score(self, num_correct, trials, time_per_guess):
        print(f"Game over.\n{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.\n{get_best_score(time_per_guess, trials, num_correct)}")
        self.string_num_label.config(text="Game over.",
                                     font = ("Arial", 20))        
        self.low_high_label.config(text=f"{num_correct}/{trials} ({round(num_correct/trials * 100)}%) correct.",
                                   font = ("Arial", 20))
        self.note_label.config(text=f"{get_best_score(time_per_guess, trials, num_correct)}",
                               font = ("Arial", 20))
        self.update()
        
    def show_highscores(self):
        ntsui = NoteTrainerScoreUI(self)
        self.withdraw()        
    
    def show_worst_notes(self):
        ntmnui = NoteTrainerMissedNotesUI(self)
        self.withdraw()        
        pass
    
    def go_main_menu(self):
        self.main_menu.deiconify()
        self.withdraw()
        
        

    