"""
Main GUI window for the SpaceMouse-Gamepad
Designed by: Laurens Guijt
GitHub: https://github.com/laurensguijt/SpaceMouse-Gamepad
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QGroupBox,
    QComboBox, QStatusBar, QMessageBox, QCheckBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap
from typing import Dict, Any
import logging
import os
import json
import psutil
import sys

logger = logging.getLogger(__name__)

class DisconnectHandler(QObject):
    disconnected = pyqtSignal()

class MainWindow(QMainWindow):
    ALL_KEYS = [
        'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',
        '0','1','2','3','4','5','6','7','8','9',
        'space','shift','ctrl','alt','tab','capslock','esc','enter','backspace','delete','insert','home','end','pageup','pagedown','up','down','left','right',
        'f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12'
    ]
    PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../profiles')
    def __init__(self, spacemouse, keyboard):
        """
        Initialize the main window
        
        Args:
            spacemouse: SpaceMouse controller instance
            keyboard: Keyboard controller instance
        """
        super().__init__()
        
        self.spacemouse = spacemouse
        self.keyboard = keyboard
        self._spacemouse_disconnected = False  # Track disconnect popup state
        
        # Maak een disconnect handler
        self.disconnect_handler = DisconnectHandler()
        self.disconnect_handler.disconnected.connect(self._show_disconnect_popup)
        
        self.setWindowTitle("SpaceMouse-Gamepad")
        self.setMinimumSize(400, 500)
        # Zet het venstericoon
        icon_path = self.resource_path('assets/icons/spacemouse_controller_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Voeg het logo toe bovenaan
        logo_label = QLabel()
        logo_pixmap = QPixmap(self.resource_path('assets/icons/Spacemouse_keyboard.png'))
        logo_label.setPixmap(logo_pixmap.scaledToWidth(175, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(logo_label)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create control sections
        self._create_connection_section(layout)
        self._create_sensitivity_section(layout)
        self._create_movement_section(layout)
        self._create_status_section(layout)
        self.current_profile = 'default'
        self.profile_process_map = {}
        self._create_profile_section(layout)
        
        # Set up update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(100)  # Update every 100ms
        
        # Initial device scan
        self._scan_devices()
        # Probeer direct te verbinden
        self._connect_spacemouse()
        
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._auto_profile_switch)
        self.process_timer.start(2000)

        # Set the disconnect callback
        self.spacemouse.set_on_disconnect(self.disconnect_handler.disconnected.emit)

        # Add designed label
        designed_label = QLabel('Designed by: Laurens Guijt | <a href="https://github.com/laurensguijt/SpaceMouse-Gamepad">GitHub</a>')
        designed_label.setOpenExternalLinks(True)
        designed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(designed_label)

    def _create_connection_section(self, parent_layout):
        """
        Create the connection control section
        
        Args:
            parent_layout: Parent layout to add widgets to
        """
        group = QGroupBox("Connection")
        layout = QVBoxLayout()
        
        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_button)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Devices")
        refresh_button.clicked.connect(self._scan_devices)
        layout.addWidget(refresh_button)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _scan_devices(self):
        """
        Scan for available SpaceMouse devices (unique names only)
        """
        self.device_combo.clear()
        devices = self.spacemouse.list_unique_devices()
        if devices:
            self.device_combo.addItems(devices)
            self.status_bar.showMessage(f"Found {len(devices)} unique device(s)")
            if len(devices) == 1:
                self.device_combo.setEnabled(False)
            else:
                self.device_combo.setEnabled(True)
        else:
            self.status_bar.showMessage("No SpaceMouse devices found")
            QMessageBox.warning(
                self,
                "No Devices Found",
                "No SpaceMouse devices were found. Please ensure your device is connected and try again."
            )

    def _device_changed(self, index):
        """
        Handle device selection change (no-op, always first device is used)
        """
        pass  # Device selection is not supported by pyspacemouse

    def _connect_spacemouse(self):
        """
        Connect to the SpaceMouse device (always first unique device)
        """
        if self.spacemouse.connect():
            self.status_label.setText("Status: Connected")
            self.connect_button.setText("Disconnect")
            self.spacemouse.set_callback(self._spacemouse_callback)
            self.status_bar.showMessage(f"Connected to {self.spacemouse.device}")
            self._spacemouse_disconnected = False  # Reset disconnect popup state
        else:
            self.status_label.setText("Status: Connection Failed")
            self.status_bar.showMessage("Failed to connect to SpaceMouse")
            QMessageBox.critical(
                self,
                "Connection Failed",
                "Failed to connect to the SpaceMouse device. Please check the connection and try again."
            )

    def _toggle_connection(self):
        """
        Toggle SpaceMouse connection
        """
        if self.spacemouse.connected:
            self.spacemouse.disconnect()
            self.status_label.setText("Status: Disconnected")
            self.connect_button.setText("Connect")
            self.status_bar.showMessage("Disconnected from SpaceMouse")
        else:
            self._connect_spacemouse()

    def _create_sensitivity_section(self, parent_layout):
        """
        Create the sensitivity control section
        
        Args:
            parent_layout: Parent layout to add widgets to
        """
        group = QGroupBox("Sensitivity Settings")
        layout = QVBoxLayout()
        
        # Sensitivity slider
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Sensitivity:"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(0, 200)
        self.sensitivity_slider.setValue(100)
        self.sensitivity_slider.valueChanged.connect(self._update_sensitivity)
        self.sensitivity_value = QLabel("1.00")
        sensitivity_layout.addWidget(self.sensitivity_slider)
        sensitivity_layout.addWidget(self.sensitivity_value)
        layout.addLayout(sensitivity_layout)
        
        # Deadzone slider
        deadzone_layout = QHBoxLayout()
        deadzone_layout.addWidget(QLabel("Deadzone:"))
        self.deadzone_slider = QSlider(Qt.Orientation.Horizontal)
        self.deadzone_slider.setRange(0, 50)
        self.deadzone_slider.setValue(10)
        self.deadzone_slider.valueChanged.connect(self._update_deadzone)
        self.deadzone_value = QLabel("0.10")
        deadzone_layout.addWidget(self.deadzone_slider)
        deadzone_layout.addWidget(self.deadzone_value)
        layout.addLayout(deadzone_layout)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_movement_section(self, parent_layout):
        """
        Create the movement control section
        
        Args:
            parent_layout: Parent layout to add widgets to
        """
        group = QGroupBox("Movement Controls")
        layout = QVBoxLayout()
        
        # Movement threshold slider
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Movement Threshold:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.valueChanged.connect(self._update_threshold)
        self.threshold_value = QLabel("0.50")
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value)
        layout.addLayout(threshold_layout)

        # Sprint key dropdown
        sprint_layout = QHBoxLayout()
        sprint_layout.addWidget(QLabel("Sprint key:"))
        self.sprint_combo = QComboBox()
        self.sprint_combo.addItems(self.ALL_KEYS)
        self.sprint_combo.setCurrentText('shift')
        self.sprint_combo.currentTextChanged.connect(self._update_sprint_key)
        sprint_layout.addWidget(self.sprint_combo)
        # Sprint threshold slider
        self.sprint_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.sprint_threshold_slider.setRange(0, 100)
        self.sprint_threshold_slider.setValue(90)
        self.sprint_threshold_slider.valueChanged.connect(self._update_sprint_threshold)
        sprint_layout.addWidget(QLabel("Sprint threshold:"))
        self.sprint_threshold_value = QLabel("0.90")
        sprint_layout.addWidget(self.sprint_threshold_slider)
        sprint_layout.addWidget(self.sprint_threshold_value)
        layout.addLayout(sprint_layout)

        # Sprint enable checkbox
        self.sprint_checkbox = QCheckBox("Enable sprint")
        self.sprint_checkbox.setChecked(True)
        self.sprint_checkbox.stateChanged.connect(self._update_sprint_enabled)
        layout.addWidget(self.sprint_checkbox)

        # Jump key dropdown
        jump_layout = QHBoxLayout()
        jump_layout.addWidget(QLabel("Jump (pull up):"))
        self.jump_combo = QComboBox()
        self.jump_combo.addItems(self.ALL_KEYS)
        self.jump_combo.setCurrentText('space')
        self.jump_combo.currentTextChanged.connect(self._update_jump_key)
        jump_layout.addWidget(self.jump_combo)
        # Jump threshold slider
        self.jump_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.jump_threshold_slider.setRange(0, 100)
        self.jump_threshold_slider.setValue(50)
        self.jump_threshold_slider.valueChanged.connect(self._update_jump_threshold)
        jump_layout.addWidget(QLabel("Threshold:"))
        self.jump_threshold_value = QLabel("0.50")
        jump_layout.addWidget(self.jump_threshold_slider)
        jump_layout.addWidget(self.jump_threshold_value)
        layout.addLayout(jump_layout)

        # Crouch key dropdown
        crouch_layout = QHBoxLayout()
        crouch_layout.addWidget(QLabel("Crouch (push down):"))
        self.crouch_combo = QComboBox()
        self.crouch_combo.addItems(self.ALL_KEYS)
        self.crouch_combo.setCurrentText('c')
        self.crouch_combo.currentTextChanged.connect(self._update_crouch_key)
        crouch_layout.addWidget(self.crouch_combo)
        self.crouch_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.crouch_threshold_slider.setRange(0, 100)
        self.crouch_threshold_slider.setValue(50)
        self.crouch_threshold_slider.valueChanged.connect(self._update_crouch_threshold)
        crouch_layout.addWidget(QLabel("Threshold:"))
        self.crouch_threshold_value = QLabel("0.50")
        crouch_layout.addWidget(self.crouch_threshold_slider)
        crouch_layout.addWidget(self.crouch_threshold_value)
        layout.addLayout(crouch_layout)

        # Prone key dropdown
        prone_layout = QHBoxLayout()
        prone_layout.addWidget(QLabel("Prone key:"))
        self.prone_combo = QComboBox()
        self.prone_combo.addItems(self.ALL_KEYS)
        self.prone_combo.setCurrentText('x')
        self.prone_combo.currentTextChanged.connect(self._update_prone_key)
        prone_layout.addWidget(self.prone_combo)
        # Prone duration slider
        self.prone_duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.prone_duration_slider.setRange(1, 20)
        self.prone_duration_slider.setValue(8)
        self.prone_duration_slider.valueChanged.connect(self._update_prone_duration)
        prone_layout.addWidget(QLabel("Prone hold (s):"))
        self.prone_duration_value = QLabel("0.80")
        prone_layout.addWidget(self.prone_duration_slider)
        prone_layout.addWidget(self.prone_duration_value)
        layout.addLayout(prone_layout)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_status_section(self, parent_layout):
        """
        Create the status display section
        
        Args:
            parent_layout: Parent layout to add widgets to
        """
        group = QGroupBox("Current Status")
        layout = QVBoxLayout()
        
        # Movement values
        self.movement_label = QLabel("Movement: X: 0.00 Y: 0.00 Z: 0.00")
        layout.addWidget(self.movement_label)
        
        # Button states
        self.button_label = QLabel("Buttons: None")
        layout.addWidget(self.button_label)
        
        # Button keybind dropdowns
        button1_layout = QHBoxLayout()
        button1_layout.addWidget(QLabel("Button 1 keybind:"))
        self.button1_combo = QComboBox()
        self.button1_combo.addItems(self.ALL_KEYS)
        self.button1_combo.setCurrentText('1')
        self.button1_combo.currentTextChanged.connect(self._update_button1_key)
        button1_layout.addWidget(self.button1_combo)
        layout.addLayout(button1_layout)
        button2_layout = QHBoxLayout()
        button2_layout.addWidget(QLabel("Button 2 keybind:"))
        self.button2_combo = QComboBox()
        self.button2_combo.addItems(self.ALL_KEYS)
        self.button2_combo.setCurrentText('2')
        self.button2_combo.currentTextChanged.connect(self._update_button2_key)
        button2_layout.addWidget(self.button2_combo)
        layout.addLayout(button2_layout)
        
        # Visualisatie van actieve acties/keys
        self.visual_label = QLabel()
        self.visual_label.setText("Active: -")
        layout.addWidget(self.visual_label)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_profile_section(self, parent_layout):
        group = QGroupBox("Profile Management")
        layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self._refresh_profiles()
        self.profile_combo.currentTextChanged.connect(self._on_profile_selected)
        layout.addWidget(QLabel("Profile:"))
        layout.addWidget(self.profile_combo)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._save_current_profile)
        layout.addWidget(btn_save)
        btn_rename = QPushButton("Rename")
        btn_rename.clicked.connect(self._rename_profile)
        layout.addWidget(btn_rename)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self._delete_profile)
        layout.addWidget(btn_delete)
        btn_export = QPushButton("Export")
        btn_export.clicked.connect(self._export_profile)
        layout.addWidget(btn_export)
        btn_import = QPushButton("Import")
        btn_import.clicked.connect(self._import_profile)
        layout.addWidget(btn_import)
        btn_link = QPushButton("Link to process")
        btn_link.clicked.connect(self._link_profile_to_process)
        layout.addWidget(btn_link)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _profile_path(self, name):
        return os.path.join(self.PROFILE_DIR, f"{name}.json")

    def _refresh_profiles(self):
        if not os.path.exists(self.PROFILE_DIR):
            os.makedirs(self.PROFILE_DIR)
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        profiles = [f[:-5] for f in os.listdir(self.PROFILE_DIR) if f.endswith('.json')]
        if 'default' not in profiles:
            profiles.insert(0, 'default')
        self.profile_combo.addItems(profiles)
        self.profile_combo.setCurrentText(self.current_profile)
        self.profile_combo.blockSignals(False)

    def _save_current_profile(self):
        data = self._gather_profile_data()
        with open(self._profile_path(self.current_profile), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        self._refresh_profiles()

    def _gather_profile_data(self):
        return {
            'movement_keys': self.keyboard.movement_keys,
            'jump_key': self.keyboard.jump_key,
            'crouch_key': self.keyboard.crouch_key,
            'sprint_key': self.keyboard.sprint_key,
            'prone_key': self.keyboard.prone_key,
            'movement_threshold': self.keyboard.movement_threshold,
            'jump_threshold': self.keyboard.jump_threshold,
            'crouch_threshold': self.keyboard.crouch_threshold,
            'sprint_threshold': self.keyboard.sprint_threshold,
            'sprint_enabled': self.keyboard.sprint_enabled,
            'prone_duration': self.keyboard.prone_duration,
            'button_keys': self.keyboard.button_keys,
            'profile_process_map': self.profile_process_map,
        }

    def _load_profile(self, name):
        path = self._profile_path(name)
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.keyboard.movement_keys = data.get('movement_keys', self.keyboard.movement_keys)
        self.keyboard.jump_key = data.get('jump_key', self.keyboard.jump_key)
        self.keyboard.crouch_key = data.get('crouch_key', self.keyboard.crouch_key)
        self.keyboard.sprint_key = data.get('sprint_key', self.keyboard.sprint_key)
        self.keyboard.prone_key = data.get('prone_key', self.keyboard.prone_key)
        self.keyboard.movement_threshold = data.get('movement_threshold', self.keyboard.movement_threshold)
        self.keyboard.jump_threshold = data.get('jump_threshold', self.keyboard.jump_threshold)
        self.keyboard.crouch_threshold = data.get('crouch_threshold', self.keyboard.crouch_threshold)
        self.keyboard.sprint_threshold = data.get('sprint_threshold', self.keyboard.sprint_threshold)
        self.keyboard.sprint_enabled = data.get('sprint_enabled', self.keyboard.sprint_enabled)
        self.keyboard.prone_duration = data.get('prone_duration', self.keyboard.prone_duration)
        self.keyboard.button_keys = data.get('button_keys', self.keyboard.button_keys)
        self.profile_process_map = data.get('profile_process_map', self.profile_process_map)
        self.current_profile = name
        self._refresh_profiles()
        self._update_gui_from_profile()

    def _update_gui_from_profile(self):
        # Zet alle GUI-controls naar de waarden van het geladen profiel
        self.sprint_combo.setCurrentText(self.keyboard.sprint_key)
        self.sprint_checkbox.setChecked(self.keyboard.sprint_enabled)
        self.sprint_threshold_slider.setValue(int(self.keyboard.sprint_threshold * 100))
        self.jump_combo.setCurrentText(self.keyboard.jump_key)
        self.jump_threshold_slider.setValue(int(self.keyboard.jump_threshold * 100))
        self.crouch_combo.setCurrentText(self.keyboard.crouch_key)
        self.crouch_threshold_slider.setValue(int(self.keyboard.crouch_threshold * 100))
        self.prone_combo.setCurrentText(self.keyboard.prone_key)
        self.prone_duration_slider.setValue(int(self.keyboard.prone_duration * 10))
        self.button1_combo.setCurrentText(self.keyboard.button_keys[0])
        self.button2_combo.setCurrentText(self.keyboard.button_keys[1])
        self.threshold_slider.setValue(int(self.keyboard.movement_threshold * 100))
        # ... eventueel meer GUI-controls ...

    def _on_profile_selected(self, name):
        self._load_profile(name)

    def _rename_profile(self):
        old = self.current_profile
        new, ok = QInputDialog.getText(self, "Rename Profile", "New name:", text=old)
        if ok and new and new != old:
            os.rename(self._profile_path(old), self._profile_path(new))
            self.current_profile = new
            self._refresh_profiles()

    def _delete_profile(self):
        if self.current_profile == 'default':
            QMessageBox.warning(self, "Delete Profile", "Cannot delete the default profile!")
            return
        os.remove(self._profile_path(self.current_profile))
        self.current_profile = 'default'
        self._refresh_profiles()
        self._load_profile('default')

    def _export_profile(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Profile", "profile.json", "JSON Files (*.json)")
        if path:
            with open(self._profile_path(self.current_profile), 'r', encoding='utf-8') as src, open(path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())

    def _import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Profile", "", "JSON Files (*.json)")
        if path:
            name, ok = QInputDialog.getText(self, "Profile Name", "Name for imported profile:")
            if ok and name:
                with open(path, 'r', encoding='utf-8') as src, open(self._profile_path(name), 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                self._refresh_profiles()

    def _link_profile_to_process(self):
        name, ok = QInputDialog.getText(self, "Link Profile to Process", "Process name (bijv. game.exe):")
        if ok and name:
            self.profile_process_map[self.current_profile] = name
            self._save_current_profile()

    def _auto_profile_switch(self):
        # Detecteer actief proces en laad profiel indien gekoppeld
        try:
            active = self._get_active_process_name()
            for prof, proc in self.profile_process_map.items():
                if proc and proc.lower() == active.lower() and prof != self.current_profile:
                    self._load_profile(prof)
                    break
        except Exception:
            pass

    def _get_active_process_name(self):
        # Windows: krijg de naam van het actieve venster/proces
        import win32gui, win32process
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['pid'] == pid:
                return p.info['name']
        return ''

    def _spacemouse_callback(self, state: Dict[str, Any]):
        """
        Callback for SpaceMouse state updates
        
        Args:
            state: Current SpaceMouse state
        """
        # Gebruik rotatie voor WASD
        roll = state['roll']
        pitch = state['pitch']
        z = state['z']
        self.keyboard.update_movement(roll, pitch, z)
        # Update button keybinds
        self.keyboard.update_buttons(state.get('buttons', []))
        # Update status display
        self.movement_label.setText(
            f"Movement: Roll: {roll:.2f} Pitch: {pitch:.2f} Z: {z:.2f}"
        )
        # Update button display
        buttons = state['buttons']
        if buttons:
            self.button_label.setText(f"Buttons: {', '.join(map(str, buttons))}")
        else:
            self.button_label.setText("Buttons: None")

    def _update_sensitivity(self, value: int):
        """
        Update sensitivity value
        
        Args:
            value: New sensitivity value (0-200)
        """
        sensitivity = value / 100.0
        self.spacemouse.set_sensitivity(sensitivity)
        self.sensitivity_value.setText(f"{sensitivity:.2f}")

    def _update_deadzone(self, value: int):
        """
        Update deadzone value
        
        Args:
            value: New deadzone value (0-50)
        """
        deadzone = value / 100.0
        self.spacemouse.set_deadzone(deadzone)
        self.deadzone_value.setText(f"{deadzone:.2f}")

    def _update_threshold(self, value: int):
        """
        Update movement threshold value
        
        Args:
            value: New threshold value (0-100)
        """
        threshold = value / 100.0
        self.keyboard.set_movement_threshold(threshold)
        self.threshold_value.setText(f"{threshold:.2f}")

    def _update_jump_key(self, key: str):
        self.keyboard.set_jump_key(key)

    def _update_crouch_key(self, key: str):
        self.keyboard.set_crouch_key(key)

    def _update_jump_threshold(self, value: int):
        threshold = value / 100.0
        self.keyboard.set_jump_threshold(threshold)
        self.jump_threshold_value.setText(f"{threshold:.2f}")

    def _update_crouch_threshold(self, value: int):
        threshold = value / 100.0
        self.keyboard.set_crouch_threshold(threshold)
        self.crouch_threshold_value.setText(f"{threshold:.2f}")

    def _update_button1_key(self, key: str):
        self.keyboard.set_button_key(0, key)

    def _update_button2_key(self, key: str):
        self.keyboard.set_button_key(1, key)

    def _update_sprint_key(self, key: str):
        self.keyboard.set_sprint_key(key)

    def _update_sprint_threshold(self, value: int):
        threshold = value / 100.0
        self.keyboard.set_sprint_threshold(threshold)
        self.sprint_threshold_value.setText(f"{threshold:.2f}")

    def _update_sprint_enabled(self, state):
        enabled = state == 2
        self.keyboard.set_sprint_enabled(enabled)

    def _update_prone_key(self, key: str):
        self.keyboard.set_prone_key(key)

    def _update_prone_duration(self, value: int):
        seconds = value / 10.0
        self.keyboard.set_prone_duration(seconds)
        self.prone_duration_value.setText(f"{seconds:.2f}")

    def _update_status(self):
        """
        Update status display
        """
        if self.spacemouse.connected:
            x, y, z = self.spacemouse.get_movement()
            self.movement_label.setText(
                f"Movement: X: {x:.2f} Y: {y:.2f} Z: {z:.2f}"
            )
            
            buttons = self.spacemouse.get_buttons()
            if buttons:
                self.button_label.setText(f"Buttons: {', '.join(map(str, buttons))}")
            else:
                self.button_label.setText("Buttons: None")
            # Visualisatie van actieve acties/keys
            actions = self.keyboard.active_actions
            vis = []
            if actions['movement']:
                vis.append("Movement: " + ', '.join(actions['movement']))
            if actions['actions']:
                vis.append("Actions: " + ', '.join(actions['actions']))
            if self.keyboard.prone_active:
                vis.append(f"Prone: {self.keyboard.prone_key}")
            if actions['buttons']:
                vis.append("Buttons: " + ', '.join(actions['buttons']))
            if not vis:
                vis = ["-"]
            self.visual_label.setText("Active: " + ' | '.join(vis))

    def closeEvent(self, event):
        """
        Handle window close event
        
        Args:
            event: Close event
        """
        self.spacemouse.disconnect()
        event.accept()

    def _show_disconnect_popup(self):
        """
        Toon de disconnect popup in de main thread
        """
        if not self._spacemouse_disconnected:
            self._spacemouse_disconnected = True
            self.status_label.setText("Status: Disconnected")
            self.connect_button.setText("Connect")
            self.status_bar.showMessage("Disconnected from SpaceMouse (device lost)")
            QMessageBox.critical(
                self,
                "SpaceMouse Disconnected",
                "The SpaceMouse has been disconnected or cannot reconnect. Please check the connection and try again."
            ) 

    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller onefile."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path) 