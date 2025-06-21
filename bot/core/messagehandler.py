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

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
            CommandHandler("test", self.test),
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
    
    async def test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display current user data for debugging."""
        try:
            # Convert user data to a readable string, handling potential circular references
            user_data_str = json.dumps(context.user_data, indent=2, default=str)
            # Escape special characters for Markdown
            escaped_data = user_data_str.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
            
            await update.message.reply_text(
                f"```\n{escaped_data}\n```",
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            await update.message.reply_text(f"Error displaying data: {str(e)}")

    async def setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initialize user setup process."""
        try:
            user_id = self.user_id(update)
            user_name = self.user_name(update)
            
            if not user_id or not user_name:
                raise ValueError("User identification failed")

            # Log the setup initiation
            logger.info(f"Setup initiated by user {user_name} (ID: {user_id})")
            
            # Initialize questions first
            questions = [
                "📊 *Question 1:*\nHow many puffs do you typically have per day?\n\n"
                "Please enter a number (example: 20)",
                
                "🎯 *Question 2:*\nHow would you like to reduce your puffs?\n\n"
                "*Type one of these options:*\n"
                "• `number` - Reduce by a specific number of puffs\n"
                "• `percent` - Reduce by a percentage",
                
                "💪 *Question 3:*\nWhat's your weekly reduction goal?\n\n"
                "• If you chose 'number': Enter puffs to reduce (example: 5)\n"
                "• If you chose 'percent': Enter percentage (example: 10)"
            ]

            # Check if user already has setup data
            if self.SETUP_KEY in context.user_data:
                # Clear existing setup data to start fresh
                context.user_data.clear()
                await update.message.reply_text(
                    "You have already setup your account in the past.\nStarting setup process again from the beginning..."
                )

            # Initialize user setup data
            context.user_data['questions'] = questions
            context.user_data[self.SETUP_KEY] = {
                'user_id': user_id,
                'user_name': user_name,
                'setup_id': str(uuid4()),
                'current_question': 0,
                'answers': {}  # Store all answers here
            }

            # Define questions with clear instructions
            context.user_data['questions'] = [
                "📊 *Question 1:*\nHow many puffs do you typically take per day?\n\n"
                "Please enter a number (example: 20)",
                
                "🎯 *Question 2:*\nHow would you like to reduce your puffs?\n\n"
                "*Type one of these options:*\n"
                "• `number` - Reduce by a specific number of puffs\n"
                "• `percent` - Reduce by a percentage",
                
                "💪 *Question 3:*\nWhat's your weekly reduction goal?\n\n"
                "• If you chose 'number': Enter puffs to reduce (example: 5)\n"
                "• If you chose 'percent': Enter percentage (example: 10)"
            ]

            # Send first question
            await update.message.reply_text(
                context.user_data['questions'][0],
                parse_mode='MarkdownV2'
            )
            return self.ANSWERING

        except Exception as e:
            logger.error(f"Setup error for user {self.user_id(update)}: {str(e)}")
            await update.message.reply_text(
                "⚠️ Setup failed\\. Please try again with /setup"
            )
            return ConversationHandler.END

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process answers and manage conversation flow."""
        try:
            setup_data = context.user_data[self.SETUP_KEY]
            current_q = setup_data['current_question']
            answer = update.message.text.strip().lower()
            
            # Process based on current question
            if current_q == 0:  # Daily puffs
                try:
                    puffs = int(answer)
                    if puffs <= 0:
                        raise ValueError("Puffs must be positive")
                    setup_data['answers']['daily_puffs'] = puffs
                    setup_data['current_question'] = 1
                    await update.message.reply_text(
                        context.user_data['questions'][1],
                        parse_mode='MarkdownV2'
                    )
                except ValueError:
                    await update.message.reply_text(
                        "❌ Please enter a valid positive number\\."
                    )
                return self.ANSWERING

            elif current_q == 1:  # Reduction type
                if answer not in ['number', 'percent']:
                    await update.message.reply_text(
                        "❌ Please type either `number` or `percent`\\.",
                        parse_mode='MarkdownV2'
                    )
                    return self.ANSWERING
                
                setup_data['answers']['reduction_type'] = answer
                setup_data['current_question'] = 2
                await update.message.reply_text(
                    context.user_data['questions'][2],
                    parse_mode='MarkdownV2'
                )
                return self.ANSWERING

            elif current_q == 2:  # Goal value
                try:
                    goal = float(answer)
                    if goal <= 0:
                        raise ValueError("Goal must be positive")
                    setup_data['answers']['goal_value'] = goal
                    
                    # Create summary
                    summary = self._create_summary(setup_data['answers'])
                    await update.message.reply_text(summary, parse_mode='MarkdownV2')
                    return ConversationHandler.END
                    
                except ValueError:
                    await update.message.reply_text(
                        "❌ Please enter a valid positive number\\."
                    )
                    return self.ANSWERING

        except KeyError as e:
            logger.error(f"Answer handling error: {e}")
            await update.message.reply_text(
                "⚠️ Something went wrong\\. Please restart with /setup"
            )
            return ConversationHandler.END

    def _create_summary(self, answers: dict) -> str:
        """Create a formatted summary of user's answers."""
        return (
            "✅ *Setup Complete\\!*\n\n"
            f"Daily puffs: `{answers['daily_puffs']}`\n"
            f"Reduction type: `{answers['reduction_type']}`\n"
            f"Weekly goal: `{answers['goal_value']}`"
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