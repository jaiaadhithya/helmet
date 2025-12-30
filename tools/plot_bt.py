import argparse
import sys
import time
from collections import deque

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("Install pyserial: pip install pyserial")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Install matplotlib: pip install matplotlib")
    sys.exit(1)


def find_bt_com_port(preferred_name: str | None = None) -> str | None:
    ports = list_ports.comports()
    print("Available COM ports:")
    for p in ports:
        print(f"- {p.device}: {p.description}")
    candidates = []
    for p in ports:
        desc = (p.description or "").lower()
        name = (p.name or "").lower()
        hwid = (p.hwid or "").lower()
        if "bluetooth" in desc or "bluetooth" in hwid:
            candidates.append(p.device)
        # Heuristic: Windows often labels as "Standard Serial over Bluetooth link"
        if "standard serial over bluetooth" in desc:
            candidates.append(p.device)
        if preferred_name and preferred_name.lower() in desc:
            candidates.append(p.device)
    # Deduplicate preserving order
    seen = set()
    result = []
    for d in candidates:
        if d not in seen:
            result.append(d)
            seen.add(d)
    return result[0] if result else None


def wait_for_stream(ser: serial.Serial, probe_seconds: float = 10.0) -> bool:
    deadline = time.time() + probe_seconds
    while time.time() < deadline:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            _ = parse_line(line)
            return True
        except Exception:
            # Ignore non-data lines (e.g., "BT connected")
            pass
    return False


def try_all_ports(baud: int, probe_seconds: float = 10.0) -> str | None:
    ports = list_ports.comports()
    for p in ports:
        dev = p.device
        try:
            ser = serial.Serial(dev, baud, timeout=1)
        except Exception:
            continue
        ok = wait_for_stream(ser, probe_seconds=probe_seconds)
        ser.close()
        if ok:
            return dev
    return None


def parse_line(line: str):
    parts = line.strip().split()
    if len(parts) < 3:
        raise ValueError("expected three floats: a_g alpha_rad_s2 CP")
    a_g = float(parts[0])
    alpha = float(parts[1])
    cp = float(parts[2])
    return a_g, alpha, cp


def main():
    ap = argparse.ArgumentParser(description="Plot MYOSA helmet data from Bluetooth serial")
    ap.add_argument("--port", help="Bluetooth COM port (e.g., COM7). If omitted, auto-detect.")
    ap.add_argument("--baud", type=int, default=115200, help="Baud rate (UI only for SPP)")
    ap.add_argument("--window", type=int, default=600, help="Samples to show in the plot window")
    ap.add_argument("--dump", action="store_true", help="Print raw lines to console for debugging")
    args = ap.parse_args()

    port = args.port or find_bt_com_port(preferred_name="MYOSA-HELMET") or try_all_ports(args.baud)
    if not port:
        print("No Bluetooth COM port found. Pair MYOSA-HELMET and check Device Manager → Ports.")
        sys.exit(2)
    print(f"Connecting to {port} at {args.baud}…")

    try:
        ser = serial.Serial(port, args.baud, timeout=1)
    except Exception as e:
        print(f"Failed to open {port}: {e}")
        print("Trying other COM ports…")
        fallback = try_all_ports(args.baud, probe_seconds=12.0)
        if not fallback:
            print("No working COM port found. Ensure MYOSA-HELMET is paired and its Outgoing COM is selected.")
            sys.exit(3)
        print(f"Connecting to {fallback} at {args.baud}…")
        ser = serial.Serial(fallback, args.baud, timeout=1)

    # Give the SPP link a moment to come up
    print("Waiting for data stream… (press EN on ESP32 if needed)")
    if not wait_for_stream(ser, probe_seconds=12.0):
        print("No data detected. Verify you're using the Outgoing COM and that only one app holds the port.")
        print("You can run with --dump to see raw lines.")
        ser.close()
        sys.exit(4)

    a_win = deque(maxlen=args.window)
    r_win = deque(maxlen=args.window)
    cp_win = deque(maxlen=args.window)

    plt.ion()
    fig, ax = plt.subplots()
    ax.set_title("MYOSA Helmet: a_g, alpha_rad_s2, CP")
    ax.set_xlabel("samples")
    l1, = ax.plot([], [], label="a_g (g)")
    l2, = ax.plot([], [], label="alpha (rad/s^2)")
    l3, = ax.plot([], [], label="CP")
    ax.legend(loc="upper right")

    try:
        while True:
            line = ser.readline().decode(errors="ignore")
            if not line:
                continue
            if args.dump:
                print(line.strip())
                continue
            try:
                a_g, alpha, cp = parse_line(line)
            except Exception:
                continue
            a_win.append(a_g)
            r_win.append(alpha)
            cp_win.append(cp)
            l1.set_data(range(len(a_win)), list(a_win))
            l2.set_data(range(len(r_win)), list(r_win))
            l3.set_data(range(len(cp_win)), list(cp_win))
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
