import telebot
import random
import os
import threading
import time
import requests
import logging
from flask import Flask, request, abort
from datetime import datetime

import sys

os.environ['PYTHONUNBUFFERED'] = '1'

# ===== Logging Setup =====
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# Force immediate flush
class FlushHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[FlushHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ===== Env Variables =====
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

log.info(f"BOT_TOKEN loaded: {TOKEN is not None}")
log.info(f"WEBHOOK_URL loaded: {WEBHOOK_URL is not None} → {WEBHOOK_URL}")
log.info(f"WEBHOOK_SECRET loaded: {WEBHOOK_SECRET is not None}")

if not TOKEN or not WEBHOOK_URL or not WEBHOOK_SECRET:
    log.critical("One or more required env variables are missing. Exiting.")
    exit(1)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ===== User State (in-memory) =====
user_state = {}
log.info("User state initialized (in-memory)")


# ===== Keep Alive =====
def keep_alive():
    log.info("Keep-alive thread running")
    while True:
        time.sleep(60)
        try:
            res = requests.get(f"{WEBHOOK_URL}/", timeout=10)
            log.info(f"Keep-alive ping → HTTP {res.status_code}")
        except requests.exceptions.ConnectionError:
            log.warning("Keep-alive ping failed → Connection error")
        except requests.exceptions.Timeout:
            log.warning("Keep-alive ping failed → Timeout")
        except Exception as e:
            log.error(f"Keep-alive ping failed → Unexpected error: {e}")


# ===== Generate Question =====
def generate_question():
    qtype = random.choice(["square", "cube", "table"])

    if qtype == "square":
        num = random.randint(11, 50)
        question = f"{num}² = ?"
        answer = num * num

    elif qtype == "cube":
        num = random.randint(2, 30)
        question = f"{num}³ = ?"
        answer = num * num * num

    else:
        num = random.randint(7, 30)
        i = random.randint(1, 10)
        question = f"{num} x {i} = ?"
        answer = num * i

    log.debug(f"Generated question → type={qtype} question='{question}' answer={answer}")
    return question, answer

def send_message(chat_id, text):
    try:
        bot.send_message(chat_id, text)
        log.info(f"Message sent → chat_id={chat_id} text='{text}'")
    except Exception as e:
        log.error(f"Failed to send message → chat_id={chat_id} error={e}", exc_info=True)


# ===== /start =====
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    username = message.from_user.username or "unknown"
    log.info(f"/start → chat_id={chat_id} username=@{username}")

    question, answer = generate_question()
    user_state[chat_id] = {"answer": answer}

    send_message(chat_id, f"Welcome! Solve:\n\n{question}")
    log.info(f"Question sent → chat_id={chat_id} question='{question}'")


# ===== /stop =====
@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    username = message.from_user.username or "unknown"
    log.info(f"/stop → chat_id={chat_id} username=@{username}")

    if chat_id in user_state:
        user_state.pop(chat_id)
        log.info(f"User state cleared → chat_id={chat_id}")
    else:
        log.info(f"No active session to clear → chat_id={chat_id}")

    send_message(chat_id, "Stopped ✅ Type /start to play again.")


# ===== Handle Answer =====
@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    username = message.from_user.username or "unknown"
    text = message.text.strip()

    log.info(f"Message received → chat_id={chat_id} username=@{username} text='{text}'")

    if chat_id not in user_state:
        log.warning(f"No active session → chat_id={chat_id} sent '{text}' without /start")
        send_message(chat_id, "Type /start first.")
        return

    if not text.lstrip('-').isdigit():
        log.warning(f"Invalid input → chat_id={chat_id} sent non-numeric: '{text}'")
        send_message(chat_id, "Please send a valid number.")
        return

    user_answer = int(text)
    correct_answer = user_state[chat_id]["answer"]

    if user_answer == correct_answer:
        log.info(f"Correct answer → chat_id={chat_id} answered {user_answer} ✅")
        send_message(chat_id, "Correct ✅")
    else:
        log.info(f"Wrong answer → chat_id={chat_id} answered {user_answer}, correct={correct_answer} ❌")
        send_message(chat_id, f"Wrong ❌  Correct answer = {correct_answer}")

    question, answer = generate_question()
    user_state[chat_id] = {"answer": answer}
    send_message(chat_id, f"Next:\n\n{question}")
    log.info(f"Next question sent → chat_id={chat_id} question='{question}'")


# ===== Webhook Route =====
@app.route("/webhook", methods=["POST"])
def webhook():
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if secret != WEBHOOK_SECRET:
        log.warning(f"Unauthorized webhook request → IP={request.remote_addr} secret_match=False")
        abort(403)

    if request.headers.get("content-type") != "application/json":
        log.warning(f"Webhook bad content-type → {request.headers.get('content-type')}")
        abort(403)

    try:
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        log.debug(f"Webhook update processed → update_id={update.update_id}")
        return "ok", 200
    except Exception as e:
        log.error(f"Failed to process webhook update → {e}", exc_info=True)
        return "error", 500


# ===== Set Webhook =====
@app.route("/set_webhook")
def set_webhook():
    log.info("Set webhook requested")
    try:
        bot.remove_webhook()
        log.info("Old webhook removed")

        result = bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET
        )

        if result:
            log.info(f"Webhook set successfully → {WEBHOOK_URL}/webhook")
            return "Webhook set successfully ✅", 200
        else:
            log.error("Webhook setup returned False")
            return "Webhook setup failed ❌", 500

    except Exception as e:
        log.error(f"Webhook setup crashed → {e}", exc_info=True)
        return f"Webhook setup crashed: {e}", 500


# ===== Health Check =====
@app.route("/")
def home():
    active_users = len(user_state)
    log.debug(f"Health check hit → active_sessions={active_users}")
    return f"Bot is running | Active sessions: {active_users}", 200


# ===== Startup =====
if __name__ == "__main__":
    log.info("Starting keep-alive thread...")
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()
    log.info("Keep-alive thread started ✅")

    port = int(os.environ.get("PORT", 5007))
    log.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)