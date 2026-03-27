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

def read_block(ser, device_id, start_addr, count, bits=32):
    """Read block. bits=32 means each register is 4 bytes (2 Modbus registers)."""
    cmd = build_read(device_id, start_addr, count)
    # byte_count in response header tells us how many data bytes to expect
    print(f"  TX: {cmd.hex(' ')}")

    ser.reset_input_buffer()
    ser.write(cmd)

    # Read header first (3 bytes: dev_id, fc, byte_count)
    deadline = time.time() + 3.0
    header = b""
    while len(header) < 3 and time.time() < deadline:
        chunk = ser.read(3 - len(header))
        if chunk:
            header += chunk

    if len(header) < 3:
        print(f"  ❌ No header received")
        return None

    dev, fc, byte_count = header[0], header[1], header[2]
    print(f"  Header: dev=0x{dev:02X} fc=0x{fc:02X} byte_count={byte_count}")

    if dev != device_id or fc != 0x03:
        print(f"  ❌ Bad header")
        return None

    # Now read remaining data + 2 CRC bytes
    remaining = byte_count + 2
    data = b""
    while len(data) < remaining and time.time() < deadline:
        chunk = ser.read(remaining - len(data))
        if chunk:
            data += chunk

    print(f"  Data ({len(data)} bytes): {data[:byte_count].hex(' ')}")

    if len(data) < byte_count:
        print(f"  ⚠️  Only got {len(data)} of {remaining} expected bytes")

    # Parse as 32-bit big-endian values (4 bytes each)
    values = []
    raw = data[:byte_count]
    for i in range(0, len(raw) - 3, 4):
        val = struct.unpack('>I', raw[i:i+4])[0]
        values.append(val)

    return values

# ── Parameter definitions ──────────────────────────────────────
# (name, scale, unit)
PARAMS = {
    201: ("Meter Serial Number",   1,      ""),
    202: ("Frequency",             0.01,   "Hz"),
    203: ("PF",                    0.01,   ""),
    204: ("Relay Status EB",       None,   ""),   # special decode
    205: ("Relay Status DG",       None,   ""),
    206: ("Tariff EB",             0.01,   "Rs"),
    207: ("Tariff DG",             0.01,   "Rs"),
    208: ("Voltage EB",            0.1,    "V"),
    209: ("Voltage DG",            0.1,    "V"),
    210: ("Current EB",            0.01,   "A"),
    211: ("Current DG",            0.01,   "A"),
    212: ("KWH EB",                0.01,   "kWh"),
    213: ("KWH DG",                0.01,   "kWh"),
    214: ("Negative Balance",      0.01,   "Rs"),
    215: ("Neg Balance Limit",     0.01,   "Rs"),
    216: ("Balance",               0.01,   "Rs"),
    217: ("Tamper",                1,      ""),
    218: ("Happy Hour",            1,      ""),
    219: ("Happy Day",             1,      ""),
    220: ("Overload Att. EB",      1,      ""),
    221: ("Overload Att. DG",      1,      ""),
    222: ("Overload Check No",     1,      ""),
    223: ("Overload Delay",        1,      "s"),
    224: ("Load Setting EB",       0.01,   "kW"),
    225: ("Load Setting DG",       0.01,   "kW"),
    226: ("Monthly Tariff",        0.01,   "Rs"),
    227: ("Cum KVAH EB",           0.01,   "kVAh"),
    228: ("Cum KVAH DG",           0.01,   "kVAh"),
    229: ("Cum KVARH EB",          0.01,   "kVARh"),
    230: ("Cum KVARH DG",          0.01,   "kVARh"),
    231: ("KW Phase R",            0.01,   "kW"),
    232: ("KW Phase Y",            0.01,   "kW"),
    233: ("KVA Phase R",           0.01,   "kVA"),
    234: ("KVA Phase Y",           0.01,   "kVA"),
    235: ("KVAR Phase R",          0.01,   "kVAR"),
    236: ("KVAR Phase Y",          0.01,   "kVAR"),
    237: ("Total KW",              0.01,   "kW"),
    238: ("Total KVA",             0.01,   "kVA"),
    239: ("Total KVAR",            0.01,   "kVAR"),
    240: ("RTC Date (DDMMYY)",     1,      ""),
    241: ("RTC Time (HHMMSS)",     1,      ""),
    254: ("Last Deduction",        0.01,   "Rs"),
    255: ("2nd Deduction",         0.01,   "Rs"),
    256: ("3rd Deduction",         0.01,   "Rs"),
    257: ("4th Deduction",         0.01,   "Rs"),
    258: ("5th Deduction",         0.01,   "Rs"),
    259: ("6th Deduction",         0.01,   "Rs"),
    260: ("7th Deduction",         0.01,   "Rs"),
    261: ("8th Deduction",         0.01,   "Rs"),
    262: ("9th Deduction",         0.01,   "Rs"),
    263: ("10th Deduction",        0.01,   "Rs"),
    264: ("Overload Time",         1,      "s"),
    265: ("Firmware Version",      1,      ""),
}

RELAY_FLAGS = {
    0x00010000: "relay_off_cmd",
    0x00100000: "low_balance",
    0x01000000: "over_load",
    0x10000000: "overload_limit_count",
    0x00010001: "relay_on_cmd",
    0x00100001: "national_holiday",
    0x01000001: "happy_hour",
    0x10000001: "HAPPY_DAY",
    0x00000000: "NORMAL OFF",
    0x00000001: "NORMAL ON",
}

def decode_relay(val):
    return RELAY_FLAGS.get(val, f"0x{val:08X}")

def format_rtc_date(val):
    # DDMMYY as integer e.g. 130325 = 13/03/25
    s = f"{val:06d}"
    return f"{s[0:2]}/{s[2:4]}/{s[4:6]}"

def format_rtc_time(val):
    s = f"{val:06d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"

def display(sno, raw):
    if sno not in PARAMS:
        return str(raw)
    name, scale, unit = PARAMS[sno]
    if scale is None:
        return decode_relay(raw)
    if sno == 240:
        return format_rtc_date(raw)
    if sno == 241:
        return format_rtc_time(raw)
    if scale == 1:
        return f"{raw} {unit}".strip()
    return f"{raw * scale:.2f} {unit}".strip()


ser = serial.Serial(port=PORT, baudrate=BAUD,
                    bytesize=8, parity='N', stopbits=1, timeout=1)

print("=" * 62)
print("  METER READ  (32-bit registers)")
print("=" * 62)

results = {}

print("\nBlock 1: S.No 201–241 (addr=0x00C9, count=41 registers)")
vals = read_block(ser, 0xAA, 0x00C9, 41)
if vals:
    print(f"  Parsed {len(vals)} values")
    for i, v in enumerate(vals):
        results[201 + i] = v

time.sleep(0.3)

print("\nBlock 2: S.No 254–265 (addr=0x00FE, count=12 registers)")
vals2 = read_block(ser, 0xAA, 0x00FE, 12)
if vals2:
    print(f"  Parsed {len(vals2)} values")
    for i, v in enumerate(vals2):
        results[254 + i] = v

ser.close()

print("\n" + "=" * 62)
print(f"  {'S.No':<6} {'Parameter':<28} {'Raw':>10}  Value")
print(f"  {'─'*4:<6} {'─'*26:<28} {'─'*8:>10}  {'─'*20}")

for sno in sorted(results):
    if sno not in PARAMS:
        continue
    raw = results[sno]
    name = PARAMS[sno][0]
    val  = display(sno, raw)
    print(f"  {sno:<6} {name:<28} {raw:>10}  {val}")

print(f"\n  {len(results)} parameters read")