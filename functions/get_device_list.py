import pyaudio # Audio input

class DeviceLister:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def _best_display_name(self, base_name, candidate_names):
        # Prefer the longest near-match when one host API truncates a device name.
        base = str(base_name or "").strip()
        if not base:
            return base
        best = base
        for cand in candidate_names:
            cand = str(cand or "").strip()
            if not cand:
                continue
            if cand.casefold() == best.casefold():
                if len(cand) > len(best):
                    best = cand
                continue
            if cand.startswith(best) or best.startswith(cand):
                if len(cand) > len(best):
                    best = cand
        return best
    
    def show_devices(self, device_type = None):
        numdevices = self.p.get_device_count()
        device_infos = [self.p.get_device_info_by_index(i) for i in range(numdevices)]

        # Keep the list scoped to the currently active/default host API to avoid duplicates.
        try:
            default_input_host_api = self.p.get_default_input_device_info().get('hostApi')
        except Exception:
            default_input_host_api = self.p.get_host_api_info_by_index(0).get('index')
        try:
            default_output_host_api = self.p.get_default_output_device_info().get('hostApi')
        except Exception:
            default_output_host_api = self.p.get_host_api_info_by_index(0).get('index')
        
        input_device_list = []
        output_device_list = []

        all_input_names = [d.get('name') for d in device_infos if d.get('maxInputChannels', 0) > 0]
        all_output_names = [d.get('name') for d in device_infos if d.get('maxOutputChannels', 0) > 0]

        for i, info in enumerate(device_infos):
            if info.get('maxInputChannels', 0) > 0 and info.get('hostApi') == default_input_host_api:
                full_name = self._best_display_name(info.get('name'), all_input_names)
                input_device_list.append("Input Device " + str(i) + " - " + full_name)
            if info.get('maxOutputChannels', 0) > 0 and info.get('hostApi') == default_output_host_api:
                full_name = self._best_display_name(info.get('name'), all_output_names)
                output_device_list.append("Output Device " + str(i) + " - " + full_name)
                 
        
        if device_type == "input":
            return input_device_list
        elif device_type == "output":
            return output_device_list
        elif device_type is None: 
            return input_device_list + output_device_list
        elif device_type not in ["input", "output", None]:
            return "Invalid device type. Please select 'input', 'output', or None"
