import machine
import time
import sys
import select

servo_pins = [0, 1, 2, 3, 4, 5, 6, 7]
servos = [machine.PWM(machine.Pin(pin), freq=50) for pin in servo_pins]

def degrees_to_duty(degrees):
    min_pulse_width = 500
    max_pulse_width = 2400
    pulse_width = min_pulse_width + (degrees / 180.0) * (max_pulse_width - min_pulse_width)
    return int((pulse_width / 20000.0) * 65535)

def move_servos(positions):
    for servo, position in zip(servos, positions):
        if 0 <= position <= 180:
            servo.duty_u16(degrees_to_duty(position))
        else:
            print(f"Warning: Position {position} out of bounds.")
    time.sleep(0.5)

def read_command():
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.readline().strip()
    return None

while True:
    command = read_command()
    if command:
        try:
            commands = command.split(';')
            for cmd in commands:
                positions = list(map(int, cmd.split(',')))
                move_servos(positions)
        except ValueError:
            print("Invalid Position")
    time.sleep(0.1)