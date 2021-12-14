#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


from telegram import Update
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters
)

from bot.common import log_func, process_error, log, reply_message
from db import Cover


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    text = (
        'Бот для отображения обложек группы ВК https://vk.com/farguscovers\n\n'
        f'Всего {Cover.select().count()} обложек за период '
        f'{Cover.get_first().date_time.year}-{Cover.get_last().date_time.year}'
    )

    reply_message(text, update, context)


@log_func(log)
def on_request(update: Update, context: CallbackContext):
    message = update.effective_message

    text = message.text

    reply_message(text)


def on_error(update: Update, context: CallbackContext):
    process_error(log, update, context)


def setup(dp: Dispatcher):
    dp.add_handler(CommandHandler('start', on_start))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
