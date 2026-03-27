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

def send(ser, name, cmd_bytes):
    print(f"\nSending: {name}")
    print(f"  TX: {cmd_bytes.hex(' ')}")
    ser.reset_input_buffer()
    ser.write(cmd_bytes)
    time.sleep(0.5)
    resp = ser.read(16)
    print(f"  RX: {resp.hex(' ') if resp else '(none)'}")
    return resp

ser = serial.Serial(port=PORT, baudrate=BAUD,
                    bytesize=8, parity='N', stopbits=1, timeout=2)

print("=" * 50)
print("  METER RECOVERY")
print("=" * 50)

# ── Step 1: Factory Reset ──────────────────────
# From your command sheet: S.No 22 = FACTORY RESET
# Address pattern follows other commands: AA 06 B1 xx
# Using AA 06 B1 CE 00 00 + CRC  (CE = next after CC=overload clear)
# Most likely address — if this doesn't work, try the ones below

factory_reset_candidates = [
    ("Factory Reset 0xCE", bytes.fromhex("AA06B1CE0000") ),
    ("Factory Reset 0xCD", bytes.fromhex("AA06B1CD0000") ),
    ("Factory Reset 0xCF", bytes.fromhex("AA06B1CF0000") ),
]

for name, frame in factory_reset_candidates:
    cmd = frame + crc16(frame)
    send(ser, name, cmd)
    time.sleep(1)

# ── Step 2: Force relay default (clears forced state) ─
# AA 06 B1 BB 00 00 = RELAY DEFAULT (from your command list)
relay_default_frame = bytes.fromhex("AA06B1BB0000")
relay_default = relay_default_frame + crc16(relay_default_frame)
send(ser, "Relay Default (BB)", relay_default)
time.sleep(0.3)

# ── Step 3: Clear overload fault ──────────────
# AA 06 B1 CC 00 00 (known working command)
overload_clear_frame = bytes.fromhex("AA06B1CC0000")
overload_clear = overload_clear_frame + crc16(overload_clear_frame)
send(ser, "Clear Overload Fault", overload_clear)
time.sleep(0.3)

# ── Step 4: Force relay ON both ───────────────
# AA 06 B1 F2 00 01 = EB RELAY ON
# AA 06 B1 F3 00 01 = DG RELAY ON
eb_on_frame = bytes.fromhex("AA06B1F20001")
eb_on = eb_on_frame + crc16(eb_on_frame)
send(ser, "EB Relay ON (F2)", eb_on)
time.sleep(0.3)

dg_on_frame = bytes.fromhex("AA06B1F30001")
dg_on = dg_on_frame + crc16(dg_on_frame)
send(ser, "DG Relay ON (F3)", dg_on)
time.sleep(0.3)

ser.close()

print("\n" + "=" * 50)
print("  Done. Check if relays are back ON.")
print("  If still stuck, add balance:")
print("  AA 06 B1 B5 2C 01 CRC  (300 Rs)")
print("=" * 50)