from aiogram import F
from aiogram.types import Message
from utils.logging_config import logger

async def chat_id_handler(message: Message):
    chat_id = message.chat.id
    logger.info(f"Received message in chat with ID: {chat_id}")
    #await message.answer(f"ID этого чата: {chat_id}")