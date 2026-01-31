import http.client
import ssl
import argparse
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse
import sys
import shutil
import time
import signal

# ANSI colors
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

stop_event = threading.Event()

def print_banner():
    print(r"""
██████╗ ██╗██████╗ ███████╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗
██╔══██╗██║██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝
██║  ██║██║██████╔╝█████╗  ██║        ██║   ██║   ██║██████╔╝ ╚████╔╝ 
██║  ██║██║██╔══██╗██╔══╝  ██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝  
██████╔╝██║██║  ██║███████╗╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║   
╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   

███████╗██╗███╗   ██╗██████╗ ███████╗██████╗ 
██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔══██╗
█████╗  ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝
██╔══╝  ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
██║     ██║██║ ╚████║██████╔╝███████╗██║  ██║
╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝

        DIRECTORYFINDER
        Fast • Threaded • Web Directory Fuzzer
""")

def request_path(base_url, path, timeout, out_q):
    if stop_event.is_set():
        return

    parsed = urlparse(base_url)
    scheme = parsed.scheme or "http"
    host = parsed.netloc or parsed.path
    target = f"/{path.lstrip('/')}"

    try:
        if scheme == "https":
            ctx = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(host, timeout=timeout, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, timeout=timeout)

        conn.request("GET", target, headers={"User-Agent": "DeathNote-DirFuzz"})
        resp = conn.getresponse()
        body = resp.read()
        status = resp.status
        size = len(body)
        conn.close()

        out_q.put((status, size, target))
    except Exception:
        out_q.put((None, 0, target))

def now():
    return datetime.now().strftime("%H:%M:%S")

def color_status(status):
    if status == 200:
        return GREEN
    elif 300 <= status < 500:
        return BLUE
    else:
        return RED

def format_eta(seconds):
    if seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def render_progress(done, total, start_time):
    term_width = shutil.get_terminal_size((100, 20)).columns

    elapsed = time.time() - start_time
    rate = done / elapsed if elapsed > 0 else 0
    remaining = total - done
    eta = remaining / rate if rate > 0 else 0
    percent = (done / total) * 100

    meta = f"{percent:.1f}% | {rate:5.1f} req/s | {done}/{total} | ETA {format_eta(eta)}"
    bar_width = max(10, term_width - len(meta) - 15)

    filled = int(bar_width * done / total)
    bar = "#" * filled + " " * (bar_width - filled)

    return f"Progress: [{bar}] {meta}"

def printer_loop(out_q, total, found_200, stats):
    completed = 0
    start_time = time.time()

    sys.stdout.write(GREEN + render_progress(0, total, start_time) + RESET)
    sys.stdout.flush()

    while completed < total:
        if stop_event.is_set() and out_q.empty():
            break

        try:
            status, size, path = out_q.get(timeout=0.1)
        except queue.Empty:
            continue

        completed += 1
        sys.stdout.write("\r\033[2K")

        if status is not None:
            if 200 <= status < 300:
                stats["2xx"] += 1
                found_200.append(path)
            elif 300 <= status < 400:
                stats["3xx"] += 1
            elif 400 <= status < 500:
                stats["4xx"] += 1
            else:
                stats["5xx"] += 1

            size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
            color = color_status(status)

            print(
                f"{color}[{now()}] "
                f"{status} - "
                f"{size_str:>6} - "
                f"{path}{RESET}"
            )

        sys.stdout.write(GREEN + render_progress(completed, total, start_time) + RESET)
        sys.stdout.flush()

    print()

def main():
    def handle_sigint(sig, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigint)

    print_banner()

    parser = argparse.ArgumentParser(description="DeathNote Dir Fuzzer")
    parser.add_argument("url")
    parser.add_argument("-w", "--wordlist", required=True)
    parser.add_argument("-t", "--threads", type=int, default=50)
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args()

    with open(args.wordlist, "r", errors="ignore") as f:
        words = [w.strip() for w in f if w.strip()]

    total = len(words)
    found_200 = []
    stats = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    out_q = queue.Queue()

    printer = threading.Thread(
        target=printer_loop,
        args=(out_q, total, found_200, stats),
        daemon=True
    )
    printer.start()

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        for word in words:
            if stop_event.is_set():
                break
            executor.submit(request_path, args.url, word, args.timeout, out_q)

    printer.join()

    print("\nScan summary:")
    print(f"  2xx: {stats['2xx']}")
    print(f"  3xx: {stats['3xx']}")
    print(f"  4xx: {stats['4xx']}")
    print(f"  5xx: {stats['5xx']}")

    if found_200:
        print(GREEN + "\n[+] Paths with 200 OK:" + RESET)
        for p in found_200:
            print(f"{GREEN}    {p}{RESET}")

if __name__ == "__main__":
    main()
