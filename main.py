import os
import openai
import telebot
from dotenv import load_dotenv

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
openai.api_key = os.getenv("OPENAI_API_KEY")

ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Храним сессии с пользователями
user_threads = {}

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.chat.id)

    # Создаем новую ветку для каждого пользователя, если нет
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id

    # Отправляем сообщение в ветку
    openai.beta.threads.messages.create(
        thread_id=user_threads[user_id],
        role="user",
        content=message.text,
    )

    # Запускаем ассистента
    run = openai.beta.threads.runs.create(
        thread_id=user_threads[user_id],
        assistant_id=ASSISTANT_ID,
    )

    # Ждем завершения
    while True:
        status = openai.beta.threads.runs.retrieve(thread_id=user_threads[user_id], run_id=run.id)
        if status.status == "completed":
            break

    # Получаем ответ
    messages = openai.beta.threads.messages.list(thread_id=user_threads[user_id])
    reply = messages.data[0].content[0].text.value

    # Отправляем ответ в Telegram
    bot.send_message(chat_id=message.chat.id, text=reply)

if __name__ == "__main__":
    bot.polling()
