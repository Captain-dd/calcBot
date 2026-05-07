import telebot
import random
import os
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN LOADED:", TOKEN is not None)

bot = telebot.TeleBot(TOKEN, threaded=False)

# ===== User State =====
user_state = {}
# {
#   chat_id: {"num": 7, "type": "square"}
# }

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

    else:  # table
        num = random.randint(7, 30)
        i = random.randint(1, 10)
        question = f"{num} x {i} = ?"
        answer = num * i

    return num, qtype, question, answer


# ===== Start =====
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    num, qtype, question, answer = generate_question()

    user_state[chat_id] = {
        "answer": answer
    }

    bot.send_message(chat_id, f"Solve:\n{question}")

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id

    if chat_id in user_state:
        del user_state[chat_id]

    bot.send_message(chat_id, "Stopped ✅")


# ===== Handle Answer =====
@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_state:
        bot.send_message(chat_id, "Type /start first")
        return

    if not text.isdigit():
        bot.send_message(chat_id, "Send a number")
        return

    user_answer = int(text)
    correct_answer = user_state[chat_id]["answer"]

    # ===== Check =====
    if user_answer == correct_answer:
        bot.send_message(chat_id, "Correct ✅")
    else:
        bot.send_message(chat_id, f"Wrong ❌ Correct = {correct_answer}")

    # ===== Next Question =====
    num, qtype, question, answer = generate_question()

    user_state[chat_id] = {
        "answer": answer
    }

    bot.send_message(chat_id, f"Next:\n{question}")

app = Flask(__name__)

@app.route("/begin", methods=["GET"])
def webhook():
    try:
        print("Running...")
        bot.infinity_polling()
    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5007))
    app.run(host="0.0.0.0", port=port)
