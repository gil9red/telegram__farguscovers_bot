#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import html
import time

import telegram
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters, CallbackQueryHandler
)

# pip install python-telegram-bot-pagination
from telegram_bot_pagination import InlineKeyboardPaginator

from bot.common import process_error, log, reply_message, FILTER_BY_ADMIN, is_equal_inline_keyboards
from bot.decorators import log_func, process_request
from bot.db import Cover
from bot.regexp_patterns import PATTERN_PAGE_COVER
from third_party.regexp import fill_string_pattern


def calc_pages(page: int, start_page: int, max_page: int) -> tuple[int, int]:
    prev_page = max_page if page <= start_page else page - 1
    next_page = start_page if page >= max_page else page + 1
    return prev_page, next_page


@log_func(log)
@process_request(log)
def on_start(update: Update, context: CallbackContext):
    text = (
        'Бот для отображения обложек с стены группы ВК https://vk.com/farguscovers\n\n'
        f'Всего {Cover.select().count()} обложек за период '
        f'{Cover.get_first().date_time.year}-{Cover.get_last().date_time.year}'
    )

    reply_message(text, update, context)


@log_func(log)
@process_request(log)
def on_cover(update: Update, context: CallbackContext):
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    total_covers = Cover.select().count()

    if context.match:
        page = int(context.match.group(1))
    else:
        page = 1

    prev_page, next_page = calc_pages(page=page, start_page=1, max_page=total_covers)

    cover = Cover.get_by_page(page=page)
    cover_text = html.escape(cover.text)
    game_name = html.escape(cover.game.name)
    url = f'<a href="{cover.url_post_image}">{cover_text}</a>'
    title = url + "\n" + game_name

    paginator = InlineKeyboardPaginator(
        page_count=total_covers,
        current_page=page,
        data_pattern=fill_string_pattern(PATTERN_PAGE_COVER, '{page}')
    )
    paginator.add_after(
        InlineKeyboardButton(text='⬅️', callback_data=fill_string_pattern(PATTERN_PAGE_COVER, prev_page)),
        InlineKeyboardButton(text='➡️', callback_data=fill_string_pattern(PATTERN_PAGE_COVER, next_page)),
    )

    reply_markup = paginator.markup

    if not query:
        message.reply_photo(
            photo=cover.server_file_id,
            caption=title,
            parse_mode=ParseMode.HTML,
            reply_markup=paginator.markup,
            quote=True,
        )
        return

    # Fix error: "telegram.error.BadRequest: Message is not modified"
    if is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
        return

    try:
        message.edit_media(
            media=InputMediaPhoto(
                media=cover.server_file_id,
                caption=title,
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=reply_markup,
        )
    except telegram.error.BadRequest as e:
        if 'Message is not modified' in str(e):
            return

        raise e


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

    dp.add_handler(
        CallbackQueryHandler(on_cover, pattern=PATTERN_PAGE_COVER)
    )
    dp.add_handler(MessageHandler(Filters.text, on_cover))

    dp.add_error_handler(on_error)
