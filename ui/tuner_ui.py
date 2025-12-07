import os
import ttkbootstrap as tb
from tuner_functions.audio_analyser import AudioAnalyser
from tuner_functions.threading_helper import ProtectedList
from tuner_functions.tuner_frame import MainFrame

from tuner_functions.color_manager import ColorManager
from tuner_functions.image_manager import ImageManager
from tuner_functions.font_manager import FontManager

class TunerUI(tb.window.Toplevel):
    def __init__(self, input_device, main_menu):
        # UI window config
        super(TunerUI, self).__init__(title = "Guitar Tuner")        
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
                             text = "Tuner",
                             font = ("Helvetica", 28))
        ntp_title.pack(pady=5)
        
        # Tuner components from Tom's project
        self.color_manager = ColorManager()
        self.font_manager = FontManager()
        # self.main_path = os.path.dirname(os.path.abspath(__file__))
        self.main_path = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
        self.image_manager = ImageManager(self.main_path)
        
        self.tuner_frame = MainFrame(self)
        
        # Main menu button
        mm_btn = tb.Button(self,
                           text = "Main menu",
                           command = self.go_main_menu,
                           style="primary.TButton"
                           )
        mm_btn.pack(pady=5)

        # Start the aduio analyser 
        self.frequency_queue = ProtectedList()        
        self.audio_analyser = AudioAnalyser(self.frequency_queue)
        self.audio_analyser.start()
        
        # For debugging
        while True:
            self.frequency_queue_data = self.frequency_queue.get()
            if self.frequency_queue_data is not None:
                print ("Loudest frequency:", self.frequency_queue_data, "\nNearest note:", self.audio_analyser.frequency_to_note_name(self.frequency_queue_data, 440))
        
        
    
    def go_main_menu(self):
        self.main_menu.deiconify()
        self.withdraw()
        
        

    