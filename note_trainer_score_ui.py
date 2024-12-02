import ttkbootstrap as tb
from sql_funcs import get_trial_time_combos

class NoteTrainerScoreUI(tb.window.Toplevel):
    def __init__(self, note_trainer_ui):
        super(NoteTrainerScoreUI, self).__init__(title = "Note Trainer Highscores") 
        self.note_trainer_ui = note_trainer_ui
        
        app_width = 1000
        app_height = 500
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight() 
        
        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)
        
        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")           
        
        page_title = tb.Label(self,
                              text = "Note Trainer Highscores",
                                  font = ("Helvetica", 25))
        page_title.pack(pady=5)
        
        past_combos = get_trial_time_combos()
        max_string = len(max(past_combos, key = len))
        self.combo_select = tb.Combobox(self,
                                        values=past_combos,
                                        width = max_string)
        self.combo_select.pack(pady=10)
        
        back_btn = tb.Button(self,
                             text = "Back",
                             command=self.back_btn_action,
                             style="secondary.TButton"
                             )
        back_btn.pack(pady=5)
        
    def show_highscore(self, trials, time_per_guess):
        pass       
        
    def back_btn_action(self):    
        self.note_trainer_ui.deiconify()
        self.withdraw()
        pass
    