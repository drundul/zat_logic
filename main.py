
import os
import threading
import logging
import json
import openai
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

# Заглушка для Render
def fake_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running.')
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()
threading.Thread(target=fake_server).start()

logging.basicConfig(level=logging.INFO)

# SQLite-база
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS questions (user_id INTEGER, question TEXT)")
conn.commit()

# Загрузка архива канала
channel_messages = []
if os.path.exists("channel_archive.json"):
    with open("channel_archive.json", "r", encoding="utf-8") as f:
        channel_messages = json.load(f)

# Память сообщений
user_histories = {}
user_states = {}

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    await update.message.reply_text(
        "✨ Привет, я Татьянин помощник. Хочешь вдохновение, медитацию или поговорим о чём-то важном?",
        reply_markup=ReplyKeyboardMarkup([['Медитация'], ['Хочу поделиться'], ['Просто побудь рядом']], resize_keyboard=True)
    )

# Диалоговая логика
async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.lower()
    c.execute("INSERT INTO questions (user_id, question) VALUES (?, ?)", (user_id, user_message))
    conn.commit()

    # Обновляем память
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": user_message})
    if len(history) > 5:
        history = history[-5:]
    user_histories[user_id] = history

    # Обработка триггеров
    if "тревога" in user_message or "боюсь" in user_message:
        user_states[user_id] = "anxiety"
        await update.message.reply_text(
            "Я рядом. Эта тревога больше про финансы, отношения или внутренний контроль?"
        )
        return
    elif user_states.get(user_id) == "anxiety":
        user_states[user_id] = "offer_practice"
        await update.message.reply_text("Давай сделаем мягкое дыхание. Хочешь?")
        return
    elif user_states.get(user_id) == "offer_practice" and "да" in user_message:
        await update.message.reply_text("🌬 Закрой глаза и просто подыши. Глубокий вдох… и мягкий выдох… Я здесь.")
        user_states[user_id] = "invite"
        return
    elif user_states.get(user_id) == "invite":
        await update.message.reply_text("Хочешь больше таких практик? Приглашаю в клуб, где мы вместе дышим, чувствуем и растём 🌿")
        user_states[user_id] = None
        return

    # Проверка архива канала
    matched = next((m["text"] for m in channel_messages if isinstance(m, dict) and "text" in m and m["text"] and m["text"] in user_message), None)

    if matched:
        reply_text = f"💬 Это из канала Татьяны:\n\n{matched}"

{matched}"
    else:
        messages = [{
            "role": "system",
            "content": (
                "Ты — тёплый и глубоко чувствующий помощник в стиле Татьяны Зарецкой. Ты слышишь, чувствуешь, направляешь. "
                "Твоя задача — помочь человеку вернуться в состояние опоры, ресурса, мягкости и понимания. Говоришь метафорами, мягко, с любовью."
            )
        }] + history
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                temperature=0.9,
                presence_penalty=0.5,
                frequency_penalty=0.4,
                messages=messages
            )
            reply_text = response.choices[0].message["content"]
        except Exception as e:
            reply_text = f"Произошла ошибка: {e}"

    user_histories[user_id].append({"role": "assistant", "content": reply_text})
    await update.message.reply_text(reply_text)

# Запуск
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    app.run_polling()

if __name__ == "__main__":
    main()
