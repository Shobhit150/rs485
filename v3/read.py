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

def build_read(device_id, start_addr, count):
    frame = bytes([device_id, 0x03,
                   (start_addr >> 8) & 0xFF, start_addr & 0xFF,
                   (count >> 8) & 0xFF, count & 0xFF])
    return frame + crc16(frame)

def read_block(ser, device_id, start_addr, count):
    cmd = build_read(device_id, start_addr, count)
    ser.reset_input_buffer()
    ser.write(cmd)
    header = b""
    deadline = time.time() + 3.0
    while len(header) < 3 and time.time() < deadline:
        header += ser.read(3 - len(header))
    if len(header) < 3 or header[1] != 0x03:
        return None
    byte_count = header[2]
    data = b""
    while len(data) < byte_count + 2 and time.time() < deadline:
        data += ser.read(byte_count + 2 - len(data))
    values = []
    for i in range(0, min(byte_count, len(data)) - 3, 4):
        val = struct.unpack('>I', data[i:i+4])[0]
        values.append(val)
    return values

PARAMS = {
    201: ("Meter Serial Number",   1,       "",       None),
    202: ("Frequency",             0.1,     "Hz",     None),
    203: ("PF",                    0.001,   "",       None),
    204: ("Relay Status EB",       1,       "",       "relay"),
    205: ("Relay Status DG",       1,       "",       "relay"),
    206: ("Tariff EB",             0.01,    "Rs",     "ffff"),
    207: ("Tariff DG",             0.01,    "Rs",     "ffff"),
    208: ("Voltage EB",            0.1,     "V",      None),
    209: ("Voltage DG",            0.1,     "V",      None),
    210: ("Current EB",            0.01,    "A",      None),
    211: ("Current DG",            0.01,    "A",      None),
    212: ("KWH EB",                0.01,    "kWh",    None),
    213: ("KWH DG",                0.01,    "kWh",    None),
    214: ("Negative Balance",      0.01,    "Rs",     None),
    215: ("Neg Balance Limit",     0.01,    "Rs",     None),
    216: ("Balance",               0.001,   "Rs",     None),
    217: ("Tamper",                1,       "",       None),
    218: ("Happy Hour",            1,       "",       "ffff"),
    219: ("Happy Day",             1,       "",       "ffff"),
    220: ("Overload Att. EB",      1,       "",       None),
    221: ("Overload Att. DG",      1,       "",       None),
    222: ("Overload Check No",     1,       "",       None),
    223: ("Overload Delay",        1,       "s",      None),
    224: ("Load Setting EB",       0.01,    "kW",     None),
    225: ("Load Setting DG",       0.01,    "kW",     None),
    226: ("Monthly Tariff",        0.01,    "Rs",     "ffff"),
    227: ("Cum KVAH EB",           0.01,    "kVAh",   None),
    228: ("Cum KVAH DG",           0.01,    "kVAh",   None),
    229: ("Cum KVARH EB",          0.01,    "kVARh",  None),
    230: ("Cum KVARH DG",          0.01,    "kVARh",  None),
    231: ("KW Phase R",            0.01,    "kW",     None),
    232: ("KW Phase Y",            0.01,    "kW",     None),
    233: ("KVA Phase R",           0.01,    "kVA",    None),
    234: ("KVA Phase Y",           0.01,    "kVA",    None),
    235: ("KVAR Phase R",          0.01,    "kVAR",   None),
    236: ("KVAR Phase Y",          0.01,    "kVAR",   None),
    237: ("Total KW",              0.01,    "kW",     None),
    238: ("Total KVA",             0.01,    "kVA",    None),
    239: ("Total KVAR",            0.01,    "kVAR",   None),
    240: ("RTC Date",              1,       "",       "date"),
    241: ("RTC Time",              1,       "",       "time"),
    254: ("Last Deduction",        0.01,    "Rs",     None),
    255: ("2nd Deduction",         0.01,    "Rs",     None),
    256: ("3rd Deduction",         0.01,    "Rs",     None),
    257: ("4th Deduction",         0.01,    "Rs",     None),
    258: ("5th Deduction",         0.01,    "Rs",     None),
    259: ("6th Deduction",         0.01,    "Rs",     None),
    260: ("7th Deduction",         0.01,    "Rs",     None),
    261: ("8th Deduction",         0.01,    "Rs",     None),
    262: ("9th Deduction",         0.01,    "Rs",     None),
    263: ("10th Deduction",        0.01,    "Rs",     None),
    264: ("Overload Time",         1,       "s",      None),
    265: ("Firmware Version",      1,       "",       None),
}

RELAY_FLAGS = {
    0x00000000: "NORMAL OFF",    0x00000001: "NORMAL ON",
    0x00010000: "relay_off_cmd", 0x00010001: "relay_on_cmd",
    0x00100000: "low_balance",   0x00100001: "national_holiday",
    0x01000000: "over_load",     0x01000001: "happy_hour",
    0x10000000: "overload_limit_count", 0x10000001: "HAPPY_DAY",
}

def display(sno, raw):
    if sno not in PARAMS: return raw, str(raw)
    name, scale, unit, special = PARAMS[sno]
    if special == "relay":
        return raw, RELAY_FLAGS.get(raw, f"0x{raw:08X}")
    if special == "ffff":
        if raw in (0xFFFF, 0xFFFFFFFE, 0xFFFFFFFF, 65534, 65535):
            return raw, "⚠️  NOT SET"
        return raw, f"{raw * scale:.2f} {unit}".strip()
    if special == "date":
        s = f"{raw:06d}"; return raw, f"{s[0:2]}/{s[2:4]}/{s[4:6]}"
    if special == "time":
        s = f"{raw:06d}"; return raw, f"{s[0:2]}:{s[2:4]}:{s[4:6]}"
    if scale == 1: return raw, f"{raw} {unit}".strip()
    return raw, f"{raw * scale:.3f} {unit}".strip()

ser = serial.Serial(port=PORT, baudrate=BAUD, bytesize=8, parity='N', stopbits=1, timeout=1)
print("=" * 62)
print("  METER READ  (32-bit, corrected scales)")
print("=" * 62)

results = {}
vals = read_block(ser, 0xAA, 0x00C9, 41)
if vals:
    for i, v in enumerate(vals): results[201 + i] = v

time.sleep(0.2)
vals2 = read_block(ser, 0xAA, 0x00FE, 12)
if vals2:
    for i, v in enumerate(vals2): results[254 + i] = v

ser.close()

print(f"\n  {'S.No':<6} {'Parameter':<26} {'Raw':>10}  Value")
print(f"  {'─'*4:<6} {'─'*24:<26} {'─'*8:>10}  {'─'*22}")
for sno in sorted(results):
    if sno not in PARAMS: continue
    raw, val = display(sno, results[sno])
    name = PARAMS[sno][0]
    print(f"  {sno:<6} {name:<26} {raw:>10}  {val}")
print(f"\n  {len(results)} parameters read")