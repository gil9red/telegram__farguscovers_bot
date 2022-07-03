#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import enum
import json
import math
from typing import Union, List, Optional

import telegram.error
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, ReplyMarkup
)
from telegram.ext import CallbackContext

# pip install python-telegram-bot-pagination
from telegram_bot_pagination import InlineKeyboardPaginator

import config


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
    **kwargs,
):
    # Для запросов CallbackQuery нужно менять текущее сообщение
    if query:
        # Fix error: "telegram.error.BadRequest: Message is not modified"
        if text == query.message.text and is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
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

    else:
        message.reply_text(
            text,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs,
        )


def reply_text_or_edit_with_keyboard_paginator(
        message: Message,
        query: Optional[CallbackQuery],
        text: str,
        page_count: int,
        items_per_page: int,
        current_page: int,
        data_pattern: str,
        before_inline_buttons: List[InlineKeyboardButton] = None,
        after_inline_buttons: List[InlineKeyboardButton] = None,
        quote: bool = False,
        **kwargs,
):
    page_count = math.ceil(page_count / items_per_page)

    paginator = InlineKeyboardPaginator(
        page_count=page_count,
        current_page=current_page,
        data_pattern=data_pattern,
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
        **kwargs,
    )
