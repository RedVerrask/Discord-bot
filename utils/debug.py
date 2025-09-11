# utils/debug.py
import logging
import inspect
import os
from datetime import datetime

# Setup base logger
logger = logging.getLogger("AshesBot")

# Log file path
DEBUG_LOG_FILE = os.path.join("data", "debug.log")
os.makedirs("data", exist_ok=True)

def debug_log(message: str, logger=logger, bot=None, **kwargs):
    """
    Centralized debug logger for the bot.
    - Only logs if debug_mode is enabled.
    - Writes to both console and debug.log.
    - Includes timestamp + file + function + context.
    """

    # Skip logging unless debug is on
    if bot is not None and not getattr(bot, "debug_mode", False):
        return

    # Caller details
    frame = inspect.stack()[1]
    origin = f"{frame.filename.split('/')[-1]}:{frame.function}"

    # Format extra context if provided
    extras = " | ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""

    # Final log message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_msg = f"[{timestamp}] 🐞 DEBUG [{origin}] {message}"
    if extras:
        final_msg += f" | {extras}"

    # Console output
    logger.info(final_msg)

    # Append to debug.log file
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(final_msg + "\n")
    except Exception:
        pass  # Don't break bot on logging failure
