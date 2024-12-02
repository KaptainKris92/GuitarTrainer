import ttkbootstrap as tb
from ttkbootstrap.tableview import Tableview
from sql_funcs import get_trial_time_combos, get_highscores
import datetime


class NoteTrainerScoreUI(tb.window.Toplevel):
    def __init__(self, note_trainer_ui):
        super(NoteTrainerScoreUI, self).__init__(
            title="Note Trainer Highscores")
        self.note_trainer_ui = note_trainer_ui

        app_width = 1000
        app_height = 500

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)

        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")

        page_title = tb.Label(self,
                              text="Note Trainer Highscores",
                              font=("Helvetica", 25))
        page_title.pack(pady=5)

        self.past_combos = get_trial_time_combos()

        combo_list = []        
        for i in self.past_combos:
            combo_list.append(f"Trials: {i[0]} | Time per trial: {i[1]}")        
        max_string = len(max(combo_list, key=len))
        
        self.combo_select = tb.Combobox(self,
                                        values=combo_list,
                                        width=max_string)
        self.combo_select.bind('<<ComboboxSelected>>', self.combo_selected)
        self.combo_select.pack(pady=10)

        self.table_columns = [
            {"text": "Date", "stretch": False},
            {"text": "Game ID", "stretch": False},
            #{"text": "Time per guess (s)", "stretch": False},
            #{"text": "Trials", "stretch": False},
            {"text": "# Correct", "stretch": False}
        ]

        self.row_data = []        

        self.highscore_table = Tableview(
            master=self,
            coldata=self.table_columns,
            rowdata=self.row_data,
            paginated=False,
            autofit=True,
            searchable=False)
        
        self.highscore_table.pack(pady=10)
        
        back_btn = tb.Button(self,
                             text="Back",
                             command=self.back_btn_action,
                             style="secondary.TButton"
                             )
        back_btn.pack(pady=5)

    def combo_selected(self, event):    
        trials = self.past_combos[self.combo_select.current()][0] 
        time_per_guess = self.past_combos[self.combo_select.current()][1]
        
        print (f"Trials: {trials}, Timer: {time_per_guess}")
        highscores = get_highscores(trials, time_per_guess)
        
        # Remove seconds and milliseconds from datetime
        dates_formatted = [x[0].strftime('%Y/%m/%d %H:%M') for x in highscores]
        
        # Replace highscores datetime with formatted version
        formatted_highscores = []
        for i, j in zip(dates_formatted, highscores):
            formatted_highscores.append((i, j[1], j[4]))
            
        self.row_data = formatted_highscores
        self.highscore_table.build_table_data(coldata = self.table_columns, rowdata=self.row_data)        
        self.highscore_table.reset_table() # To make sure it doesn't expand

    def back_btn_action(self):
        self.note_trainer_ui.deiconify()
        self.withdraw()
