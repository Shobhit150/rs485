import serial
import time
import json

with open("command.json", "r") as f:
    raw = json.load(f)
    commands = {k: v.replace(" ", "") for k, v in raw.items()}

PORT = "/dev/cu.usbmodem58B60156681"

def send_command(ser, name):
    if name not in commands:
        print(f"Unknown command: {name}")
        return False

    cmd = bytes.fromhex(commands[name])
    print(f"\nSending [{name}]: {cmd.hex(' ')}")

    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.3)

    response = ser.read(16)
    if response:
        print(f"Response: {response.hex(' ')}")
        return True
    else:
        print("No response")
        return False


ser = serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=2
)

currentCommand = "offBoth"

if currentCommand == "onBoth":
    send_command(ser, "onEb")
    time.sleep(0.3)
    send_command(ser, "onDg")

elif currentCommand == "offBoth":
    send_command(ser, "offEb")
    time.sleep(0.3)
    send_command(ser, "offDg")

else:
    send_command(ser, currentCommand)

ser.close()