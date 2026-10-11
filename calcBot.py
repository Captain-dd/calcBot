import telebot
import random
import os
import threading
import time
import requests
from flask import Flask, request, abort
from fpdf import FPDF
from datetime import datetime
from config import *
from logger import setup_logging, get_logger
setup_logging()          # ← call ONCE at entry point
log = get_logger(__name__)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ===== User State (in-memory) =====
user_state = {}
log.info("User state initialized (in-memory)")

LABELS = {
    TABLE:  "Tables",
    SQUARE: "Squares",
    CUBE:   "Cubes",
    SINGLE_DIGIT_ADDITION: "Single-Digit Addition",
    SINGLE_DIGIT_SUBTRACTION: "Single-Digit Subtraction",
    TWO_DIGIT_ADDITION: "Two-Digit Addition",
    TWO_DIGIT_SUBTRACTION: "Two-Digit Subtraction",
    THREE_DIGIT_ADDITION: "Three-Digit Addition",
    THREE_DIGIT_SUBTRACTION: "Three-Digit Subtraction",
    ADDITION_SUBTRACTION_MIX: "Addition/Subtraction Mix",
    # MULTIPLICATION_WITH_TWO_HALF_ONE_HALF_AND_EIGHT: "Multiplication with 2, 0.5, 1.5, & 8",
    # MULTIPLICATION_WITH_TWO_DIGIT_INTO_ONE_DIGIT: "Multiplication with two digit into one digit",
    # MULTIPLICATION_WITH_TWO_DIGIT_INTO_TWO_DIGIT: "Multiplication with two digit into two digit",
    # MULTIPLICATION_WITH_FIVE_TWENTY_FIVE_AND_ONE_TWENTY_FIVE: "Multiplication with 5, 25, & 125",
    # MULTIPLICATION_OF_TWO_DIGIT_NUMBERS_WITH_DIFFERENCE_TWO: "Multiplication of two digit numbers with difference 2",
    # MULTIPLICATION_OF_TWO_DIGIT_NUMBERS_WITH_EVEN_DIFFERENCE: "Multiplication of two digit numbers with even difference",
    # MULTIPLICATION_OF_CONSECUTIVE_NUMBERS: "Multiplication of consecutive numbers",
    # MULTIPLICATION_WITH_11: "Multiplication with 11",
    WANT_PDF: "Practice Question in pdf"
}

def build_type_keyboard(enabled):
    
    keyboard = telebot.types.InlineKeyboardMarkup()
    for key, label in LABELS.items():
        check = "✅" if key in enabled else "☐"
        btn = telebot.types.InlineKeyboardButton(
            f"{check} {label}",
            callback_data=f"toggle_{key}"
        )
        keyboard.row(btn)  # ← one per row, no buttons list needed

    confirm = telebot.types.InlineKeyboardButton("Confirm ✅", callback_data="confirm_types")
    keyboard.row(confirm)
    return keyboard



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
def generate_question(enabled):
    qtype = random.choice(enabled)

    if qtype == SQUARE:
        num = random.randint(SQUARE_MIN, SQUARE_MAX)
        question = f"{num}² = ?"
        answer = num * num

    elif qtype == CUBE:
        num = random.randint(CUBE_MIN, CUBE_MAX)
        question = f"{num}³ = ?"
        answer = num * num * num

    elif qtype == TABLE:
        num = random.randint(TABLE_MIN, TABLE_MAX)
        i = random.randint(2, 10)
        question = f"{num} x {i} = ?"
        answer = num * i
    
    elif qtype == SINGLE_DIGIT_ADDITION:
        a = random.randint(0, 9)
        b = random.randint(0, 9)
        question = f"{a} + {b} = ?"
        answer = a + b

    elif qtype == SINGLE_DIGIT_SUBTRACTION:
        a = random.randint(0, 9)
        b = random.randint(0, a)  # ensure non-negative result
        question = f"{a} - {b} = ?"
        answer = a - b

    elif qtype == TWO_DIGIT_ADDITION:
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        question = f"{a} + {b} = ?"
        answer = a + b

    elif qtype == TWO_DIGIT_SUBTRACTION:
        a = random.randint(10, 99)
        b = random.randint(10, a)  # ensure non-negative result
        question = f"{a} - {b} = ?"
        answer = a - b

    elif qtype == THREE_DIGIT_ADDITION:
        a = random.randint(100, 999)
        b = random.randint(100, 999)
        question = f"{a} + {b} = ?"
        answer = a + b
    
    elif qtype == THREE_DIGIT_SUBTRACTION:
        a = random.randint(100, 999)
        b = random.randint(100, a)  # ensure non-negative result
        question = f"{a} - {b} = ?"
        answer = a - b

    elif qtype == ADDITION_SUBTRACTION_MIX:
        a = random.randint(0, 999)
        b = random.randint(0, 999)
        op = random.choice(["+", "-"])
        if op == "+":
            question = f"{a} + {b} = ?"
            answer = a + b
        else:
            # ensure non-negative result for subtraction
            a, b = max(a, b), min(a, b)
            question = f"{a} - {b} = ?"
            answer = a - b

    log.debug(f"Generated question → type={qtype} question='{question}' answer={answer}")
    return question, answer

