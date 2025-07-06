# bot.py
import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, PicklePersistence,
    ContextTypes, filters
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(leveln# 1.  ⚙️ ame)s - %(message)s",
    level=logging.INFO,
)
LOG = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self) -> None:
        self.app = (
            Application.builder()
            .token(os.getenv("TOKEN"))
            .build()
        )
        self._register_handlers()
        self.QUESTIONS = [
            ("puffs",  "📊 How many puffs per day?"),
            ("method", "🎯 Reduce by 'number' or 'percent'?"),
            ("goal",   "💪 Weekly reduction goal?")
        ]

    @staticmethod
    def _uid(up: Update) -> int  | None:
        return up.effective_user.id if up.effective_user else None

    @staticmethod
    def _uname(up: Update) -> str | None:
        return up.effective_user.first_name if up.effective_user else None
    
    def _register_handlers(self) -> None:
        # Command handlers
        self.app.add_handlers([
            CommandHandler("start", self.start),
            CommandHandler("help", self.help),
            CommandHandler("setup", self.start_setup)
        ])
        # Message handlers
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_answer
        ))

    async def start(self, up: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await up.message.reply_text(
            f"Hello {self._uname(up)}! 👋\n\n"
            "I'm your personal vaping-reduction assistant.\n"
            "Send /help for all commands."
        )

    async def help(self, up: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await up.message.reply_text(
            "*Available commands:*\n"
            "• /start – welcome message\n"
            "• /setup – configure your reduction plan\n"
            "• /cancel – abort current setup\n"
            "• /help – this help",
            parse_mode="MarkdownV2",
        )
    async def start_setup(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Entry point: /setup"""
        ctx.user_data["step"] = 0  # Reset progress
        await self.ask_question(update, ctx)  # Send first question
    
    async def ask_question(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        step = ctx.user_data["step"]
        await update.message.reply_text(self.QUESTIONS[step][1])
    
    async def handle_answer(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        step = ctx.user_data.get("step")
        if step is None:
            return
        
        # 1) Store current answer
        key = self.QUESTIONS[step][0]
        ctx.user_data[key] = update.message.text.strip()

        # 2) Advance or finish
        step += 1
        if step < len(self.QUESTIONS):
            ctx.user_data["step"] = step
            await self.ask_question(update, ctx)
        else:
            await self.summary(update, ctx)
            ctx.user_data.clear()

    async def summary(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"✅ Setup complete:\n"
            f"• Puffs: {ctx.user_data['puffs']}\n"
            f"• Method: {ctx.user_data['method']}\n"
            f"• Goal: {ctx.user_data['goal']}"
        )

    def run(self) -> None:
        LOG.info("Bot started …")
        self.app.run_polling()


if __name__ == "__main__":
    TelegramBot().run()
