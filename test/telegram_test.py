import telebot

# ==== CONFIG ====
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"   # Replace with your chat ID


def main():
    bot = telebot.TeleBot(BOT_TOKEN)
    test_msg = "✅ Hello from MT5 Bot 🚀\nYour Telegram bot is working!"
    try:
        bot.send_message(CHAT_ID, test_msg)
        print("✅ Test message sent successfully.")
    except Exception as e:
        print("❌ Failed to send Telegram message:", e)


if __name__ == "__main__":
    main()
