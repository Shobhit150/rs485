"""
sniffer.py
──────────
Passively listens on the RS485 line and logs ALL traffic.
Run this while the hub does its force-read cycle.
Captures the exact command the hub sends + the meter's response.

Usage:
  1. Connect your USB-RS485 adapter to the same bus as the hub
  2. Run this script BEFORE the hub's next read cycle
  3. Watch the output — you'll see the hub's read command and meter's reply
"""
import serial
import time
from datetime import datetime

PORT = "/dev/cu.usbmodem58B60156681"
BAUD = 9600
LISTEN_SECONDS = 120   # listen for 2 minutes — adjust to cover hub's read cycle

def is_printable(b):
    return 32 <= b <= 126

def parse_frame(data: bytes, direction: str):
    hex_str = data.hex(' ')
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n{'─'*60}")
    print(f"  [{ts}] {direction}  ({len(data)} bytes)")
    print(f"  HEX : {hex_str}")

    # Try to decode as AA 06 write command
    if len(data) >= 8 and data[0] == 0xAA and data[1] == 0x06:
        addr = (data[2] << 8) | data[3]
        val  = (data[4] << 8) | data[5]
        print(f"  TYPE: WRITE command")
        print(f"  ADDR: 0x{addr:04X}  VALUE: {val} (0x{val:04X})")

    # Try to decode as AA 03 read command
    elif len(data) >= 8 and data[0] == 0xAA and data[1] == 0x03:
        addr  = (data[2] << 8) | data[3]
        count = (data[4] << 8) | data[5]
        print(f"  TYPE: READ command (FC03)")
        print(f"  ADDR: 0x{addr:04X}  COUNT: {count}")

    # Try to decode as a read response (AA 03 02 <hi> <lo> CRC)
    elif len(data) >= 7 and data[0] == 0xAA and data[1] == 0x03 and data[2] == 0x02:
        val = (data[3] << 8) | data[4]
        print(f"  TYPE: READ RESPONSE")
        print(f"  VALUE: {val} (0x{val:04X})")

    # Unknown frame — show device ID and function code
    elif len(data) >= 2:
        print(f"  DEV : 0x{data[0]:02X}  FC: 0x{data[1]:02X}")

    # ASCII attempt
    ascii_str = ''.join(chr(b) if is_printable(b) else '.' for b in data)
    print(f"  ASCII: {ascii_str}")


def main():
    ser = serial.Serial(
        port=PORT, baudrate=BAUD,
        bytesize=8, parity='N', stopbits=1,
        timeout=0.05
    )

    print("=" * 60)
    print("  RS485 BUS SNIFFER")
    print(f"  Listening on {PORT} @ {BAUD} baud")
    print(f"  Duration: {LISTEN_SECONDS} seconds")
    print()
    print("  !! Trigger the hub's force-read NOW !!")
    print("=" * 60)

    all_frames = []
    start = time.time()
    buf = b""
    last_byte_time = time.time()
    FRAME_GAP = 0.015   # 15ms silence = frame boundary

    while time.time() - start < LISTEN_SECONDS:
        chunk = ser.read(64)

        if chunk:
            buf += chunk
            last_byte_time = time.time()
        else:
            # Silence gap — flush current buffer as a frame
            if buf and (time.time() - last_byte_time) > FRAME_GAP:
                parse_frame(buf, "BUS TRAFFIC")
                all_frames.append((time.time(), buf))
                buf = b""

        elapsed = time.time() - start
        if int(elapsed) % 10 == 0 and elapsed > 1:
            remaining = LISTEN_SECONDS - int(elapsed)
            print(f"  ... {remaining}s remaining, {len(all_frames)} frames captured so far", end='\r')

    # Flush remaining
    if buf:
        parse_frame(buf, "BUS TRAFFIC")
        all_frames.append((time.time(), buf))

    ser.close()

    print(f"\n\n{'='*60}")
    print(f"  CAPTURE COMPLETE — {len(all_frames)} frames")
    print(f"{'='*60}")

    if all_frames:
        print("\n  ── Frame summary ──────────────────────────────────────")
        for i, (ts, frame) in enumerate(all_frames):
            print(f"  [{i+1:02d}] {frame.hex(' ')}")

        print("\n  ── Look for pairs: command followed by response ────────")
        print("  The hub's READ command will be followed within ~50ms")
        print("  by the meter's response with actual data values.")

        # Save raw capture to file
        with open("capture.bin", "wb") as f:
            for ts, frame in all_frames:
                f.write(frame)
        print("\n  Raw capture saved to: capture.bin")
    else:
        print("\n  No traffic captured.")
        print("  Make sure:")
        print("  1. Your adapter is wired to the SAME RS485 A/B terminals as the hub")
        print("  2. The hub's read cycle ran during the capture window")
        print("  3. Try increasing LISTEN_SECONDS to cover the hub's full cycle")


if __name__ == "__main__":
    main()