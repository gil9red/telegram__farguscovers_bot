#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


from telegram import Update
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters
)

from bot.common import log_func, process_error, log, reply_message


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    # TODO: добавить описание бота и как с ним работать
    # TODO: отобразить клавиатуру
    reply_message(
        'Бот для отображения обложек группы ВК https://vk.com/farguscovers',
        update, context
    )


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
