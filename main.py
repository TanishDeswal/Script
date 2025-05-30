# === Auto-Updater ===
import requests
import os
import sys
import time

GITHUB_USER = "TanishDeswal"
GITHUB_REPO = "Script"
BRANCH = "main"
SCRIPT_NAME = "CodeTantra_Chrome.py"
VERSION_FILE = "version.txt"

RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
REMOTE_SCRIPT_URL = f"{RAW_BASE_URL}/{SCRIPT_NAME}"
REMOTE_VERSION_URL = f"{RAW_BASE_URL}/{VERSION_FILE}"

LOCAL_SCRIPT_PATH = os.path.abspath(__file__)
LOCAL_VERSION_PATH = os.path.join(os.path.dirname(LOCAL_SCRIPT_PATH), VERSION_FILE)

def get_remote_text(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None

def get_local_version():
    if os.path.exists(LOCAL_VERSION_PATH):
        with open(LOCAL_VERSION_PATH, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def save_local_version(version):
    with open(LOCAL_VERSION_PATH, 'w') as f:
        f.write(version)

def update_script(remote_code, remote_version):
    print("[INFO] Updating script...")
    with open(LOCAL_SCRIPT_PATH, 'w', encoding='utf-8') as f:
        f.write(remote_code)
    save_local_version(remote_version)
    print("[INFO] Script updated to version", remote_version)
    relaunch_script()

def relaunch_script():
    print("[INFO] Relaunching script...")
    time.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)

def check_for_updates():
    print("[INFO] Checking for updates...")
    local_version = get_local_version()
    remote_version = get_remote_text(REMOTE_VERSION_URL)
    if not remote_version:
        print("[WARN] Could not check version.")
        return
    if remote_version > local_version:
        print(f"[INFO] New version found: {remote_version} (local: {local_version})")
        remote_code = get_remote_text(REMOTE_SCRIPT_URL)
        if remote_code:
            update_script(remote_code, remote_version)
    else:
        print("[INFO] No update needed. Current version:", local_version)

check_for_updates()

# === Telegram Bot Logic ===
import telebot
import pyautogui
import pytesseract
import ctypes
import threading
import keyboard
from PIL import Image
import logging
import traceback

# === Setup logging ===
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    app_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = base_dir

log_file = os.path.join(app_dir, 'error.log')
logging.basicConfig(
    filename=log_file,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

def log_exception(e):
    logging.error(f"Exception: {e}")
    logging.error(traceback.format_exc())

# === Load username ===
try:
    username_file = os.path.join(app_dir, 'username.txt')
    with open(username_file, 'r', encoding='utf-8') as f:
        telegram_username = f.read().strip().lstrip('@')
        if not telegram_username:
            raise ValueError("username.txt is empty.")
except Exception as e:
    log_exception(e)
    print(f"❌ {e}")
    sys.exit(1)

# === Hide Console ===
try:
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except Exception as e:
    log_exception(e)

# === Set Tesseract Path ===
try:
    tesseract_path = os.path.join(base_dir, 'Tesseract-OCR', 'tesseract.exe')
    if not os.path.exists(tesseract_path):
        raise FileNotFoundError(f"Tesseract not found at {tesseract_path}")
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
except Exception as e:
    log_exception(e)
    sys.exit(1)

# === Telegram Bot Setup ===
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)
user_id = None

# === Exit Shortcut ===
def quit_script():
    os._exit(0)

def start_hotkey_listener():
    try:
        keyboard.add_hotkey("alt+shift+q", quit_script)
        keyboard.wait()
    except Exception as e:
        log_exception(e)

threading.Thread(target=start_hotkey_listener, daemon=True).start()

# === Telegram Handlers ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    global user_id
    try:
        incoming_username = message.from_user.username
        if incoming_username == telegram_username:
            user_id = message.chat.id
            bot.send_message(user_id, f"✅ Hello @{telegram_username}, you are authorized.")
        else:
            bot.send_message(message.chat.id, "❌ You are not authorized.")
    except Exception as e:
        log_exception(e)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    global user_id
    try:
        if message.from_user.username != telegram_username:
            bot.send_message(message.chat.id, "❌ Unauthorized user.")
            return
        if user_id is None:
            bot.send_message(message.chat.id, "⚠️ Send /start first.")
            return
        if message.text.strip() == "1":
            screenshot = pyautogui.screenshot()
            filepath = os.path.join(app_dir, "screenshot.png")
            screenshot.save(filepath)
            with open(filepath, "rb") as photo:
                bot.send_photo(user_id, photo)
            extracted_text = pytesseract.image_to_string(Image.open(filepath))
            bot.send_message(user_id, f"📝 Extracted Text:\n{extracted_text}" if extracted_text.strip() else "ℹ️ No readable text found.")
            os.remove(filepath)
        else:
            bot.send_message(user_id, "❓ Send '1' to get a screenshot with OCR text.")
    except Exception as e:
        log_exception(e)

print("🚀 Bot running... Alt + Shift + Q to quit.")
try:
    bot.infinity_polling()
except Exception as e:
    log_exception(e)
