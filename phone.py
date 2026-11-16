"""
phone.py - Access your own Android phone (Itel A70) from your laptop using ADB.

Requirements on the laptop:
  - Python 3
  - ADB (platform-tools) in PATH
  - scrcpy in PATH (for screen mirroring)

Requirements on the phone:
  - Developer options ON, USB debugging ON
  - Tap "Allow" on the prompt that appears when you connect
"""

import datetime
import os
import re
import shutil
import subprocess
import sys
import time


def adb(*args, binary=False):
    """Run an adb command and return its output."""
    result = subprocess.run(["adb", *args], capture_output=True)
    if result.returncode != 0:
        print("Error:", result.stderr.decode(errors="ignore").strip())
        return b"" if binary else ""
    return result.stdout if binary else result.stdout.decode(errors="ignore")


def check_tools():
    if not shutil.which("adb"):
        sys.exit("ADB not found. Install platform-tools and add it to PATH.")


def check_device():
    lines = adb("devices").strip().splitlines()[1:]
    if any("unauthorized" in l for l in lines):
        sys.exit("Phone is unauthorized. Unlock it and tap 'Allow' on the USB debugging prompt.")
    if not any(l.endswith("device") for l in lines):
        sys.exit("No phone found. Check the cable, set USB mode to File transfer, and enable USB debugging.")
    print("Phone connected.")


def mirror():
    """Mirror and control the phone screen (tuned for the A70's limited RAM)."""
    if not shutil.which("scrcpy"):
        print("scrcpy not found. Get it from https://github.com/Genymobile/scrcpy")
        return
    subprocess.run(["scrcpy", "-m", "800", "-b", "4M", "--max-fps", "20"])


def screenshot():
    data = adb("exec-out", "screencap", "-p", binary=True)
    name = f"screen_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    with open(name, "wb") as f:
        f.write(data)
    print("Saved", name)


def read_sms(limit=20):
    out = adb("shell", "content", "query", "--uri", "content://sms/inbox",
              "--projection", "address:date:body", "--sort", "date DESC")
    if not out.strip() or "No result" in out:
        print("No SMS returned (this phone may block SMS access over ADB). Use mirroring instead.")
        return
    for line in out.splitlines()[:limit]:
        print(line)


def notifications():
    out = adb("shell", "dumpsys", "notification", "--noredact")
    for line in out.splitlines():
        if any(k in line for k in ("pkg=", "android.title", "android.text")):
            print(line.strip())


def log_notifications(seconds=60, file="notifications.txt"):
    """Save notification titles/text to a file on the laptop for some time."""
    seen = set()
    end = time.time() + seconds
    print(f"Logging notifications for {seconds}s to {file} ...")
    with open(file, "a", encoding="utf-8") as f:
        while time.time() < end:
            out = adb("shell", "dumpsys", "notification", "--noredact")
            for line in out.splitlines():
                if "android.title" in line or "android.text" in line:
                    line = line.strip()
                    if line not in seen:
                        seen.add(line)
                        f.write(f"{datetime.datetime.now():%H:%M:%S} {line}\n")
                        print(line)
            time.sleep(5)


def list_files(path="/sdcard/"):
    print(adb("shell", "ls", "-la", path))


def pull_file(remote, local="."):
    print(adb("pull", remote, local))


def backup_photos():
    dest = f"phone_photos_{datetime.datetime.now():%Y%m%d}"
    os.makedirs(dest, exist_ok=True)
    print("Copying photos from /sdcard/DCIM (this can take a while)...")
    print(adb("pull", "/sdcard/DCIM", dest))


def phone_info():
    for prop in ("ro.product.model", "ro.build.version.release", "ro.product.brand"):
        print(prop, "=", adb("shell", "getprop", prop).strip())
    battery = adb("shell", "dumpsys", "battery")
    m = re.search(r"level: (\d+)", battery)
    if m:
        print("Battery:", m.group(1) + "%")


def go_wireless():
    """Switch from USB to Wi-Fi (phone and laptop must be on the same network)."""
    ip_out = adb("shell", "ip", "route")
    m = re.search(r"src (\d+\.\d+\.\d+\.\d+)", ip_out)
    if not m:
        print("Could not find the phone's Wi-Fi IP. Is Wi-Fi on?")
        return
    ip = m.group(1)
    adb("tcpip", "5555")
    time.sleep(2)
    print(adb("connect", f"{ip}:5555"))
    print("You can unplug the cable now.")


MENU = """
===== Itel A70 Phone Link =====
1) Mirror & control screen (scrcpy)
2) Take screenshot
3) Read recent SMS
4) Show current notifications
5) Log notifications to file
6) Browse files
7) Pull a file to laptop
8) Backup photos
9) Phone info
w) Switch to wireless
q) Quit
"""

if __name__ == "__main__":
    check_tools()
    check_device()
    while True:
        print(MENU)
        c = input("> ").strip().lower()
        if c == "1":
            mirror()
        elif c == "2":
            screenshot()
        elif c == "3":
            read_sms()
        elif c == "4":
            notifications()
        elif c == "5":
            secs = input("Seconds to log [60]: ").strip()
            log_notifications(int(secs) if secs.isdigit() else 60)
        elif c == "6":
            list_files(input("Path [/sdcard/]: ").strip() or "/sdcard/")
        elif c == "7":
            pull_file(input("Remote path on phone: ").strip())
        elif c == "8":
            backup_photos()
        elif c == "9":
            phone_info()
        elif c == "w":
            go_wireless()
        elif c == "q":
            break
