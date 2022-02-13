#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time

from telegram import Update
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters
)

from bot.common import process_error, log, reply_message, FILTER_BY_ADMIN
from bot.decorators import log_func, process_request
from bot.db import Cover


@log_func(log)
@process_request(log)
def on_start(update: Update, context: CallbackContext):
    text = (
        'Бот для отображения обложек группы ВК https://vk.com/farguscovers\n\n'
        f'Всего {Cover.select().count()} обложек за период '
        f'{Cover.get_first().date_time.year}-{Cover.get_last().date_time.year}'
    )

    reply_message(text, update, context)


@log_func(log)
@process_request(log)
def on_request(update: Update, context: CallbackContext):
    message = update.effective_message

    text = message.text

    reply_message(text, update, context)


@log_func(log)
@process_request(log)
def on_fill_server_file_id(update: Update, context: CallbackContext):
    message = update.effective_message

    covers = Cover.select().where(Cover.server_file_id.is_null())
    total_covers = covers.count()

    title_progress = 'ℹ️ Загрузка обложек.'

    if not total_covers:
        message.reply_text(
            f'{title_progress}\nВсе обложки уже загружены!',
            quote=True,
        )
        return

    message_progress = message.reply_text(
        title_progress,
        quote=True,
    )

    t = time.perf_counter()

    # Перебор всех обложек без server_file_id
    for i, cover in enumerate(covers, 1):
        message_photo = message.reply_photo(
            photo=open(cover.abs_file_name, 'rb')
        )
        photo_large = max(message_photo.photo, key=lambda x: (x.width, x.height))
        message_photo.delete()

        cover.server_file_id = photo_large.file_id
        cover.save()

        message_progress.edit_text(f'{title_progress}\n{i} / {total_covers}')

        # У ботов лимиты на отправку сообщений
        time.sleep(0.3)

    elapsed_secs = int(time.perf_counter() - t)
    message_progress.edit_text(
        f'{title_progress}\n'
        f'Загружено {total_covers} обложек за {elapsed_secs} секунд.'
    )


def on_error(update: Update, context: CallbackContext):
    process_error(log, update, context)


def setup(dp: Dispatcher):
    dp.add_handler(CommandHandler('start', on_start))

    dp.add_handler(
        CommandHandler('fill_server_file_id', on_fill_server_file_id, FILTER_BY_ADMIN)
    )

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
