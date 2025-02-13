# send_telegram_alert.py
import os
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_KEY")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(text: str):
    """
    Async send to Telegram using httpx.
    """
    logger.debug("Preparing to send a Telegram message.")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }

    logger.info(f"Sending message to {CHAT_ID}: '{text}'")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.is_success:
        logger.info("Message sent successfully.")
        return response.json()
    else:
        logger.error("Error sending Telegram message: %s", response.text)
        return None

def _send_telegram_in_thread(custom_message: str):
    """
    Runs in a separate thread so your main code isn't blocked.
    This time, we DO need an event loop, because we have an async function.
    """
    try:
        logger.info("Starting Telegram send in a separate thread.")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_message(custom_message))
        loop.close()

        logger.info("Telegram message sent successfully from a background thread.")
    except Exception as e:
        logger.error(f"Error sending Telegram message in background thread: {e}", exc_info=True)
