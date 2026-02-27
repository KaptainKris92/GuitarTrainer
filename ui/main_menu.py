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
        max_string = len(max(self.input_devices, key=len)) if self.input_devices else 30

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

        # Set default device if any are available
        if self.input_devices:
            self.device_combo.current(0)
        else:
            self.device_label.config(text="No input device found")
            self.select_device_btn.configure(state="disabled")

        # 'Tuner' button
        self.tuner_btn = tb.Button(self,
                                   text="Tuner",
                                   command=self.launch_tuner,
                                   style="primary.TButton")

        self.tuner_btn.pack(pady=5)

        # 'Note trainer' button
        self.ntp_btn = tb.Button(self,
                                 text="Note Trainer",
                                 command=self.launch_note_trainer,
                                 style="primary.TButton")
        self.ntp_btn.pack(pady=5)
        if not self.input_devices:
            self.tuner_btn.configure(state="disabled")
            self.ntp_btn.configure(state="disabled")

        # 'Quit' button
        self.exit_btn = tb.Button(self,
                                  text="Quit",
                                  command=self.exit_app,
                                  style="danger.TButton"
                                  )
        self.exit_btn.pack(pady=5)

    def device_confirmation(self):
        try:
            device_id = self._selected_input_device_id()
            self.device_label.config(text=f"Input device {device_id} selected")
        except ValueError:
            self.device_label.config(text="Please select a valid input device")

    def launch_tuner(self):
        tuner = TunerUI(self._selected_input_device_id(), self)
        self.withdraw()

    def launch_note_trainer(self):
        ntp = NoteTrainerUI(input_device=self._selected_input_device_id(), main_menu=self)
        self.withdraw()

    def exit_app(self):
        self.destroy()
        self.quit()

    def _selected_input_device_id(self):
        selected = self.device_combo.get().strip()
        if not selected.startswith("Input Device "):
            raise ValueError("No valid device selected")
        return int(selected.split(" - ", 1)[0].replace("Input Device ", ""))
