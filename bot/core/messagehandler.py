import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    ContextTypes, 
    ConversationHandler, 
    MessageHandler, 
    filters, 
    PicklePersistence
)
from uuid import uuid4
import json

# Set up logging configuration
log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramBot:
    # Class constants
    ANSWERING = 0
    SETUP_KEY = "setup_data"  # Default key for user setup data

    def __init__(self):
        """Initialize the bot with persistence and handlers."""
        load_dotenv()
        
        # Initialize persistence
        persistence = PicklePersistence(filepath="conversation_states")
        
        # Build application with persistence
        self.app = Application.builder().token(
            os.getenv("TOKEN")
        ).persistence(persistence).build()
        
        # Set up handlers
        self._create_handlers()

        self.questions = {
            0: {
                'question': "📊 How many puffs do you typically take per day?\n\n",
                'help_text': "Please enter a number (example: 20)",
                'validation': 'number',
                'options': None,
                'error_msg': "❌ Please enter a valid positive number\\."
            },
            1: {
                'question': "🎯 How would you like to reduce your puffs?\n\n",
                'help_text': "Type 'number' for fixed reduction or 'percent' for percentage reduction",
                'validation': 'choice',
                'options': ['number', 'percent'],
                'error_msg': "❌ Please type either `number` or `percent`\\"
            },
            2: {
                'question': "💪 What's your weekly reduction goal?\n\n",
                'help_text': "Enter a number for puffs or percentage based on your previous choice",
                'validation': 'number',
                'options': None,
                'error_msg': "❌ Please enter a valid positive number\\."
            }
            }

    def _create_handlers(self):
        """Create and register all handlers for the bot."""
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self.setup)],
            states={
                self.ANSWERING: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        self.handle_answer
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            name="user_setup",
            persistent=True
        )

        # Register all handlers
        handlers = [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help),
            CommandHandler("setup", self.setup),
            conv_handler
        ]
        
        for handler in handlers:
            self.app.add_handler(handler)

    def user_id(self, update: Update) -> int:
        """Get user ID safely."""
        return update.effective_user.id if update.effective_user else None

    def user_name(self, update: Update) -> str:
        """Get username safely."""
        return update.effective_user.first_name if update.effective_user else None

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_name = self.user_name(update)
        welcome_message = (
            f"Hello {user_name}! 👋\n\n"
            f"I'm your personal vaping reduction assistant. I'm here to help "
            f"you track and reduce your vaping habits.\n\n"
            f"Use /setup to begin your reduction journey or /help for available commands."
        )
        await update.message.reply_text(welcome_message)

    async def setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initialize user setup process."""
        try:
            # Initialize setup data
            context.user_data[self.SETUP_KEY] = {
                'user_id': self.user_id(update),
                'current_question': 0,
                'answers': {}
            }

            # Ask first question
            await update.message.reply_text(
                self.questions[0]['text'],
                parse_mode='MarkdownV2'
            )
            return self.ANSWERING

        except Exception as e:
            logger.error(f"Setup error: {str(e)}")
            await update.message.reply_text("⚠️ Setup failed\\. Please try again\\.")
            return ConversationHandler.END

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle answers and manage conversation flow."""
        try:
            setup_data = context.user_data[self.SETUP_KEY]
            current_q = setup_data['current_question']
            answer = update.message.text.strip().lower()
            question = self.questions[current_q]

            # Validate answer based on question type
            if question['validation'] == 'number':
                try:
                    value = float(answer)
                    if value <= 0:
                        raise ValueError()
                    setup_data['answers'][f'q{current_q}'] = value
                except ValueError:
                    await update.message.reply_text(
                        question['error_msg'],
                        parse_mode='MarkdownV2'
                    )
                    return self.ANSWERING

            elif question['validation'] == 'choice':
                if answer not in question['options']:
                    await update.message.reply_text(
                        question['error_msg'],
                        parse_mode='MarkdownV2'
                    )
                    return self.ANSWERING
                setup_data['answers'][f'q{current_q}'] = answer

            # Move to next question or finish
            if current_q < len(self.questions) - 1:
                setup_data['current_question'] += 1
                next_question = self.questions[setup_data['current_question']]
                await update.message.reply_text(
                    next_question['text'],
                    parse_mode='MarkdownV2'
                )
                return self.ANSWERING
            else:
                # Create and show summary
                summary = self._create_summary(setup_data['answers'])
                await update.message.reply_text(summary, parse_mode='MarkdownV2')
                return ConversationHandler.END

        except Exception as e:
            logger.error(f"Answer handling error: {str(e)}")
            await update.message.reply_text(
                "⚠️ Something went wrong\\. Please try /setup again\\."
            )
            return ConversationHandler.END

    def _create_summary(self, answers: dict) -> str:
        """Create formatted summary of answers."""
        return (
            "✅ *Setup Complete\\!*\n\n"
            f"Daily puffs: `{answers['q0']}`\n"
            f"Reduction type: `{answers['q1']}`\n"
            f"Weekly goal: `{answers['q2']}`"
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle conversation cancellation."""
        if self.SETUP_KEY in context.user_data:
            del context.user_data[self.SETUP_KEY]
            logger.info(f"Setup cancelled by user {self.user_id(update)}")
        
        await update.message.reply_text(
            "❌ Setup cancelled\\. Use /setup to start again\\."
        )
        return ConversationHandler.END

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Display help information."""
        help_text = (
            "*Available Commands:*\n\n"
            "🟢 /start \\- Welcome message\n"
            "⚙️ /setup \\- Configure your reduction plan\n"
            "❓ /help \\- Show this help message"
        )
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')

    def run(self):
        """Start the bot."""
        logger.info("Starting bot...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()