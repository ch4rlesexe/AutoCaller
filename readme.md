```markdown
# AutoCaller for Google Voice

AutoCaller is a Python-based automation tool that repeatedly calls a phone number via Google Voice, plays an audio file once the call is answered, and redials until a specific DTMF keypress (5) is detected.

## Features
- Calls a designated phone number via Google Voice.
- Plays a random audio file from a local folder.
- Detects DTMF keypress (5) during call playback to stop redialing.
- Automatically retries calling if unanswered.
- Scheduled daily calling at a specific time.

## Setup Guide

### Prerequisites
- **Python 3.11+**
- Google Chrome installed
- [ChromeDriver](https://sites.google.com/chromium.org/driver/) matching your Chrome version
- Google Voice account signed into Chrome
- Optional: [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (for DTMF detection)

### Installation

1. Clone or download this repository.

2. Install required Python packages:

```bash
pip install selenium pydub sounddevice numpy pytz
```

3. Download and place `chromedriver.exe` into the project folder.

4. Setup a Chrome profile already signed into your Google Voice account. Update these fields inside `main.py`:
   ```python
   CHROME_USER_DATA = r"C:\Path\To\Your\Chrome\User Data"
   CHROME_PROFILE = "ProfileName"
   ```

5. Place one or more audio files (`.mp3`, `.wav`, `.ogg`, `.flac`) inside an `audio/` folder.

6. (Optional but recommended) Install VB-Audio Virtual Cable to allow internal audio loopback for DTMF detection. Your windows speaker output should be VB-Audio Virtual cable, and the Input should be CABLE output (VB-Audio Virtual cable) 

### Running

```bash
python main.py
```

The script will:
- Wait until the scheduled time.
- Start calling and retrying every few seconds.
- Play the audio once answered.
- Stop calling after receiving DTMF keypress 5.

## Technologies Used

### Python Libraries
- **Selenium** – Automates Google Voice interactions using Chrome.
- **pydub** – Plays the selected audio files during calls.
- **sounddevice** – Captures audio input to detect DTMF keypresses.
- **numpy** – Processes and analyzes raw audio samples.
- **pytz** – Handles timezones for scheduled calls.

### Audio Detection
- **DTMF Detection** is implemented using the Goertzel algorithm.
- It specifically listens for:
  - **770 Hz** and **1336 Hz** frequencies simultaneously, which correspond to the DTMF '5' key.
- If both frequencies are strongly detected together (power exceeds a threshold), the script stops redialing.

### Selenium Elements Targeted
- **Phone number input field:**  
  ```html
  <input id="il1" type="text" placeholder="Enter a name or number">
  ```
- **Hang up buttons (multiple fallbacks):**  
  ```html
  <span class="mat-ripple mat-mdc-button-ripple"></span>
  <span class="mat-focus-indicator"></span>
  <span class="mat-mdc-button-touch-target"></span>
  ```
- **In-call timer:**  
  Used to detect whether the call has been answered:
  ```html
  <span gv-test-id="in-call-callduration">00:07</span>
  ```
- **"Calling..." label:**  
  Used to detect if the call is still ringing and timeout after 15 seconds if unanswered.

## Notes
- Ensure your Google Chrome version matches your ChromeDriver version exactly.
- Audio detection relies on system volume, microphone settings, and VB-Cable if used. Tune thresholds if needed inside `main.py`.
