import logging
import os
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ─── Настройки ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = "ВАШ_TELEGRAM_TOKEN"
DEEPSEEK_API_KEY = "ВАШ_DEEPSEEK_API_KEY"

# Системный промпт — можно настроить под себя
SYSTEM_PROMPT = "Ты полезный ассистент. Отвечай кратко и по делу на русском языке."

# История сообщений на пользователя (chat_id + user_id -> список сообщений)
# Хранит последние N сообщений для контекста
MAX_HISTORY = 10
conversation_history: dict[str, list] = {}

# ─── Клиент DeepSeek ──────────────────────────────────────────────────────────
deepseek = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── Обработчик сообщений ─────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    chat_id = message.chat_id
    user_id = user.id
    text = message.text.strip()

    # Игнорируем команды (/start и т.п.)
    if text.startswith("/"):
        return

    # В группах отвечаем только если бот упомянут (@username) или это ответ боту,
    # либо раскомментируй строку ниже чтобы отвечать на ВСЕ сообщения
    bot_username = context.bot.username
    is_reply_to_bot = (
        message.reply_to_message and
        message.reply_to_message.from_user and
        message.reply_to_message.from_user.username == bot_username
    )
    is_mentioned = bot_username and f"@{bot_username}" in text

    if message.chat.type in ("group", "supergroup"):
        if not is_reply_to_bot and not is_mentioned:
            return  # ← закомментируй эту строку чтобы отвечать на все сообщения в группе

    # Убираем упоминание бота из текста
    if bot_username:
        text = text.replace(f"@{bot_username}", "").strip()

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
        response = await deepseek.chat.completions.create(
            model="deepseek-chat",
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
        logger.error(f"DeepSeek error: {e}")
        await message.reply_text("⚠️ Произошла ошибка при обращении к ИИ. Попробуй позже.")


# ─── Запуск ───────────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
