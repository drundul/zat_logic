import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai
import json

# Заглушка для Render (порт 10000)
def fake_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running.')
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

threading.Thread(target=fake_server).start()

# OpenAI ключ из переменной окружения
openai.api_key = os.getenv("OPENAI_API_KEY")

# Telegram токен из переменной окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Загрузка архива сообщений канала
try:
    with open("channel_archive.json", "r", encoding="utf-8") as f:
        archive_data = json.load(f)
except:
    archive_data = []

# Память
chat_histories = {}
user_questions = {}
unique_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ Привет, я Татьянин помощник. Готова поддержать тебя, дать практику или вдохновение. Спроси меня о чём-то важном 💫")

def get_matched_archive_response(user_message):
    if not archive_data:
        return ""
    for item in archive_data:
        text = item.get("text", "").lower()
        if any(word in user_message.lower() for word in ["страх", "тревога", "деньги", "желание", "контроль"]):
            if text and len(text) > 50:
                return text
    return ""

async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    unique_users.add(user_id)
    user_questions.setdefault(user_id, []).append(user_text)

    # Обработка памяти сообщений
    history = chat_histories.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    if len(history) > 5:
        history = history[-5:]
    chat_histories[user_id] = history

    # System prompt в стиле Татьяны
    system_prompt = (
        "Ты — проводник Татьяна, мягкая, теплая, глубоко принимающая. "
        "Ты отвечаешь женщине 35–54 лет, которая тревожится, ищет путь к себе, хочет внутреннего покоя и достатка. "
        "Говори образно, с теплом, как душевная подруга, предлагай практики, задавай уточняющие вопросы, веди от боли к доверию."
    )

    messages = [{"role": "system", "content": system_prompt}] + history

    # Получение ответа от OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages
        )
        reply_text = response.choices[0].message["content"]
    except Exception as e:
        reply_text = "⚠️ Возникла ошибка при обращении к OpenAI: " + str(e)

    # Добавление ответа в историю
    history.append({"role": "assistant", "content": reply_text})
    chat_histories[user_id] = history

    # Ответ из архива
    matched = get_matched_archive_response(user_text)
    if matched:
        reply_text += f"\n\n💬 Это из канала Татьяны:\n\n{matched}"

    await update.message.reply_text(reply_text)

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))

if __name__ == "__main__":
    application.run_polling()
