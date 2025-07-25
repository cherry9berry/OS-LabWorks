import win32pipe
import win32file
import pywintypes
import win32gui
import win32process
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
import sys
import logging
from abc import ABC, abstractmethod
from config import (PIPE_NAME, PIPE_READ_BUFFER_SIZE, STATUS_UPDATE_INTERVAL, 
                   EVENT_TYPES, PROTOCOL_MESSAGES)

logger = logging.getLogger(__name__)

class BaseClient(ABC):
    """Base client class with common functionality."""
    
    def __init__(self, base_name, client_type):
        self.base_name = base_name
        self.client_type = client_type
        self.client_name = None
        self.client_id = None
        self.pipe = None
        self.root = None
        self.text_var = None
        self.is_typing = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
    
    def connect_to_server(self):
        """Connect to server via named pipe."""
        try:
            self.pipe = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None)
            logger.info(f"Server connection established")
            return True
        except pywintypes.error as e:
            logger.error(f"Pipe connection error: {e}")
            return False
    
    def register_with_server(self):
        """Register client with server."""
        try:
            # Send REGISTER
            register_msg = f"{EVENT_TYPES['REGISTER']}:{self.base_name}:{self.client_type}"
            win32file.WriteFile(self.pipe, register_msg.encode())
            
            # Get unique name and client_id from server
            data = win32file.ReadFile(self.pipe, PIPE_READ_BUFFER_SIZE)[1].decode()
            if not data.startswith("NAME:"):
                logger.error("No name received from server")
                return False
            
            _, self.client_name, self.client_id = data.split(':')
            logger.info(f"Registered as {self.client_name} with ID {self.client_id}")
            
            # Send Started
            started_msg = f"{EVENT_TYPES['STARTED']}:{self.client_name} запущен"
            win32file.WriteFile(self.pipe, started_msg.encode())
            
            return True
        except pywintypes.error as e:
            logger.error(f"Registration error: {e}")
            return False
    
    def is_window_active(self):
        """Check if client window is active."""
        try:
            current_pid = os.getpid()
            foreground_window = win32gui.GetForegroundWindow()
            _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_window)
            return current_pid == foreground_pid
        except Exception as e:
            logger.warning(f"Window activity check error: {e}")
            return False
    
    def send_periodic_status(self):
        """Send periodic Active/Idle status."""
        while True:
            try:
                status = EVENT_TYPES['ACTIVE'] if self.is_window_active() else EVENT_TYPES['IDLE']
                status_msg = f"{status}:{status} {self.client_name}"
                win32file.WriteFile(self.pipe, status_msg.encode())
                time.sleep(STATUS_UPDATE_INTERVAL)
            except pywintypes.error:
                logger.info("Status thread ended - pipe closed")
                break
            except Exception as e:
                logger.error(f"Status send error: {e}")
                break
    
    def send_message(self, event_type, details):
        """Send message to server."""
        try:
            message = f"{event_type}:{details}"
            win32file.WriteFile(self.pipe, message.encode())
            logger.debug(f"Sent: {message}")
        except pywintypes.error as e:
            logger.error(f"Message send error: {e}")
    
    def create_gui(self):
        """Create GUI interface."""
        self.root = tk.Tk()
        self.root.title(f"process {self.client_id}")
        
        self.text_var = tk.StringVar()
        entry = ttk.Entry(self.root, textvariable=self.text_var)
        entry.pack(padx=10, pady=10)
        
        send_button = ttk.Button(self.root, text="Отправить")
        send_button.pack(padx=10, pady=5)
        
        # Bind events
        self.text_var.trace_add('write', self.on_text_change)
        send_button.config(command=self.on_send)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        return entry, send_button
    
    def on_closing(self):
        """Handle window closing."""
        try:
            stop_msg = f"{EVENT_TYPES['STOPPED']}:{self.client_name} завершен"
            win32file.WriteFile(self.pipe, stop_msg.encode())
            win32file.CloseHandle(self.pipe)
        except pywintypes.error:
            pass
        except Exception as e:
            logger.error(f"Closing error: {e}")
        
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Main client run method."""
        if not self.connect_to_server():
            return
        
        if not self.register_with_server():
            self.cleanup()
            return
        
        # Start periodic status thread
        status_thread = threading.Thread(target=self.send_periodic_status, daemon=True)
        status_thread.start()
        
        # Create and run GUI
        self.create_gui()
        self.root.mainloop()
        
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            if self.pipe:
                win32file.CloseHandle(self.pipe)
        except pywintypes.error:
            pass
    
    @abstractmethod
    def on_text_change(self, *args):
        """Handle text input changes. Must be implemented in subclasses."""
        pass
    
    @abstractmethod
    def on_send(self):
        """Handle send button click. Must be implemented in subclasses."""
        pass 