def create_pdf(chat_id, types):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Practice Questions", new_x="LMARGIN", new_y="NEXT")

    all_answers = []   # saved for the answer key

    for qtype in types:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, LABELS[qtype], new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 12)

        answers = []
        for i in range(1, 11):                      # 10 questions per type
            question, answer = generate_question([qtype])
            pdf.cell(0, 7, f"{i}.  {question}", new_x="LMARGIN", new_y="NEXT")
            answers.append(answer)
        all_answers.append((LABELS[qtype], answers))

    # Answer key on a new page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Answer Key", new_x="LMARGIN", new_y="NEXT")
    for label, answers in all_answers:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 12)
        for i, ans in enumerate(answers, start=1):
            pdf.cell(0, 7, f"{i}.  {ans}", new_x="LMARGIN", new_y="NEXT")

    filename = f"practice_{chat_id}.pdf"
    pdf.output(filename)
    return filename

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

    user_state[chat_id] = {
        "mode": "setup",
        "enabled": [],        # nothing selected yet
        "answer": None
    }

    keyboard = build_type_keyboard(enabled=[])
    bot.send_message(chat_id, "What do you want to practice?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id

    # Safety: if state missing, ask to /start again
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "Please type /start first.")
        return

    # if user is selecting types of question to practice
    if call.data.startswith("toggle_"):
        qtype = call.data.replace("toggle_", "")           # "table" / "square" / "cube"
        enabled = user_state[chat_id].get("enabled", [])

        if qtype in enabled:
            enabled.remove(qtype)
        else:
            enabled.append(qtype)

        user_state[chat_id]["enabled"] = enabled

        # Edit the same message with updated checkmarks
        keyboard = build_type_keyboard(enabled)
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.id,
            reply_markup=keyboard
        )
        bot.answer_callback_query(call.id)   # clears the loading spinner
        log.info(f"Toggle → chat_id={chat_id} type={qtype} enabled={enabled}")

    # user clicked confirm after selecting types
    elif call.data == "confirm_types":
        log.info(f"Confirm button clicked by → chat_id={chat_id}")
        enabled = user_state[chat_id].get("enabled", [])

        # Separate the PDF option from the real question types
        want_pdf = WANT_PDF in enabled
        practice_types = [t for t in enabled if t != WANT_PDF]

        # Nothing real selected → toast and stop
        if not practice_types:
            bot.answer_callback_query(call.id, "⚠️ Select at least one question type!", show_alert=False)
            return

        bot.answer_callback_query(call.id)

        summary = ", ".join(LABELS[t] for t in enabled)
        bot.edit_message_text(
            f"Selected: {summary} ✅",
            chat_id=chat_id,
            message_id=call.message.id
        )

        # ---- PDF part ----
        if want_pdf:
            try:
                send_message(chat_id, "Creating your PDF, please wait... ⏳")
                filename = create_pdf(chat_id, practice_types)
                with open(filename, "rb") as f:
                    bot.send_document(chat_id, f, caption="Here are your practice questions 📄")
                os.remove(filename)
                log.info(f"PDF sent → chat_id={chat_id} types={practice_types}")
            except Exception as e:
                log.error(f"PDF failed → chat_id={chat_id} error={e}", exc_info=True)
                send_message(chat_id, "Sorry, could not create the PDF ❌")

        # ---- Normal practice: only the real types, never WANT_PDF ----
        user_state[chat_id]["enabled"] = practice_types
        user_state[chat_id]["mode"] = "playing"
        question, answer = generate_question(practice_types)
        user_state[chat_id]["answer"] = answer
        send_message(chat_id, f"Let's go! Solve:\n\n{question}")
        log.info(f"Setup done → chat_id={chat_id} enabled={practice_types}")


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
        send_message(chat_id, "Type /start first.")
        return

    # Block text input during setup — user should use buttons
    if user_state[chat_id].get("mode") == "setup":
        send_message(chat_id, "Please select your practice types using the buttons above.")
        return

    if not text.lstrip('-').isdigit():
        send_message(chat_id, "Please send a valid number.")
        return

    user_answer = int(text)
    correct_answer = user_state[chat_id]["answer"]

    if user_answer == correct_answer:
        log.info(f"Correct → chat_id={chat_id} ✅")
        send_message(chat_id, "Correct ✅")
    else:
        log.info(f"Wrong → chat_id={chat_id} answered {user_answer}, correct={correct_answer} ❌")
        send_message(chat_id, f"Wrong ❌  Correct answer = {correct_answer}")

    enabled = user_state[chat_id]["enabled"]
    question, answer = generate_question(enabled)
    user_state[chat_id]["answer"] = answer
    send_message(chat_id, f"Next:\n\n{question}")

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