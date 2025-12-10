import sys
import os
import ttkbootstrap as tb
import numpy as np

from tuner_utils.audio_analyser import AudioAnalyser
from tuner_utils.threading_helper import ProtectedList
from tuner_utils.tuner_frame import MainFrame
from tuner_utils.settings import Settings

from managers.color_manager import ColorManager
from managers.image_manager import ImageManager
from managers.font_manager import FontManager
from managers.timing import Timer


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
        
        self.main_frame = MainFrame(self)

        # Start the audio analyser 
        self.frequency_queue = ProtectedList()        
        self.audio_analyser = AudioAnalyser(queue = self.frequency_queue, device_index = input_device)
        self.audio_analyser.start()
        
        self.needle_buffer_array = np.zeros(Settings.NEEDLE_BUFFER_LENGTH)
        self.tone_hit_counter = 0
        self.note_number_counter = 0
        self.nearest_note_number_buffered = 69
        self.a4_frequency = 440        
        
        self.draw_main_frame()
        
        self.timer = Timer(Settings.FPS)
            
        # For debugging:
        # Periodic polling of queue (prevents while loop from blocking thread)
        self.poll_frequency_queue()
                    
    def go_main_menu(self):
        self.main_menu.deiconify()
        self.audio_analyser.running = False
        # Ensures thread has fully stopped
        self.audio_analyser.join()
        self.withdraw()
        
    def draw_main_frame(self, event=0):
        self.tuner_frame.place(relx=0, rely=0, relheight=1, relwidth=1)
        
    def on_closing(self, event=0):
        self.audio_analyser.running = False
        # Ensures thread has fully stopped
        self.audio_analyser.join()
        self.destroy()
        
    def poll_frequency_queue(self):
        '''Periodically checks the frequency queue without blocking the UI. This is also responsible for updating the UI'''
        freq = self.frequency_queue.get()
        
        # DEBUGGING
        if freq is not None:
            print(
                "Loudest frequency:", freq,
                "\nNearest note:", self.audio_analyser.frequency_to_note_name(freq, 440)
            )
        # Method runs again every 50ms
        # self.after(50, self.poll_frequency_queue)
                        
        try:
            # get the current frequency from the queue
            freq = self.frequency_queue.get()
            if freq is not None:
                # convert frequency to note number
                number = self.audio_analyser.frequency_to_number(freq, self.a4_frequency)

                # calculate nearest note number, name and frequency
                nearest_note_number = round(number)
                nearest_note_freq = self.audio_analyser.number_to_frequency(nearest_note_number, self.a4_frequency)

                # calculate frequency difference from freq to nearest note
                freq_difference = nearest_note_freq - freq

                # calculate the frequency difference to the next note (-1)
                semitone_step = nearest_note_freq - self.audio_analyser.number_to_frequency(round(number-1),
                                                                                            self.a4_frequency)

                # calculate the angle of the display needle
                needle_angle = -90 * ((freq_difference / semitone_step) * 2) if semitone_step != 0 else 0

                # buffer the current nearest note number change
                if nearest_note_number != self.nearest_note_number_buffered:
                    self.note_number_counter += 1
                    if self.note_number_counter >= Settings.HITS_TILL_NOTE_NUMBER_UPDATE:
                        self.nearest_note_number_buffered = nearest_note_number
                        self.note_number_counter = 0

                # if needle in range +-5 degrees then make it green, otherwise red
                if abs(freq_difference) < 0.25:
                    self.main_frame.set_needle_color("green")
                    self.tone_hit_counter += 1
                else:
                    self.main_frame.set_needle_color("red")
                    self.tone_hit_counter = 0

                # after 7 hits of the right note in a row play the sound
                # Sound temporarily removed to get main functionality working. TODO: Re-implement sound thread 
                if self.tone_hit_counter > 7:
                    self.tone_hit_counter = 0

                # update needle buffer array
                self.needle_buffer_array[:-1] = self.needle_buffer_array[1:]
                self.needle_buffer_array[-1:] = needle_angle

                # update ui note labels and display needle
                self.main_frame.set_needle_angle(np.average(self.needle_buffer_array))
                self.main_frame.set_note_names(note_name=self.audio_analyser.number_to_note_name(self.nearest_note_number_buffered),
                                                note_name_lower=self.audio_analyser.number_to_note_name(self.nearest_note_number_buffered - 1),
                                                note_name_higher=self.audio_analyser.number_to_note_name(self.nearest_note_number_buffered + 1))

                # calculate difference in cents
                if semitone_step == 0:
                    diff_cents = 0
                else:
                    diff_cents = (freq_difference / semitone_step) * 100
                    
                freq_label_text = f"+{round(-diff_cents, 1)} cents" if -diff_cents > 0 else f"{round(-diff_cents, 1)} cents"
                self.main_frame.set_frequency_difference(freq_label_text)

                # set current frequency
                if freq is not None: self.main_frame.set_frequency(freq)            

        except IOError as err:
            sys.stderr.write('Error: Line {} {} {}\n'.format(sys.exc_info()[-1].tb_lineno, type(err).__name__, err))
            
        # Next poll in X milliseconds
        self.after(Settings.GUI_UPDATE_INTERVAL_MS, self.poll_frequency_queue)