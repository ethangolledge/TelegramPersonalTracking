import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, 
    ApplicationBuilder,
    MessageHandler,
    CommandHandler, 
    ContextTypes
)

"""need to know the best time to reliably input the data"""
class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.app = Application.builder().token(os.getenv("TOKEN")).build()
        self._add_handlers()

    def _add_handlers(self):
        """Add command handlers to the bot."""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("setup", self.setup))
        self.app.add_handler(CommandHandler("help", self.help))
        
    def user_id(self, update: Update) -> int:
        """Grabs the user ID from the conversation."""
        return update.effective_user.id if update.effective_user else None

    def user_name(self, update: Update) -> str:
        """Grabs the user name from the conversation."""
        return update.effective_user.first_name if update.effective_user else None
    
    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        message = (
            f"Hello {self.user_name(update)}, as you're probably aware, I'm a bot.\n"
            "I have been specifically designed to help reduce reliance on vaping!\n" \
            "Use /setup to get started or /help for assistance with commands."
        )
        await update.message.reply_text(message, parse_mode='Markdown')

    async def setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Setup the bot to determine the user's goal and preferences."""
        if 'setup_stage' not in context.user_data:
            context.user_data['setup_stage'] = 'puffs'
            await update.message.reply_text(
                "Let's start tracking your progress.\nPlease tell me roughly how many puffs you have a day:"
            )
            return

        if context.user_data['setup_stage'] == 'puffs':
            try:
                puffs = int(update.message.text)
                context.user_data['daily_puffs'] = puffs
                context.user_data['setup_stage'] = 'goal_type'
                context.user_data['user_id'] = self.user_id(update)
                context.user_data['user_name'] = self.user_name(update)
                
                keyboard_goal_type = [
                    [InlineKeyboardButton("Reduce by a set number", callback_data="goal_num")],
                    [InlineKeyboardButton("Reduce by a percentage", callback_data="goal_perc")]
                ]
                await update.message.reply_text(
                    f"Great! You currently have {puffs} puffs per day.\nHow would you like to set your weekly reduction goal?",
                    reply_markup=InlineKeyboardMarkup(keyboard_goal_type)
                )
            except ValueError:
                await update.message.reply_text("Please enter a valid number of puffs.")
            return

        if context.user_data['setup_stage'] == 'goal_target':
            try:
                goal = float(update.message.text)
                context.user_data['goal'] = goal
                goal_type = "puffs" if context.user_data.get('goal_type') == 'num' else "percent"
                
                # Store final user preferences
                user_preferences = {
                    'user_id': context.user_data['user_id'],
                    'user_name': context.user_data['user_name'],
                    'daily_puffs': context.user_data['daily_puffs'],
                    'goal_type': context.user_data['goal_type'],
                    'goal_value': goal
                }
                context.user_data['preferences'] = user_preferences
                
                await update.message.reply_text(
                    f"Setup complete! You will reduce by {goal} {goal_type} per week.\n"
                    f"Starting from {context.user_data['daily_puffs']} daily puffs."
                )
            except ValueError:
                await update.message.reply_text("Please enter a valid number.")

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Available commands:\n/start - Welcome message\n/setup - Setup your tracking preferences\n/help - Show this help message")

    def run(self):
        self.app.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    print("Bot is running...")
    bot.run()
