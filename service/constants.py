SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".avif",
    ".heic",
    ".heif",
    ".gif",
    ".ico",
    ".ppm",
    ".pgm",
    ".pbm",
}


BUTTON_STYLE = """
    QPushButton {
        background-color: #0078d4;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #1088e6;
    }
    QPushButton:pressed {
        background-color: #005a9e;
    }
    QPushButton:disabled {
        background-color: #555;
        color: #aaa;
    }
"""


WINDOW_STYLE = """
    QMainWindow {
        background-color: #f0f0f0;
    }
    QGroupBox {
        font-weight: bold;
        border: 2px solid #cccccc;
        border-radius: 5px;
        margin-top: 1ex;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }
    QLabel[class="tooltip"] {
        color: #666;
        font-style: italic;
        font-size: 11px;
    }
"""


STATUS_LABEL_STYLE = "color: #666; font-size: 12px; font-style: italic;"
