import pyaudio # Audio input

class DeviceLister:
    def __init__(self):
        self.p = pyaudio.PyAudio()
    
    def show_devices(self, device_type = None):
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        input_device_list = []
        output_device_list = []
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                input_device_list.append("Input Device " + str(i) + " - " + self.p.get_device_info_by_host_api_device_index(0, i).get('name'))            
            if (self.p.get_device_info_by_index(i).get('maxOutputChannels')) > 0:
                output_device_list.append("Output Device " + str(i) + " - " + self.p.get_device_info_by_index(i).get('name'))
                
        
        if device_type == "input":
            return input_device_list
        elif device_type == "output":
            return output_device_list
        elif device_type is None: 
            return input_device_list + output_device_list
        elif device_type not in ["input", "output", None]:
            return "Invalid device type. Please select 'input', 'output', or None"