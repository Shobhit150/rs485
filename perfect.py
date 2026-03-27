import serial
import time
import json

with open("command.json", "r") as f:
    commands = json.load(f)

ser = serial.Serial(
    port="/dev/cu.usbmodem58B60156681",
    baudrate=9600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=2
)

cmd = bytes.fromhex(commands["onBoth"])

bytes_written = ser.write(cmd)

time.sleep(2)

waiting = ser.in_waiting

if waiting > 0:
    response = ser.read(waiting)
    print("Received:", response.hex(' '))
else:
    response = ser.read(64)
    if response:
        print("Received:", response.hex(' '))
    else:
        print("No response received")

ser.close()