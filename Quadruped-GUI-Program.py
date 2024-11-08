import tkinter as tk
from tkinter import ttk, messagebox
import json
import serial
import time


class Slider:
    """Represents individual servo control sliders."""

    def __init__(self, parent, servo_id, name, x, y, min_val=0, max_val=180):
        self.servo_id = servo_id
        self.name = name
        self.value = min_val

        self.slider = ttk.Scale(parent, from_=min_val, to=max_val, orient='horizontal',
                                command=self.update_value, length=200)

        self.slider.set(min_val)
        self.slider.grid(column=x, row=y)

        # Create the label
        self.label = ttk.Label(parent, text=f"{name}: {min_val}")
        self.label.grid(column=x, row=y + 1)

    def update_value(self, val):
        try:
            self.value = int(float(val))
            self.label.config(text=f"{self.name}: {self.value}")
        except Exception as e:
            print(f"Error updating value for {self.name}: {e}")

    def get_value(self):
        return self.value


class Quadruped:
    """Represents the entire quadruped robot."""

    def __init__(self, parent):
        self.sliders = []
        for i in range(4):
            hip_slider = Slider(parent, f"leg_{i}_hip", f"Leg {i} Hip", 0, i * 4)
            self.sliders.append(hip_slider)
            ankle_slider = Slider(parent, f"leg_{i}_ankle", f"Leg {i} Ankle", 0, i * 4 + 2)
            self.sliders.append(ankle_slider)

    def get_all_positions(self):
        return [slider.get_value() for slider in self.sliders]


class SerialCommunicator:
    """Handles serial communication with the Pico."""

    def __init__(self, port='COM9', baud_rate=115200):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.connection_status_label = None
        self.connect()

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"Connected to {self.port} at {self.baud_rate} baud.")
            if self.connection_status_label:
                self.connection_status_label.config(text="Connected", foreground="green")
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            if self.connection_status_label:
                self.connection_status_label.config(text="Disconnected", foreground="red")

    def send_command(self, command):
        try:
            self.serial.write(command.encode())
            print(f"Sent Positions To Pico: {command.strip()}")
            time.sleep(0.1)
        except Exception as e:
            print(f"Error sending command: {e}")
            messagebox.showerror("Error", f"Failed to send command: {e}")

    def receive_data(self):
        try:
            return self.serial.readline().decode('utf-8').strip()
        except Exception as e:
            print(f"Error receiving data: {e}")
            return ""

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            print(f"Connection to {self.port} closed.")


class StateManager:
    """Handles saving and loading of robot states in JSON."""

    def __init__(self, quadruped):
        self.quadruped = quadruped

    def save_state(self, filename):
        positions = self.quadruped.get_all_positions()
        state_dict = {"positions": positions}

        with open(filename, 'w') as file:
            json.dump(state_dict, file)

        messagebox.showinfo("Info", f"State saved to {filename}")

    def load_state(self, filename):
        try:
            with open(filename, 'r') as json_file:
                state_dict = json.load(json_file)
                positions = state_dict.get("positions", [])

                if len(positions) == 8:
                    for i, slider in enumerate(self.quadruped.sliders):
                        slider.slider.set(positions[i])
                        slider.update_value(positions[i])  # Ensure label updates
                    messagebox.showinfo("Info", "State loaded successfully!")
                else:
                    messagebox.showerror("Error", "Invalid state data!")
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("Error", f"Failed to load state from {filename}.")

    def load_positions(self, filename):
        """Load positions from a JSON file for walking."""
        try:
            with open(filename, 'r') as json_file:
                state_dict = json.load(json_file)
                return state_dict.get("positions", [])
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("Error", f"Failed to load positions from {filename}.")
            return None


class QuadrupedGUI:
    """Main class for the graphical interface."""

    def __init__(self, root):
        self.root = root
        self.root.title("Quadruped Robot Control")
        self.quadruped = Quadruped(root)
        self.serial_communicator = SerialCommunicator()
        self.state_manager = StateManager(self.quadruped)

        self.filename_entry = ttk.Entry(root, width=20)
        self.filename_entry.grid(column=1, row=5)
        self.filename_entry.insert(0, "stand.json")  # Default filename

        self.create_gui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_gui(self):
        ttk.Button(self.root, text="Update Pico", command=self.update_pico).grid(column=1, row=7)
        ttk.Button(self.root, text="Save State", command=self.save_state).grid(column=1, row=8)
        ttk.Button(self.root, text="Load State", command=self.load_state).grid(column=1, row=9)
        ttk.Button(self.root, text="Reset Positions", command=self.reset_positions).grid(column=1, row=10)
        ttk.Button(self.root, text="Walk Left", command=self.walk_left).grid(column=2, row=8)
        ttk.Button(self.root, text="Walk Right", command=self.walk_right).grid(column=2, row=9)

    def walk_left(self):
        positions = self.state_manager.load_positions("left.json")
        if positions:
            self.set_positions(positions)

    def walk_right(self):
        positions = self.state_manager.load_positions("right.json")
        if positions:
            self.set_positions(positions)

    def set_positions(self, positions):
        for index, slider in enumerate(self.quadruped.sliders):
            slider.slider.set(positions[index])
            slider.update_value(positions[index])
        self.update_pico()

    def save_state(self):
        filename = self.filename_entry.get()
        self.state_manager.save_state(filename)

    def load_state(self):
        filename = self.filename_entry.get()
        self.state_manager.load_state(filename)

    def update_pico(self):
        if not self.serial_communicator.serial or not self.serial_communicator.serial.is_open:
            messagebox.showerror("Error", "Not connected to the serial port.")
            return

        positions = self.quadruped.get_all_positions()
        command = ",".join(map(str, positions)) + "\n"
        self.serial_communicator.send_command(command)

        self.serial_communicator.receive_data()

    def reset_positions(self):
        default_positions = [90] * 8
        for index, slider in enumerate(self.quadruped.sliders):
            slider.slider.set(default_positions[index])
            slider.update_value(default_positions[index])
        self.update_pico()

    def on_close(self):
        self.serial_communicator.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = QuadrupedGUI(root)
    root.mainloop()
