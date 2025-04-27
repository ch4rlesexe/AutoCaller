import os
import sys
import time
import threading
import subprocess
import random
import numpy as np
import sounddevice as sd
import pytz

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pydub import AudioSegment
from pydub.playback import play

# --- SETTINGS ---
PHONE_NUMBER       = "0000000000"       # Your Phone Number in the format of 0000000000
AUDIO_DIR          = "audio"            # folder containing audio files
CALL_TIME          = "01:25"            # HH:MM
TIMEZONE           = "US/Eastern"

CHROME_DRIVER_PATH = "chromedriver.exe"
CHROME_USER_DATA   = r"C:\Users\USER\AppData\Local\Google\Chrome\User Data" # Your google chrome file path
CHROME_PROFILE     = "Default"

MAX_RING_SECONDS   = 15                 # seconds to wait for answer before redial
REDIAL_DELAY       = 10                 # seconds between calls until keypress

# --- DTMF DETECTION SETUP ---
TARGET_FREQ       = 770.0               # row tone for '5'
SAMPLE_RATE       = 8000
BLOCK_DURATION    = 0.1                 # seconds
POWER_THRESHOLD   = 1000                # detect when Goertzel power > this

stop_testing = threading.Event()

def find_cable_device():
    for idx, d in enumerate(sd.query_devices()):
        if 'cable' in d['name'].lower():
            return idx
    return None

CABLE_DEVICE = find_cable_device()
if CABLE_DEVICE is not None:
    print(f"[INFO] Using input device #{CABLE_DEVICE} for DTMF.")
else:
    print("[WARN] 'cable' device not found; using default input.")

def goertzel(samples, freq, fs):
    N = len(samples)
    k = int(0.5 + (N * freq) / fs)
    w = 2 * np.pi * k / N
    coeff = 2 * np.cos(w)
    s_prev = s_prev2 = 0.0
    for x in samples:
        s = x + coeff * s_prev - s_prev2
        s_prev2, s_prev = s_prev, s
    return s_prev2*s_prev2 + s_prev*s_prev - coeff*s_prev*s_prev2

def dtmf_listener():
    def callback(indata, frames, time_info, status):
        power = goertzel(indata[:,0], TARGET_FREQ, SAMPLE_RATE)
        print(f"[DTMF] 770 Hz power: {power:.0f}", end="\r")
        if power > POWER_THRESHOLD:
            print("\n[DTMF] Detected keypress (770 Hz)!")
            stop_testing.set()
            raise sd.CallbackStop()

    try:
        with sd.InputStream(device=CABLE_DEVICE,
                            channels=1,
                            samplerate=SAMPLE_RATE,
                            blocksize=int(SAMPLE_RATE * BLOCK_DURATION),
                            callback=callback):
            while not stop_testing.is_set():
                time.sleep(0.1)
    except sd.CallbackStop:
        pass
    except Exception as e:
        print(f"[DTMF] Listener error: {e}")

# start listener thread
threading.Thread(target=dtmf_listener, daemon=True).start()

# select audio file
if not os.path.isdir(AUDIO_DIR):
    print(f"[ERROR] Audio directory '{AUDIO_DIR}' not found."); sys.exit(1)

candidates = [
    f for f in os.listdir(AUDIO_DIR)
    if os.path.isfile(os.path.join(AUDIO_DIR, f))
    and f.lower().endswith((".mp3", ".wav", ".ogg", ".flac"))
]
if not candidates:
    print(f"[ERROR] No audio files in '{AUDIO_DIR}'."); sys.exit(1)

AUDIO_FILE = os.path.join(AUDIO_DIR, random.choice(candidates))
print(f"[INFO] Selected audio file: {AUDIO_FILE}")

def check_files():
    if not os.path.exists(CHROME_DRIVER_PATH):
        print(f"[ERROR] {CHROME_DRIVER_PATH} not found."); sys.exit(1)
    if not os.path.exists(AUDIO_FILE):
        print(f"[ERROR] {AUDIO_FILE} not found."); sys.exit(1)

def wait_until(target_time_str):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    t = datetime.strptime(target_time_str, "%H:%M").time()
    run_at = tz.localize(datetime.combine(now.date(), t))
    if now >= run_at:
        run_at += timedelta(days=1)
    print(f"[INFO] Waiting until {run_at}…")
    while datetime.now(tz) < run_at:
        time.sleep(30)
    print("[INFO] Target time reached.")

def setup_browser():
    opts = Options()
    opts.add_argument(f"--user-data-dir={CHROME_USER_DATA}")
    opts.add_argument(f"--profile-directory={CHROME_PROFILE}")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=opts)

def place_call(driver):
    driver.get("https://voice.google.com/u/0/calls")
    wait = WebDriverWait(driver, 20)
    inp = wait.until(EC.visibility_of_element_located((By.ID, "il1")))
    inp.clear()
    inp.send_keys(PHONE_NUMBER)
    time.sleep(1)
    inp.send_keys(Keys.ENTER)

def play_audio():
    try:
        song = AudioSegment.from_file(AUDIO_FILE)
        play(song)
    except:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", AUDIO_FILE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

def hang_up(driver):
    sels = [
        "span.mat-ripple.mat-mdc-button-ripple",
        "span.mat-focus-indicator",
        "span.mat-mdc-button-touch-target",
    ]
    for sel in sels:
        for e in driver.find_elements(By.CSS_SELECTOR, sel):
            if e.is_displayed():
                try:
                    e.click()
                    return
                except:
                    driver.execute_script("arguments[0].click();", e)
                    return

def handle_call():
    driver = setup_browser()
    place_call(driver)
    start = time.time()
    while True:
        if driver.find_elements(By.CSS_SELECTOR, 'span[gv-test-id="in-call-callduration"]'):
            play_audio()
            break
        if driver.find_elements(By.XPATH, '//span[text()="Calling…" and @aria-hidden="false"]') \
           and time.time() - start > MAX_RING_SECONDS:
            break
        time.sleep(0.5)
    hang_up(driver)
    driver.quit()

def main():
    check_files()
    while True:
        wait_until(CALL_TIME)
        stop_testing.clear()
        threading.Thread(target=dtmf_listener, daemon=True).start()
        while not stop_testing.is_set():
            handle_call()
            time.sleep(REDIAL_DELAY)
        print("[INFO] Keypress detected – next call scheduled for tomorrow.")

if __name__ == "__main__":
    main()
