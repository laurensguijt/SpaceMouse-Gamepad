"""
SpaceMouse Controller Module
Handles all SpaceMouse input and processing
"""

import pyspacemouse
from typing import Tuple, Optional, List
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpaceMouseController:
    def __init__(self):
        """
        Initialize the SpaceMouse controller
        """
        self.connected = False
        self.running = False
        self.thread = None
        self.callback = None
        self.on_disconnect = None
        self.device = None
        
        # Movement thresholds
        self.deadzone = 0.1
        self.sensitivity = 1.0
        
        # Current state
        self.current_state = {
            'x': 0.0,
            'y': 0.0,
            'z': 0.0,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'buttons': []
        }

    def list_devices(self) -> List[str]:
        """
        List all available SpaceMouse devices
        
        Returns:
            List[str]: List of device names
        """
        try:
            devices = pyspacemouse.list_devices()
            return [str(device) for device in devices]
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    def list_unique_devices(self) -> List[str]:
        """
        List unique SpaceMouse device names (to avoid duplicate dongle entries)
        Returns:
            List[str]: List of unique device names
        """
        try:
            devices = self.list_devices()
            # Only keep unique names
            unique = []
            for d in devices:
                if d not in unique:
                    unique.append(d)
            return unique
        except Exception as e:
            logger.error(f"Error listing unique devices: {e}")
            return []

    def connect(self) -> bool:
        """
        Connect to the first available SpaceMouse device
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.connected:
                self.disconnect()
            devices = self.list_unique_devices()
            if not devices:
                logger.error("No SpaceMouse devices found")
                return False
            logger.info(f"Found unique devices: {devices}")
            # pyspacemouse.open() always connects to the first available device
            success = pyspacemouse.open()
            if success:
                self.connected = True
                self.device = devices[0]
                logger.info(f"Connected to device: {self.device}")
                self.start_listening()
                return True
            else:
                logger.error("Failed to connect to SpaceMouse")
                return False
        except Exception as e:
            logger.error(f"Error connecting to SpaceMouse: {e}")
            return False

    def disconnect(self):
        """
        Disconnect from the SpaceMouse device
        """
        self.running = False
        if self.thread and self.thread != threading.current_thread():
            self.thread.join()
        self.connected = False
        self.device = None
        try:
            pyspacemouse.close()
        except Exception as e:
            logger.error(f"Error disconnecting from SpaceMouse: {e}")

    def start_listening(self):
        """
        Start listening for SpaceMouse input in a separate thread
        """
        self.running = True
        self.thread = threading.Thread(target=self._input_loop)
        self.thread.daemon = True
        self.thread.start()

    def _input_loop(self):
        """
        Main input loop for SpaceMouse data
        """
        retry_count = 0
        max_retries = 3
        last_error_time = 0
        error_cooldown = 1.0  # 1 second between error logs
        
        while self.running:
            try:
                state = pyspacemouse.read()
                if state:
                    retry_count = 0  # Reset retry count on successful read
                    self.current_state = {
                        'x': state.x,
                        'y': state.y,
                        'z': state.z,
                        'roll': state.roll,
                        'pitch': state.pitch,
                        'yaw': state.yaw,
                        'buttons': state.buttons
                    }
                    if self.callback:
                        self.callback(self.current_state)
                time.sleep(0.005)  # 200Hz polling rate
                
            except Exception as e:
                current_time = time.time()
                retry_count += 1
                
                # Only log error if enough time has passed since last error
                if current_time - last_error_time >= error_cooldown:
                    logger.error(f"Error reading SpaceMouse input: {e}")
                    last_error_time = current_time
                
                # Direct disconnect detection for USB unplug
                if "Failed to read from HID device" in str(e):
                    logger.error("SpaceMouse disconnected (USB unplugged)")
                    self.connected = False
                    self.device = None
                    try:
                        pyspacemouse.close()
                    except:
                        pass
                    if self.on_disconnect:
                        time.sleep(0.1)  # Small delay for GUI
                        self.on_disconnect()
                    self.running = False
                    return  # Stop the thread
                
                if retry_count >= max_retries:
                    logger.error("Max retries reached, attempting to reconnect...")
                    self.connected = False
                    self.device = None
                    try:
                        pyspacemouse.close()
                    except:
                        pass
                    if self.connect():
                        retry_count = 0
                    else:
                        if self.on_disconnect:
                            time.sleep(0.1)  # Small delay for GUI
                            self.on_disconnect()
                        time.sleep(1)  # Wait before retrying connection
                else:
                    time.sleep(0.1)  # Short wait before retry

    def set_callback(self, callback):
        """
        Set the callback function for SpaceMouse updates
        
        Args:
            callback: Function to call with SpaceMouse state updates
        """
        self.callback = callback

    def set_on_disconnect(self, callback):
        """
        Set the callback function for SpaceMouse disconnect events
        Args:
            callback: Function to call when SpaceMouse is disconnected
        """
        self.on_disconnect = callback

    def get_movement(self) -> Tuple[float, float, float]:
        """
        Get the current movement values
        
        Returns:
            Tuple[float, float, float]: (x, y, z) movement values
        """
        if not self.connected:
            return (0.0, 0.0, 0.0)
            
        x = self.current_state['x'] * self.sensitivity
        y = self.current_state['y'] * self.sensitivity
        z = self.current_state['z'] * self.sensitivity
        
        # Apply deadzone
        x = 0.0 if abs(x) < self.deadzone else x
        y = 0.0 if abs(y) < self.deadzone else y
        z = 0.0 if abs(z) < self.deadzone else z
        
        return (x, y, z)

    def get_buttons(self) -> list:
        """
        Get the current button states
        
        Returns:
            list: List of pressed button indices
        """
        return self.current_state['buttons']

    def set_sensitivity(self, value: float):
        """
        Set the movement sensitivity
        
        Args:
            value (float): Sensitivity value (0.0 to 2.0)
        """
        self.sensitivity = max(0.0, min(2.0, value))

    def set_deadzone(self, value: float):
        """
        Set the movement deadzone
        
        Args:
            value (float): Deadzone value (0.0 to 0.5)
        """
        self.deadzone = max(0.0, min(0.5, value)) 