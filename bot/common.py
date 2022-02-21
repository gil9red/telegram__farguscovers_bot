#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import json
import logging
import sys
import re

from pathlib import Path
from typing import Optional, Union

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Filters

import config
from config import DIR_LOGS, USER_NAME_ADMINS
from third_party.reply_message import reply_message, SeverityEnum


FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


def is_equal_inline_keyboards(
        keyboard_1: Union[InlineKeyboardMarkup, str],
        keyboard_2: InlineKeyboardMarkup
) -> bool:
    if isinstance(keyboard_1, InlineKeyboardMarkup):
        keyboard_1_inline_keyboard = keyboard_1.to_dict()['inline_keyboard']
    elif isinstance(keyboard_1, str):
        keyboard_1_inline_keyboard = json.loads(keyboard_1)['inline_keyboard']
    else:
        raise Exception(f'Unsupported format (keyboard_1={type(keyboard_1)})!')

    keyboard_2_inline_keyboard = keyboard_2.to_dict()['inline_keyboard']
    return keyboard_1_inline_keyboard == keyboard_2_inline_keyboard


def get_logger(file_name: str, dir_name='logs'):
    dir_name = Path(dir_name).resolve()
    dir_name.mkdir(parents=True, exist_ok=True)

    file_name = str(dir_name / Path(file_name).resolve().name) + '.log'

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s')

    fh = logging.FileHandler(file_name, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.DEBUG)

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    log.addHandler(fh)
    log.addHandler(ch)

    return log


def process_error(log: logging.Logger, update: Update, context: CallbackContext):
    log.error('Error: %s\nUpdate: %s', context.error, update, exc_info=context.error)
    if update:
        reply_message(config.ERROR_TEXT, update, context, severity=SeverityEnum.ERROR)


def get_slug(text: Optional[str]) -> str:
    if not text:
        return ''

    text = text.strip().replace(' ', '_')
    return re.sub(r'\W', '', text).lower()


log = get_logger('main', DIR_LOGS)


if __name__ == '__main__':
    assert get_slug("") == ""
    assert get_slug('Half-Life 2: Episode Two') == 'halflife_2_episode_two'
    assert get_slug("! ! !") == "__"
    assert get_slug("123") == "123"
    assert get_slug("1 2-3") == "1_23"
    assert get_slug("  Привет World!") == "привет_world"
    assert get_slug(None) == ''
