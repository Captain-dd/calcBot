# logger.py
import sys
import logging
import os

os.environ['PYTHONUNBUFFERED'] = '1'

class FlushHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logging(level=logging.DEBUG):
    """Call once in main.py only."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[FlushHandler(sys.stdout)]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
