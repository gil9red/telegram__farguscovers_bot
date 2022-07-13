#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import enum
import json

import logging
import math
import sys
import re

from pathlib import Path
from typing import Optional, Union, List

import telegram.error
from telegram import Update, InlineKeyboardMarkup, ReplyMarkup, Message, CallbackQuery, InlineKeyboardButton
from telegram.ext import CallbackContext, Filters

# pip install python-telegram-bot-pagination
from telegram_bot_pagination import InlineKeyboardPaginator

import config
from config import DIR_LOGS, USER_NAME_ADMINS


FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


class SeverityEnum(enum.Enum):
    NONE = '{text}'
    INFO = 'ℹ️ {text}'
    ERROR = '⚠ {text}'


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


def reply_message(
        text: str,
        update: Update,
        context: CallbackContext,
        severity: SeverityEnum = SeverityEnum.NONE,
        reply_markup: ReplyMarkup = None,
        quote: bool = True,
        **kwargs
):
    message = update.effective_message

    text = severity.value.format(text=text)

    for n in range(0, len(text), config.MAX_MESSAGE_LENGTH):
        mess = text[n: n + config.MAX_MESSAGE_LENGTH]
        message.reply_text(
            mess,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs
        )


def reply_text_or_edit_with_keyboard(
    message: Message,
    query: Optional[CallbackQuery],
    text: str,
    reply_markup: Union[InlineKeyboardMarkup, str],
    quote: bool = False,
    as_new_msg: bool = False,
    force_edit: bool = False,
    **kwargs,
):
    if (not query or as_new_msg) and not force_edit:
        message.reply_text(
            text,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs,
        )
        return

    # Для запросов CallbackQuery нужно менять текущее сообщение
    # Fix error: "telegram.error.BadRequest: Message is not modified"
    if query and text == query.message.text and is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
        return

    try:
        message.edit_text(
            text,
            reply_markup=reply_markup,
            **kwargs,
        )
    except telegram.error.BadRequest as e:
        if 'Message is not modified' in str(e):
            return

        raise e


def reply_text_or_edit_with_keyboard_paginator(
        message: Message,
        query: Optional[CallbackQuery],
        text: str,
        page_count: int,
        items_per_page: int,
        current_page: int,
        paginator_pattern: str,
        before_inline_buttons: List[InlineKeyboardButton] = None,
        after_inline_buttons: List[InlineKeyboardButton] = None,
        quote: bool = False,
        as_new_msg: bool = False,
        force_edit: bool = False,
        **kwargs,
):
    page_count = math.ceil(page_count / items_per_page)

    paginator = InlineKeyboardPaginator(
        page_count=page_count,
        current_page=current_page,
        data_pattern=paginator_pattern,
    )
    if before_inline_buttons:
        paginator.add_before(*before_inline_buttons)

    if after_inline_buttons:
        paginator.add_after(*after_inline_buttons)

    reply_markup = paginator.markup

    reply_text_or_edit_with_keyboard(
        message, query,
        text,
        reply_markup,
        quote=quote,
        as_new_msg=as_new_msg,
        force_edit=force_edit,
        **kwargs,
    )


def get_deep_linking(argument, context: CallbackContext) -> str:
    return f'{context.bot.link}?start={argument}'


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
