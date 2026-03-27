import serial
import struct
import time

PORT = "/dev/cu.usbmodem58B60156681"
BAUD = 9600
DEVICE_ID = 0xAA

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return struct.pack('<H', crc)

def build_read(device_id, start_addr, count):
    frame = bytes([
        device_id,
        0x03,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    ])
    return frame + crc16(frame)

def read_block(ser, device_id, start_addr, count):
    cmd = build_read(device_id, start_addr, count)

    print(f"\nSending request for registers {start_addr}–{start_addr+count-1}")
    print("TX:", cmd.hex(" "))

    ser.reset_input_buffer()
    ser.write(cmd)

    header = ser.read(3)
    if len(header) < 3:
        print("No response")
        return None

    byte_count = header[2]
    data = ser.read(byte_count + 2)

    print("RX:", (header + data).hex(" "))

    values = []
    for i in range(0, byte_count, 2):
        reg = struct.unpack(">H", data[i:i+2])[0]
        values.append(reg)

    return values


ser = serial.Serial(
    port=PORT,
    baudrate=BAUD,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=1
)

print("\nScanning first 2000 registers...\n")

for addr in range(0, 2000, 10):
    vals = read_block(ser, DEVICE_ID, addr, 10)

    if vals:
        for i, v in enumerate(vals):
            reg_addr = addr + i
            print(f"Register {reg_addr:04d} = {v}")

    time.sleep(0.1)

ser.close()

print("\nScan complete")