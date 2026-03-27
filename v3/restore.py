import serial
import struct
import time

PORT = "/dev/cu.usbmodem58B60156681"
BAUD = 9600

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return struct.pack('<H', crc)

def send_write(ser, name, addr, value):
    frame = bytes([0xAA, 0x06,
                   (addr >> 8) & 0xFF, addr & 0xFF,
                   (value >> 8) & 0xFF, value & 0xFF])
    cmd = frame + crc16(frame)
    print(f"  {name}")
    print(f"    TX: {cmd.hex(' ')}")
    ser.reset_input_buffer()
    ser.write(cmd)
    time.sleep(0.4)
    resp = ser.read(16)
    ok = "✅" if resp == cmd else ("⚠️  " + resp.hex(' ') if resp else "❌ no response")
    print(f"    RX: {ok}")
    return resp == cmd

ser = serial.Serial(port=PORT, baudrate=BAUD,
                    bytesize=8, parity='N', stopbits=1, timeout=1)

print("=" * 55)
print("  RESTORE METER SETTINGS")
print("=" * 55)

# ── Tariff settings (were 0xFFFE = unset) ─────────────────────
# From your original commands:
# AA 06 B1 B3 DC 05 = DG tariff 15 Rs  (1500 = 0x05DC)
# AA 06 B1 B4 78 05 = EB tariff 14 Rs  (1400 = 0x0578)
print("\n── Tariff Settings ────────────────────────────────")
send_write(ser, "DG Tariff = 15 Rs  (0x05DC)", 0xB1B3, 0x05DC)
send_write(ser, "EB Tariff = 14 Rs  (0x0578)", 0xB1B4, 0x0578)

# ── Monthly deduction ─────────────────────────────────────────
# AA 06 B1 CA 78 00 = 120 Rs/month
print("\n── Monthly / Daily Deduction ──────────────────────")
send_write(ser, "Monthly deduction = 120 Rs (0x0078)", 0xB1CA, 0x0078)
send_write(ser, "Daily charge = 5 Rs (0x01F4)",        0xB1B6, 0x01F4)

# ── Happy Hour / Day (were 0xFFFF = unset) ────────────────────
# AA 06 B1 C7 0A 0C = Happy Day 10/12
# AA 06 B1 C8 11 12 = Happy Hour 17-18
print("\n── Happy Hour / Day ───────────────────────────────")
send_write(ser, "Happy Day  10/12  (0x0A0C)", 0xB1C7, 0x0A0C)
send_write(ser, "Happy Hour 17-18  (0x1112)", 0xB1C8, 0x1112)

# ── Negative balance limit ────────────────────────────────────
# Currently 50 Rs — set back to 300 Rs
print("\n── Balance Settings ───────────────────────────────")
send_write(ser, "Neg balance limit = 300 Rs (0x012C)", 0xB1F1, 0x012C)
send_write(ser, "Balance recharge  = 300 Rs (0x012C)", 0xB1B5, 0x012C)

# ── Overload settings ─────────────────────────────────────────
print("\n── Overload Settings ──────────────────────────────")
send_write(ser, "Overload attempts = 2 (0x0002)",    0xB1B7, 0x0002)
send_write(ser, "Overload delay    = 32s (0x0020)",  0xB1B8, 0x0020)

# ── Load settings (already correct at 30kW but set explicitly) 
# 4.8kW = 480 = 0x01E0  OR  30kW = 3000 = 0x0BB8
# Your current read shows 3000 so keeping that
print("\n── Relay ON ───────────────────────────────────────")
send_write(ser, "Clear overload fault",    0xB1CC, 0x0000)
time.sleep(0.3)
send_write(ser, "Relay default (clear forced)", 0xB1BB, 0x0000)
time.sleep(0.3)
send_write(ser, "EB Relay ON",  0xB1F2, 0x0001)
time.sleep(0.3)
send_write(ser, "DG Relay ON",  0xB1F3, 0x0001)

ser.close()

print("\n" + "=" * 55)
print("  Done — now run read_32bit.py to verify")
print("  Expected after this:")
print("    Relay Status EB → NORMAL ON")
print("    Tariff EB       → 14.00 Rs")
print("    Tariff DG       → 15.00 Rs")
print("    Balance         → 300.00 Rs")
print("=" * 55)