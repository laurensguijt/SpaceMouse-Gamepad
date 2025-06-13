#!/usr/bin/env python3
"""
SpaceMouse-Gamepad
Designed by: Laurens Guijt
GitHub: https://github.com/laurensguijt/SpaceMouse-Gamepad
"""

import sys
from PyQt6.QtWidgets import QApplication
from core.spacemouse_controller import SpaceMouseController
from core.keyboard_controller import KeyboardController
from gui.main_window import MainWindow

def main():
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    # Initialize controllers
    spacemouse = SpaceMouseController()
    keyboard = KeyboardController()
    
    # Try to connect automatically
    spacemouse.connect()
    
    # Create and show main window
    window = MainWindow(spacemouse, keyboard)
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 