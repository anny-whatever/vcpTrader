import os
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN_FIVE_EMA = os.getenv("TELEGRAM_KEY")
CHAT_ID_FIVE_EMA = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message_five_ema(text: str):
    """
    Async function to send a message to Telegram using httpx.
    """
    if not TELEGRAM_BOT_TOKEN_FIVE_EMA or not CHAT_ID_FIVE_EMA:
        logger.warning("Telegram credentials are not set. Cannot send message.")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_FIVE_EMA}/sendMessage"
    payload = {
        "chat_id": CHAT_ID_FIVE_EMA,
        "text": text,
    }

    logger.info(f"Sending message to chat {CHAT_ID_FIVE_EMA}: '{text}'")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.is_success:
                logger.info("Telegram message sent successfully.")
                return response.json()
            else:
                logger.error("Error sending Telegram message: %s", response.text)
                return None
        except Exception as e:
            logger.error(f"Exception during Telegram send: {e}", exc_info=True)
            return None

def _send_telegram_in_thread_five_ema(custom_message: str):
    """
    Runs in a separate thread so your main code isn't blocked.
    We create a fresh event loop for the async function.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_message_five_ema(custom_message))
        loop.close()
        logger.info("Telegram message send routine completed.")
    except Exception as e:
        logger.error(f"Error sending Telegram message in background thread: {e}", exc_info=True)
