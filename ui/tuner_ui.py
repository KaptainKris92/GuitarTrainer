import ttkbootstrap as tb

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
        
        # Main menu button
        mm_btn = tb.Button(self,
                           text = "Main menu",
                           command = self.go_main_menu,
                           style="primary.TButton"
                           )
        mm_btn.pack(pady=5)
        
    
    def go_main_menu(self):
        self.main_menu.deiconify()
        self.withdraw()
        
        

    