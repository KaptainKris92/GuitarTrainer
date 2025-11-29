from functions.get_device_list import DeviceLister
import ttkbootstrap as tb
from ui.note_trainer_ui import NoteTrainerUI
from ui.tuner_ui import TunerUI


class MainMenu(tb.window.Window):
    def __init__(self):
        super().__init__(title="Guitar Trainer", themename="superhero")
        # super(MainMenu, self).__init__(title = "Guitar Trainer")

        app_width = 1080
        app_height = 720

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculating where to put top-left corner of window
        # Middle point of screen minus (w & h of app / 2)
        x = (screen_width / 2) - (app_width / 2)
        y = (screen_height / 2) - (app_height / 2)

        self.geometry(f"{app_width}x{app_height}+{int(x)}+{int(y)}")

        mm_title = tb.Label(self,
                            text="Guitar Trainer",
                            font=("Helvetica", 28)).pack(pady=10)    

        # Select input device
        self.dl = DeviceLister()
        self.input_devices = self.dl.show_devices("input")
        max_string = len(max(self.input_devices, key=len))

        self.device_label = tb.Label(
            self, text="Select input device", font=("Helvetica", 18)
        )
        self.device_label.pack(pady=5)  # Specify padding

        self.device_combo = tb.Combobox(self,
                                        values=self.input_devices,
                                        width=max_string)
        self.device_combo.pack(pady=10)

        self.select_device_btn = tb.Button(self,
                                           text="Select device",
                                           command=self.device_confirmation,
                                           style="success.TButton")
        
        self.select_device_btn.pack(pady=5)

        # Set default device
        self.device_combo.current(2)

        # 'Tuner' button
        self.tuner_btn = tb.Button(self,
                                   text="Tuner",
                                   command=self.launch_tuner,
                                   style="primary.Tbutton")
        
        self.tuner_btn.pack(pady=5)

        # 'Note trainer' button
        self.ntp_btn = tb.Button(self,
                                 text="Note Trainer",
                                 command=self.launch_note_trainer,
                                 style="primary.TButton")
        self.ntp_btn.pack(pady=5)

        # 'Quit' button
        self.exit_btn = tb.Button(self,
                                  text="Quit",
                                  command=self.exit_app,
                                  style="danger.TButton"
                                  )
        self.exit_btn.pack(pady=5)

    def device_confirmation(self):
        device_id = self.input_devices.index(self.device_combo.get())
        self.device_label.config(text=f"Device {device_id} selected")

    def launch_tuner(self):
        tuner = TunerUI(self.input_devices.index(
            self.device_combo.get()), self)
        self.withdraw()
        
    def launch_note_trainer(self):
        ntp = NoteTrainerUI(self.input_devices.index(
            self.device_combo.get()), self)
        self.withdraw()

    def exit_app(self):
        self.destroy()
        self.quit()
