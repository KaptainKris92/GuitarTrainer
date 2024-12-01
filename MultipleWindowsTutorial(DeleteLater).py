from get_device_list import DeviceLister
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
  
 
LARGEFONT =("Verdana", 35)
  
class tkinterApp(tk.Tk):
     
    # __init__ function for class tkinterApp 
    def __init__(self, *args, **kwargs): 
         
        self.dl = DeviceLister()
        # __init__ function for class Tk
        tk.Tk.__init__(self, *args, **kwargs)
         
        self.root = tb.Window(themename="superhero")
        self.input_devices = self.dl.show_devices("input")
        
        self.root.title("Guitar Trainer")
        self.root.geometry("1000x500")
        
        # creating a container
        #container = tk.Frame(self)  
        #container.pack(side = "top", fill = "both", expand = True) 
        #self.root.grid_rowconfigure(0, weight = 1)
        #self.root.grid_columnconfigure(0, weight = 1)
  
        # initializing frames to an empty array
        self.frames = {}  
  
        # iterating through a tuple consisting
        # of the different page layouts
        for F in (MainMenu, NoteTrainer):
  
            frame = F(self.root, self)
  
            # initializing frame of that object from
            # startpage, page1, page2 respectively with 
            # for loop
            self.frames[F] = frame 
  
            #frame.grid(row = 0, column = 0, sticky ="nsew")
  
        self.show_frame(MainMenu)
  
    # to display the current frame passed as
    # parameter
    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
  
# first window frame startpage
  
class MainMenu(tk.Frame):
    def __init__(self, parent, controller): 
        tk.Frame.__init__(self, parent)
         
        # label of frame Layout 2
        label = ttk.Label(self, text ="Main menu", font = LARGEFONT)
         
        # putting the grid in its place by using
        # grid
        label.grid(row = 0, column = 4, padx = 10, pady = 10) 
  
        button1 = ttk.Button(self, text ="Page 1",
        command = lambda : controller.show_frame(NoteTrainer))
     
        # putting the button in its place by
        # using grid
        button1.grid(row = 1, column = 1, padx = 10, pady = 10)
              
  
          
  
  
# second window frame page1 
class NoteTrainer(tk.Frame):
     
    def __init__(self, parent, controller):
         
        tk.Frame.__init__(self, parent)
        label = ttk.Label(self, text ="Note Trainer", font = LARGEFONT)
        label.grid(row = 0, column = 4, padx = 10, pady = 10)
  
        # button to show frame 2 with text
        # layout2
        button1 = ttk.Button(self, text ="Main menu",
                            command = lambda : controller.show_frame(MainMenu))
     
        # putting the button in its place 
        # by using grid
        button1.grid(row = 1, column = 1, padx = 10, pady = 10)
  
  
  
  
# Driver Code
app = tkinterApp()
app.mainloop()