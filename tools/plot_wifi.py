import argparse
import socket
import sys
import time
import csv
from datetime import datetime
from collections import deque

try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button
except ImportError:
    print("Install matplotlib: pip install matplotlib")
    sys.exit(1)

try:
    from openpyxl import Workbook
    OPENPYXL = True
except ImportError:
    OPENPYXL = False


def parse_line(line: str):
    parts = line.strip().split()
    if len(parts) < 3:
        raise ValueError("expected three floats: a_g alpha_rad_s2 CP")
    a_g = float(parts[0])
    alpha = float(parts[1])
    cp = float(parts[2])
    return a_g, alpha, cp


def main():
    ap = argparse.ArgumentParser(description="Plot MYOSA helmet data over Wi-Fi TCP")
    ap.add_argument("--host", default="192.168.4.1", help="ESP32 AP IP (default 192.168.4.1)")
    ap.add_argument("--port", type=int, default=8080, help="TCP port (default 8080)")
    ap.add_argument("--window", type=int, default=600, help="Samples to show in the plot window")
    ap.add_argument("--dump", action="store_true", help="Print raw lines for debugging")
    args = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((args.host, args.port))
    except Exception as e:
        print(f"Failed to connect to {args.host}:{args.port} — {e}")
        print("Connect your laptop to the ESP32 AP 'MYOSA-HELMET-AP' and try again.")
        sys.exit(2)
    f = s.makefile("r", encoding="utf-8", errors="ignore")

    a_win = deque(maxlen=args.window)
    r_win = deque(maxlen=args.window)
    cp_win = deque(maxlen=args.window)

    plt.ion()
    fig, ax = plt.subplots()
    ax.set_title("MYOSA Helmet: a_g, alpha_rad_s2, CP (Wi-Fi)")
    ax.set_xlabel("samples")
    l1, = ax.plot([], [], label="a_g (g)")
    l2, = ax.plot([], [], label="alpha (rad/s^2)")
    l3, = ax.plot([], [], label="CP")
    ax.legend(loc="upper right")

    def save_excel(event=None):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"myosa_data_{ts}.xlsx"
        if OPENPYXL:
            wb = Workbook()
            ws = wb.active
            ws.title = "MYOSA"
            ws.append(["index", "a_g", "alpha_rad_s2", "CP"])
            n = min(len(a_win), len(r_win), len(cp_win))
            for i in range(n):
                ws.append([i, a_win[i], r_win[i], cp_win[i]])
            wb.save(path)
            print(f"Saved {path}")
        else:
            path = f"myosa_data_{ts}.csv"
            with open(path, "w", newline="") as fcsv:
                w = csv.writer(fcsv)
                w.writerow(["index", "a_g", "alpha_rad_s2", "CP"])
                n = min(len(a_win), len(r_win), len(cp_win))
                for i in range(n):
                    w.writerow([i, a_win[i], r_win[i], cp_win[i]])
            print(f"Saved {path} (install openpyxl for .xlsx)")

    btn_ax = fig.add_axes([0.8, 0.92, 0.18, 0.06])
    btn = Button(btn_ax, "Save Excel")
    btn.on_clicked(save_excel)

    try:
        while True:
            try:
                line = f.readline()
            except (TimeoutError, OSError):
                continue
            if not line:
                time.sleep(0.01)
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
        try:
            f.close()
        except Exception:
            pass
        s.close()


if __name__ == "__main__":
    main()
