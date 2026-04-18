import os
import sys

def resource_path(relative_path):
    """
    Standardized resource locator for PyInstaller _MEIPASS compatibility.
    Mandatory for 'onefile' executable distribution.
    """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback to local directory for development environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)