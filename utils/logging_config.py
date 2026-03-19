from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {module}:{line} - {message}")
logger.add("logging.log", level="DEBUG", rotation="10 MB", format="{time} | {level} | {module}:{function}:{line} - {message}")