
try:
    import Image
except ImportError:
    from PIL import Image

try:
    import ImageTk
except ImportError:
    from PIL import ImageTk


class ImageManager(object):
    def __init__(self, main_path):
        self.bell_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/bell.png").resize((50, 50), Image.LANCZOS))

        self.bell_hovered_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/bell_hovered.png").resize((50, 50), Image.LANCZOS))

        self.bell_muted_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/mutedBell.png").resize((50, 50), Image.LANCZOS))

        self.bell_muted_hovered_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/mutedBell_hovered.png").resize((50, 50), Image.LANCZOS))

        self.arrowUp_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/arrowUp.png").resize((147, 46), Image.LANCZOS))

        self.arrowUp_image_hovered = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/arrowUp_hovered.png").resize((147, 46), Image.LANCZOS))

        self.arrowDown_image = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/arrowDown.png").resize((147, 46), Image.LANCZOS))

        self.arrowDown_image_hovered = ImageTk.PhotoImage(
            Image.open(main_path + "/images/tuner_images/arrowDown_hovered.png").resize((147, 46), Image.LANCZOS))
