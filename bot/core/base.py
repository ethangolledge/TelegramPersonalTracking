import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.app = Application.builder().token(os.getenv("TOKEN")).build()
        self._add_handlers()

    def _add_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello! I'm your bot. Use /help to see commands.")

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Available commands:\n/start - Welcome message\n/help - Show this help")

    def run(self):
        self.app.run_polling()

if __name__ == "__main__":
    print(os.getenv("TOKEN"))
    bot = TelegramBot()
    bot.run()