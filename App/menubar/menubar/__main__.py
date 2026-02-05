"""
Main entry point for OpenCode Token Meter menubar app
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from menubar.app import OpenCodeTokenMeter

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running even when windows are closed
    
    window = OpenCodeTokenMeter()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
