import logging
import os
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ─── Настройки ────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN = os.environ[“TELEGRAM_TOKEN”]
GROQ_API_KEY = os.environ[“GROQ_API_KEY”]

# Системный промпт — можно настроить под себя

SYSTEM_PROMPT = “Ты полезный ассистент. Отвечай кратко и по делу на русском языке.”

# История сообщений на пользователя (chat_id + user_id -> список сообщений)

MAX_HISTORY = 10
conversation_history: dict[str, list] = {}

# ─── Клиент Groq ──────────────────────────────────────────────────────────────

client = AsyncOpenAI(
api_key=GROQ_API_KEY,
base_url=“https://api.groq.com/openai/v1”
)

logging.basicConfig(
format=”%(asctime)s | %(levelname)s | %(message)s”,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# ─── Обработчик сообщений ─────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
message = update.message
if not message or not message.text:
return

```
user = message.from_user
chat_id = message.chat_id
user_id = user.id
text = message.text.strip()

# Игнорируем команды (/start и т.п.)
if text.startswith("/"):
    return

logger.info(f"[{chat_id}] {user.first_name} ({user_id}): {text}")

# История диалога — ключ: chat_id + user_id
history_key = f"{chat_id}:{user_id}"
if history_key not in conversation_history:
    conversation_history[history_key] = []

history = conversation_history[history_key]
history.append({"role": "user", "content": text})

# Обрезаем историю до MAX_HISTORY сообщений
if len(history) > MAX_HISTORY:
    history = history[-MAX_HISTORY:]
    conversation_history[history_key] = history

# Отправляем "печатает..."
await context.bot.send_chat_action(chat_id=chat_id, action="typing")

try:
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
        max_tokens=1000,
    )
    reply = response.choices[0].message.content.strip()

    # Добавляем ответ в историю
    history.append({"role": "assistant", "content": reply})

    # Отвечаем реплаем на сообщение пользователя
    await message.reply_text(reply)
    logger.info(f"[{chat_id}] Bot -> {user.first_name}: {reply[:80]}...")

except Exception as e:
    logger.error(f"Groq error: {e}")
    await message.reply_text("⚠️ Произошла ошибка при обращении к ИИ. Попробуй позже.")
```

# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
logger.info(“Бот запущен. Нажми Ctrl+C для остановки.”)
app.run_polling(allowed_updates=Update.ALL_TYPES)

if **name** == “**main**”:
main()
