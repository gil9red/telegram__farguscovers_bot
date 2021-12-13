#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import enum

from telegram import Update, ReplyMarkup
from telegram.ext import CallbackContext

import config


class SeverityEnum(enum.Enum):
    NONE = '{text}'
    INFO = 'ℹ️ {text}'
    ERROR = '⚠ {text}'


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
