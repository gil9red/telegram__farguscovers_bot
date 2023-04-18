#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import sys

from pathlib import Path


# Текущая папка, где находится скрипт
DIR = Path(__file__).resolve().parent

DIR_LOGS = DIR / "logs"
DIR_LOGS.mkdir(parents=True, exist_ok=True)

DIR_DATA_VK = DIR / "data_vk"

FILE_NAME_DUMP = DIR_DATA_VK / "dump.json"
if not FILE_NAME_DUMP.exists():
    raise Exception(f"Отсутствует экспортированный файл обложек: {FILE_NAME_DUMP}")

DIR_IMAGES = DIR_DATA_VK / "images"
if not DIR_IMAGES.exists() or not any(DIR_IMAGES.glob("*.jpg")):
    raise Exception(f"Отсутствует или пустая папка с картинками: {DIR_IMAGES}")

TOKEN_FILE_NAME = DIR / "TOKEN.txt"

try:
    TOKEN = os.environ.get("TOKEN") or TOKEN_FILE_NAME.read_text("utf-8").strip()
    if not TOKEN:
        raise Exception("TOKEN пустой!")

except:
    print(
        f"Нужно в {TOKEN_FILE_NAME.name} или в переменную окружения TOKEN добавить токен бота"
    )
    TOKEN_FILE_NAME.touch()
    sys.exit()

SCREENSHOT_GIF_START_DEEP_LINKING = (
    DIR / "etc" / "screenshots" / "start_deep_linking.gif"
)
if not SCREENSHOT_GIF_START_DEEP_LINKING.exists():
    raise Exception(f"Отсутствует файл: {SCREENSHOT_GIF_START_DEEP_LINKING}")

ERROR_TEXT = "Возникла какая-то проблема. Попробуйте повторить запрос или попробовать чуть позже..."
PLEASE_WAIT = "Пожалуйста, подождите..."

# Создание папки для базы данных
DB_DIR_NAME = DIR / "database"
DB_DIR_NAME.mkdir(parents=True, exist_ok=True)

# Путь к файлу базы данных
DB_FILE_NAME = str(DB_DIR_NAME / "database.sqlite")

USER_NAME_ADMINS = [
    "@ilya_petrash",
]

MAX_MESSAGE_LENGTH = 4096
ITEMS_PER_PAGE = 10

DEFAULT_AUTHOR_ID = 0
DEFAULT_AUTHOR_NAME = 'Обложки "Фаргус"'
DEFAULT_AUTHOR_URL = "https://vk.com/farguscovers"
