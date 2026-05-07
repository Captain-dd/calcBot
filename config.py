
import os
from logger import setup_logging, get_logger

log = get_logger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

log.info(f"BOT_TOKEN loaded: {TOKEN is not None}")
log.info(f"WEBHOOK_URL loaded: {WEBHOOK_URL is not None} → {WEBHOOK_URL}")
log.info(f"WEBHOOK_SECRET loaded: {WEBHOOK_SECRET is not None}")

if not TOKEN or not WEBHOOK_URL or not WEBHOOK_SECRET:
    log.critical("One or more required env variables are missing. Exiting.")
    exit(1)
    
TABLE_MIN = int(os.getenv("TABLE_MIN", 0))
TABLE_MAX = int(os.getenv("TABLE_MAX", 0))

SQUARE_MIN = int(os.getenv("SQUARE_MIN", 0))
SQUARE_MAX = int(os.getenv("SQUARE_MAX", 0))

CUBE_MIN = int(os.getenv("CUBE_MIN", 0))
CUBE_MAX = int(os.getenv("CUBE_MAX", 0))


TABLE = "table"
SQUARE = "square"
CUBE = "cube"
SINGLE_DIGIT_ADDITION = "single digit addition"
SINGLE_DIGIT_SUBTRACTION = "single digit subtraction"
TWO_DIGIT_ADDITION = "two digit addition"
TWO_DIGIT_SUBTRACTION = "two digit subtraction"
THREE_DIGIT_ADDITION = "three digit addition"
THREE_DIGIT_SUBTRACTION = "three digit subtraction"
ADDITION_SUBTRACTION_MIX = "addition subtraction mix"