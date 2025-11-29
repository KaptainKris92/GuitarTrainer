import ttkbootstrap as tb
from functions.sql_funcs import create_incorrect_bar_chart
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class NoteTrainerMissedNotesUI(tb.window.Toplevel):
    def __init__(self, note_trainer_ui):
        
        super(NoteTrainerMissedNotesUI, self).__init__(
        title="Note Trainer - Top 10 missed notes")
        
        self.note_trainer_ui = note_trainer_ui

        app_width = 1080
        app_height = 720

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)

        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")        
        
        page_title = tb.Label(self,
                              text="Note Trainer - Top 10 missed notes",
                              font=("Helvetica", 25))
        page_title.pack(pady=5)
        
        top_n_container = tb.Frame(self)
        top_n_container.pack(anchor='center', pady=5)
        
        label1 = tb.Label(top_n_container, 
                          text = "Top")
        label1.pack(side="left", pady=10)
        self.top_n = tb.Combobox(top_n_container,
                                 values=list(range(1, 21)),
                                 width = 2)
        self.top_n.current(10)
        self.top_n.bind('<<ComboboxSelected>>', self.plot_incorrect)
        self.top_n.pack(side="left",pady=10)
        label2 = tb.Label(top_n_container, 
                          text = "missed notes")
        label2.pack(side="left",pady=10)
        
        
        back_btn = tb.Button(self,
                             text="Back",
                             command=self.back_btn_action,
                             style="secondary.TButton"
                             )
        back_btn.pack(pady=5)
        
        self.fig = create_incorrect_bar_chart(10)
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master = self)
        self.plot_canvas.get_tk_widget().pack(side="top", fill = None, expand = False)                        
        self.plot_canvas.draw()
        
    def plot_incorrect(self, event):                                    
        self.plot_canvas.get_tk_widget().pack_forget() 
        self.fig = create_incorrect_bar_chart(self.top_n.get())                
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master = self)        
        self.plot_canvas.get_tk_widget().pack(side="top", fill = None, expand = False)               
        self.update()
        
        
    def back_btn_action(self):
        self.note_trainer_ui.deiconify()
        self.withdraw()
