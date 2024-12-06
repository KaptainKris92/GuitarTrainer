import ttkbootstrap as tb
import matplotlib as plt
from sql_funcs import get_top_incorrect

class NoteTrainerMissedNotesUI(tb.window.Toplevel):
    def __init__(self, note_trainer_ui):
        
        super(NoteTrainerMissedNotesUI, self).__init__(
        title="Note Trainer - Top missed notes")
        
        self.note_trainer_ui = note_trainer_ui

        app_width = 1000
        app_height = 500

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)

        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")

        page_title = tb.Label(self,
                              text="Note Trainer - Top missed notes",
                              font=("Helvetica", 25))
        page_title.pack(pady=5)
        
        back_btn = tb.Button(self,
                             text="Back",
                             command=self.back_btn_action,
                             style="secondary.TButton"
                             )
        back_btn.pack(pady=5)
        
    def back_btn_action(self):
        self.note_trainer_ui.deiconify()
        self.withdraw()
