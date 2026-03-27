import serial
import time
import struct

PORT = "/dev/cu.usbmodem58B60156681"
BAUD = 9600

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return struct.pack('<H', crc)

def send(ser, name, frame_hex):
    frame = bytes.fromhex(frame_hex)
    cmd = frame + crc16(frame)
    print(f"\n{name}")
    print(f"  TX: {cmd.hex(' ')}")
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.5)
    resp = ser.read(16)
    print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    return resp

ser = serial.Serial(port=PORT, baudrate=BAUD,
                    bytesize=8, parity='N', stopbits=1, timeout=2)

# From your command sheet:
# FF 06 B1 CB FF AA 0B 59  — ID 255 to 170 (0xAA)
# AA 06 B1 CB AA 0A 38 74  — ID 170 to 10
#
# Pattern: <current_id> 06 B1 CB <new_id_hi> <new_id_lo> CRC
# So to change from 0x01 back to 0xAA:
#   device=0x01, reg=0xB1CB, value=0xAA (170 decimal = 0x00AA)

send(ser, "Change ID: 0x01 → 0xAA", "0106B1CB00AA")

time.sleep(1)

# Verify — try reading with new ID 0xAA
print("\nVerifying with new ID 0xAA...")
verify_frame = bytes([0xAA, 0x03, 0x00, 0xC9, 0x00, 0x01])
verify_cmd = verify_frame + crc16(verify_frame)
print(f"  TX: {verify_cmd.hex(' ')}")
ser.reset_input_buffer()
ser.write(verify_cmd)
time.sleep(0.5)
resp = ser.read(16)
if resp and resp[0] == 0xAA:
    print(f"  ✅ Meter responding as 0xAA again! RX: {resp.hex(' ')}")
else:
    print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    print("  If no response, try running again — meter may need a moment to apply new ID")

ser.close()