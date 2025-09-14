from loguru import logger


#logger.remove()  # Удаляем дефолтный хэндлер
logger.add("logging.log", rotation="10 MB", format="{time} | {level} | {module}:{function}:{line} - {message}")
#    logger.add(lambda msg: print(msg, end=""), format="{time} | {level} | {module}:{function}:{line} - {message}") """