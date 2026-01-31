# directoryfinder
DirectoryFinder is a fast, threaded web directory and file fuzzer written in Python.   It performs concurrent HTTP requests against a target URL using a wordlist and provides live results with a real-time progress bar, request rate, ETA, and graceful interruption handling.

## Features

- Multi-threaded directory brute forcing
- Live output of discovered paths
- Color-coded HTTP status codes
- Static bottom progress bar with:
  - Percentage completed
  - Requests per second
  - Completed / total requests
  - Estimated time remaining (ETA)
- Graceful Ctrl+C handling with partial results summary
- Automatic terminal width detection
- HTTPS support (certificate verification disabled by default)
- Summary of HTTP status codes (2xx / 3xx / 4xx / 5xx)
- Final list of discovered `200 OK` paths

---

## Requirements

- Python **3.8+**
- Linux / macOS / Windows (tested mainly on Linux)
- Internet connectivity to target

No external Python libraries are required.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/jameskyle1000/directoryfinder.git
cd directoryfinder

(Optional but recommended) Create a virtual environment:
python3 -m venv venv
source venv/bin/activate

Usage

Basic usage:
python3 directoryfinder.py http://example.com -w wordlist.txt

Example
python3 directoryfinder.py https://target.site -w common.txt -t 100 --timeout 3


Notes

HTTPS certificate verification is disabled to avoid scan interruption

Some servers return fake 200 or same-size responses for non-existing paths — always validate manually

Very high thread counts may cause rate limiting or inaccurate results

Disclaimer

This tool is intended for authorized security testing and educational purposes only.
Do not scan systems you do not own or have explicit permission to test.

The author is not responsible for misuse or illegal activity.
