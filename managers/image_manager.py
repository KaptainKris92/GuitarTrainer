
try:
    import Image
except ImportError:
    from PIL import Image

try:
    import ImageTk
except ImportError:
    from PIL import ImageTk
from pathlib import Path


class ImageManager(object):
    def __init__(self, main_path):
        base = Path(main_path) / "images" / "tuner_images"
        self.bell_image = ImageTk.PhotoImage(
            Image.open(base / "bell.png").resize((50, 50), Image.LANCZOS))

        self.bell_hovered_image = ImageTk.PhotoImage(
            Image.open(base / "bell_hovered.png").resize((50, 50), Image.LANCZOS))

        self.bell_muted_image = ImageTk.PhotoImage(
            Image.open(base / "mutedBell.png").resize((50, 50), Image.LANCZOS))

        self.bell_muted_hovered_image = ImageTk.PhotoImage(
            Image.open(base / "mutedBell_hovered.png").resize((50, 50), Image.LANCZOS))

        self.arrowUp_image = ImageTk.PhotoImage(
            Image.open(base / "arrowUp.png").resize((147, 46), Image.LANCZOS))

        self.arrowUp_image_hovered = ImageTk.PhotoImage(
            Image.open(base / "arrowUp_hovered.png").resize((147, 46), Image.LANCZOS))

        self.arrowDown_image = ImageTk.PhotoImage(
            Image.open(base / "arrowDown.png").resize((147, 46), Image.LANCZOS))

        self.arrowDown_image_hovered = ImageTk.PhotoImage(
            Image.open(base / "arrowDown_hovered.png").resize((147, 46), Image.LANCZOS))
