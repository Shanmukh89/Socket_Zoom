#!/usr/bin/env python3
"""
LAN Communication Client - Main Application
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client_gui import LANCommClientGUI

def main():
    app = LANCommClientGUI()
    app.run()

if __name__ == '__main__':
    main()
