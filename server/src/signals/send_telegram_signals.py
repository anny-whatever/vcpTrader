import os
import logging
import httpx
import asyncio
from tabulate import tabulate  # Make sure this is installed in your venv

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN_FIVE_EMA = os.getenv("TELEGRAM_BOT_TOKEN_FIVE_EMA")
CHAT_ID_FIVE_EMA = os.getenv("TELEGRAM_CHAT_ID_FIVE_EMA")

def convert_to_table(message: str) -> str:
    """
    Converts a text message into a table using the tabulate library.
    Steps:
      1. Split the message by lines.
      2. Identify a 'title' (the first non-dashed line without a colon).
      3. Extract key-value pairs from lines containing a colon.
      4. Use tabulate to create a neat two-column table.
      5. Wrap it all in <pre> tags for Telegram.
    """
    lines = message.splitlines()
    title = ""
    rows = []

    for line in lines:
        stripped = line.strip()

        # Skip lines that are purely dashes (e.g. "------------------------------")
        if stripped and set(stripped) == {"-"}:
            continue

        # If we haven't found a title yet, and this line doesn't have a colon, treat it as a title
        if not title and ":" not in stripped:
            title = stripped

        # If the line has a colon, treat it as a key-value pair
        elif ":" in stripped:
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                rows.append([key, value])

    # If we found no key-value pairs, just return the original message in <pre>
    if not rows:
        return f"<pre>{message}</pre>"

    # Build a two-column table
    # Use "plain" or "pretty" or any other tabulate format that suits you
    table = tabulate(rows, tablefmt="plain")

    # Combine title + table
    final_message = f"{title}\n{table}"
    return f"<pre>{final_message}</pre>"

async def send_telegram_message_five_ema(text: str):
    """
    Async function to send a message to Telegram using httpx.
    We convert the message into a neat table before sending.
    """
    if not TELEGRAM_BOT_TOKEN_FIVE_EMA or not CHAT_ID_FIVE_EMA:
        logger.warning("Telegram credentials are not set. Cannot send message.")
        return None

    # Convert the incoming text into a formatted table
    formatted_text = convert_to_table(text)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_FIVE_EMA}/sendMessage"
    payload = {
        "chat_id": CHAT_ID_FIVE_EMA,
        "text": formatted_text,
        "parse_mode": "HTML",  # Ensure Telegram treats <pre> tags correctly
    }

    logger.info(f"Sending message to chat {CHAT_ID_FIVE_EMA}: '{formatted_text}'")

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
