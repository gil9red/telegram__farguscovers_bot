#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import os
import time

# pip install python-telegram-bot
from telegram import Update
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackContext, Defaults

from config import TOKEN
from common import get_logger, log_func, reply_error


log = get_logger(__file__)


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    # TODO: добавить описание бота и как с ним работать
    # TODO: отобразить клавиатуру
    update.effective_message.reply_text(
        'Бот для отображения обложек группы ВК https://vk.com/farguscovers'
    )


@log_func(log)
def on_request(update: Update, context: CallbackContext):
    message = update.effective_message

    text = message.text

    message.reply_text(text)


def on_error(update: Update, context: CallbackContext):
    reply_error(log, update, context)


def main():
    log.debug('Start')

    cpu_count = os.cpu_count()
    workers = cpu_count
    log.debug('System: CPU_COUNT=%s, WORKERS=%s', cpu_count, workers)

    updater = Updater(
        TOKEN,
        workers=workers,
        defaults=Defaults(run_async=True),
    )
    bot = updater.bot
    log.debug(f'Bot name {bot.first_name!r} ({bot.name})')

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', on_start))
    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)

    updater.start_polling()
    updater.idle()

    log.debug('Finish')


if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            log.exception('')

            timeout = 15
            log.info(f'Restarting the bot after {timeout} seconds')
            time.sleep(timeout)
