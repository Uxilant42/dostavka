"""
🍣 Sushi Express - Telegram Ordering Bot
Main entry point for the bot application

Usage:
    1. Set your bot token in config.yaml
    2. Set your admin IDs in config.yaml
    3. Run: python main.py
"""
import logging
import yaml
import os
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Suppress httpx info logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Import handlers
from handlers.user_handlers import get_user_handlers
from handlers.admin_handlers import get_admin_handlers


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    
    if not os.path.exists(config_path):
        logger.error("config.yaml not found! Please create it with your bot token.")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


async def error_handler(update: Update, context):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Notify user about error
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Произошла ошибка. Попробуйте ещё раз или используйте /start"
            )
        except Exception:
            pass


def main():
    """Main function to start the bot"""
    # Load configuration
    config = load_config()
    
    bot_token = config.get('bot', {}).get('token', '')
    
    if not bot_token or bot_token == 'YOUR_BOT_TOKEN':
        logger.error("Please set your bot token in config.yaml!")
        logger.info("Get a token from @BotFather on Telegram")
        sys.exit(1)
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add admin handlers first (higher priority)
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # Add user handlers
    for handler in get_user_handlers():
        application.add_handler(handler)
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Log startup
    admin_ids = config.get('bot', {}).get('admin_ids', [])
    logger.info("=" * 50)
    logger.info("🍣 Sushi Express Bot starting...")
    logger.info(f"📋 Admin IDs: {admin_ids}")
    logger.info("=" * 50)
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
