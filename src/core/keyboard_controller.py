"""
Keyboard Controller Module
Handles keyboard input simulation for game control
"""

import math
import pydirectinput
from typing import Set
import threading
import time

class KeyboardController:
    def __init__(self):
        self.active_keys: Set[str] = set()
        self.held_movement_keys: Set[str] = set()
        self.held_action_keys: Set[str] = set()  # jump, crouch, sprint
        self.movement_keys = {
            'forward': 'w',
            'backward': 's',
            'left': 'a',
            'right': 'd',
        }
        self.movement_threshold = 0.5
        self.jump_key = 'space'
        self.crouch_key = 'c'
        self.sprint_key = 'shift'
        self.prone_key = 'x'
        self.jump_threshold = 0.5
        self.crouch_threshold = 0.5
        self.sprint_threshold = 0.9
        self.sprint_enabled = True
        self.prone_duration = 0.8  # in seconds
        self.prone_active = False
        self.prone_timer = None
        self.button_keys = ['1', '2']
        self.button_states = [False, False]

    def update_movement(self, x: float, y: float, z: float):
        magnitude = (x**2 + y**2)**0.5
        # Movement keys
        if abs(x) < self.movement_threshold and abs(y) < self.movement_threshold:
            for key in ['forward', 'backward', 'left', 'right']:
                self._release_movement(self.movement_keys[key])
        else:
            angle = math.atan2(y, x)
            directions = []
            if -math.pi/8 <= angle < math.pi/8:
                directions.append('right')
            if math.pi/8 <= angle < 3*math.pi/8:
                directions.extend(['right', 'forward'])
            if 3*math.pi/8 <= angle < 5*math.pi/8:
                directions.append('forward')
            if 5*math.pi/8 <= angle < 7*math.pi/8:
                directions.extend(['left', 'forward'])
            if angle >= 7*math.pi/8 or angle < -7*math.pi/8:
                directions.append('left')
            if -7*math.pi/8 <= angle < -5*math.pi/8:
                directions.extend(['left', 'backward'])
            if -5*math.pi/8 <= angle < -3*math.pi/8:
                directions.append('backward')
            if -3*math.pi/8 <= angle < -math.pi/8:
                directions.extend(['right', 'backward'])
            for key in ['forward', 'backward', 'left', 'right']:
                if key not in directions:
                    self._release_movement(self.movement_keys[key])
            for key in directions:
                self._hold_movement(self.movement_keys[key])
        # Sprint
        if self.sprint_enabled and magnitude > self.sprint_threshold:
            self._hold_action(self.sprint_key)
        else:
            self._release_action(self.sprint_key)
        # Jump
        if z > self.jump_threshold:
            self._hold_action(self.jump_key)
        else:
            self._release_action(self.jump_key)
        # Crouch/Prone logic
        self._handle_crouch_prone(z)

    def _handle_crouch_prone(self, z):
        prone_time = self.prone_duration
        crouch_key = self.crouch_key
        prone_key = self.prone_key
        if not hasattr(self, '_crouch_prone_thread'):
            self._crouch_prone_thread = None
        if z < -self.crouch_threshold:
            if self._crouch_prone_thread is None or not self._crouch_prone_thread.is_alive():
                def crouch_or_prone_worker():
                    start = time.time()
                    while True:
                        elapsed = time.time() - start
                        # Check if threshold is still held
                        if self._last_z is not None and self._last_z >= -self.crouch_threshold:
                            # Released before prone_time: do crouch for held time
                            pydirectinput.keyDown(crouch_key)
                            self.active_keys.add(crouch_key)
                            self.held_action_keys.add(crouch_key)
                            time.sleep(elapsed)
                            pydirectinput.keyUp(crouch_key)
                            self.active_keys.discard(crouch_key)
                            self.held_action_keys.discard(crouch_key)
                            return
                        if elapsed >= prone_time:
                            # Held long enough: do prone only
                            pydirectinput.keyDown(prone_key)
                            self.active_keys.add(prone_key)
                            self.held_action_keys.add(prone_key)
                            time.sleep(prone_time)
                            pydirectinput.keyUp(prone_key)
                            self.active_keys.discard(prone_key)
                            self.held_action_keys.discard(prone_key)
                            return
                        time.sleep(0.01)
                self._last_z = z
                def z_updater():
                    while True:
                        self._last_z = self._current_z
                        time.sleep(0.01)
                self._current_z = z
                self._z_updater_thread = threading.Thread(target=z_updater)
                self._z_updater_thread.daemon = True
                self._z_updater_thread.start()
                self._crouch_prone_thread = threading.Thread(target=crouch_or_prone_worker)
                self._crouch_prone_thread.daemon = True
                self._crouch_prone_thread.start()
            else:
                self._current_z = z
        else:
            self._current_z = z
            self._release_action(crouch_key)

    def _hold_movement(self, key: str):
        if key not in self.held_movement_keys:
            pydirectinput.keyDown(key)
            self.held_movement_keys.add(key)
            self.active_keys.add(key)
    def _release_movement(self, key: str):
        if key in self.held_movement_keys:
            pydirectinput.keyUp(key)
            self.held_movement_keys.remove(key)
            self.active_keys.discard(key)
    def _hold_action(self, key: str):
        if key not in self.held_action_keys:
            pydirectinput.keyDown(key)
            self.held_action_keys.add(key)
            self.active_keys.add(key)
    def _release_action(self, key: str):
        if key in self.held_action_keys:
            pydirectinput.keyUp(key)
            self.held_action_keys.remove(key)
            self.active_keys.discard(key)

    def release_all_keys(self):
        for key in list(self.active_keys):
            pydirectinput.keyUp(key)
        self.active_keys.clear()
        self.held_movement_keys.clear()
        self.held_action_keys.clear()

    def set_movement_key(self, action: str, key: str):
        if action in self.movement_keys:
            self.movement_keys[action] = key.lower()
    def set_jump_key(self, key: str):
        self.jump_key = key.lower()
    def set_crouch_key(self, key: str):
        self.crouch_key = key.lower()
    def set_sprint_key(self, key: str):
        self.sprint_key = key.lower()
    def set_movement_threshold(self, value: float):
        self.movement_threshold = max(0.0, min(1.0, value))
    def set_jump_threshold(self, value: float):
        self.jump_threshold = max(0.0, min(1.0, value))
    def set_crouch_threshold(self, value: float):
        self.crouch_threshold = max(0.0, min(1.0, value))
    def set_sprint_threshold(self, value: float):
        self.sprint_threshold = max(0.0, min(1.0, value))
    def set_sprint_enabled(self, enabled: bool):
        self.sprint_enabled = enabled
    def update_buttons(self, buttons: list):
        n = max(len(self.button_keys), len(self.button_states), len(buttons))
        while len(self.button_keys) < n:
            self.button_keys.append('1')
        while len(self.button_states) < n:
            self.button_states.append(False)
        for i in range(n):
            pressed = (buttons[i] == 1) if i < len(buttons) else False
            key = self.button_keys[i]
            if pressed != self.button_states[i]:
                if pressed and not self.button_states[i]:
                    pydirectinput.press(key)
                    self.active_keys.add(key)
                elif not pressed and self.button_states[i]:
                    pydirectinput.keyUp(key)
                    if key in self.active_keys:
                        self.active_keys.remove(key)
            self.button_states[i] = pressed
    def set_button_key(self, index: int, key: str):
        while len(self.button_keys) <= index:
            self.button_keys.append(str(index+1))
        self.button_keys[index] = key.lower()
    def set_prone_key(self, key: str):
        self.prone_key = key.lower()
    def set_prone_duration(self, seconds: float):
        self.prone_duration = max(0.05, float(seconds))
    @property
    def active_actions(self):
        return {
            'movement': list(self.held_movement_keys),
            'actions': list(self.held_action_keys),
            'buttons': [self.button_keys[i] for i, pressed in enumerate(self.button_states) if pressed],
        } 