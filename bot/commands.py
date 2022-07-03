#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import html
import re
import time
from typing import Union

from telegram import (
    Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ReplyKeyboardMarkup
)
from telegram.error import BadRequest
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters, CallbackQueryHandler
)

# pip install python-telegram-bot-pagination
from telegram_bot_pagination import InlineKeyboardPaginator

from bot.common import process_error, log, reply_message, FILTER_BY_ADMIN, SeverityEnum, get_deep_linking
from bot.decorators import log_func, process_request
from bot.db import Cover, Author, GameSeries, Game, ITEMS_PER_PAGE
from bot import regexp_patterns as P
from third_party.regexp import fill_string_pattern
from third_party.reply_message import reply_text_or_edit_with_keyboard_paginator, is_equal_inline_keyboards


def calc_pages(page: int, start_page: int, max_page: int) -> tuple[int, int]:
    prev_page = max_page if page <= start_page else page - 1
    next_page = start_page if page >= max_page else page + 1
    return prev_page, next_page


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    commands = [
        [fill_string_pattern(P.PATTERN_REPLY_ALL_COVERS)],
        [
            fill_string_pattern(P.PATTERN_REPLY_ALL_AUTHORS),
            fill_string_pattern(P.PATTERN_REPLY_ALL_GAME_SERIES),
            fill_string_pattern(P.PATTERN_REPLY_ALL_GAMES)
        ],
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


def get_html_url(url: str, title: str) -> str:
    return f'<a href="{url}">{title}</a>'


def get_deep_linking_html_url(
        update: Update,
        context: CallbackContext,
        title: str,
        obj: Union[Author, GameSeries, Game],
        reply_to_message_id: int = None,
) -> str:
    message = update.effective_message

    if reply_to_message_id is None:
        reply_to_message_id = message.message_id

    start_argument = fill_string_pattern(
        P.PATTERN_START_ARGUMENT,
        obj.__class__.__name__,
        obj.id,
        reply_to_message_id
    )
    url = get_deep_linking(start_argument, context)
    return get_html_url(url, title)


@log_func(log)
@process_request(log)
def on_start(update: Update, context: CallbackContext):
    # При открытии ссылки (deep linking)
    # https://t.me/<bot_name>?start=<start_argument>
    if context.args:
        start_argument = context.args[0]

        m = P.PATTERN_START_ARGUMENT.match(start_argument)
        data = m.groupdict()
        class_name = data['class_name']
        object_id = int(data['object_id'])
        message_id = int(data['message_id'])

        match class_name:
            case Author.__name__:
                reply_author(update, context, author_id=object_id, reply_to_message_id=message_id)

            case GameSeries.__name__:
                reply_game_series(update, context, game_series_id=object_id, reply_to_message_id=message_id)

            case Game.__name__:
                reply_game(update, context, game_id=object_id, reply_to_message_id=message_id)

            case _:
                raise Exception(f'Неподдерживаемый тип {class_name!r}')

        # Удаление сообщения с /start, что останется после клика на ссылку
        update.effective_message.delete()

        return

    text = (
        'Бот для отображения обложек с стены группы ВК https://vk.com/farguscovers\n\n'
        f'Всего {Cover.select().count()} обложек за период '
        f'{Cover.get_first().date_time.year}-{Cover.get_last().date_time.year}'
    )

    reply_message(
        text,
        update, context,
        reply_markup=get_reply_keyboard(),
    )


def reply_author(
        update: Update,
        context: CallbackContext,
        author_id: int,
        reply_to_message_id: int = None
):
    author = Author.get_by_id(author_id)

    author_html_url = get_html_url(
        url=author.url,
        title=html.escape(author.name)
    )
    text = (
        f'<b>Автор {author_html_url}</b>\n'
        '\n'
        f'Обложки: {author.get_number_of_covers()}\n'  # TODO: Фильтрация обложек по автору
        f'Серии: {author.get_number_of_game_series()}\n'  # TODO: Фильтрация серий по автору
        f'Игры: {author.get_number_of_games()}'  # TODO: Фильтрация игр по автору
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_PAGE_COVER_AS_NEW_MSG, 1, author_id, None, None)
        ),
    ])

    reply_message(
        text,
        update, context,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
    )


def reply_game_series(
        update: Update,
        context: CallbackContext,
        game_series_id: int,
        reply_to_message_id: int = None
):
    game_series = GameSeries.get_by_id(game_series_id)

    text = (
        f'<b>Серия {html.escape(game_series.name)}</b>\n'
        '\n'
        f'Авторы: {game_series.get_number_of_authors()}\n'   # TODO: Фильтрация авторов по серии
        f'Обложки: {game_series.get_number_of_covers()}\n'  # TODO: Фильтрация обложек по серии
        f'Игр: {game_series.get_number_of_games()}'  # TODO: Фильтрация игр по серии
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_PAGE_COVER_AS_NEW_MSG, 1, None, game_series_id, None)
        ),
    ])

    reply_message(
        text,
        update, context,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
    )


def reply_game(
        update: Update,
        context: CallbackContext,
        game_id: int,
        reply_to_message_id: int = None
):
    game = Game.get_by_id(game_id)

    game_series_html_url = get_deep_linking_html_url(
        update, context,
        title=html.escape(game.series_name),
        obj=game.series,
        reply_to_message_id=reply_to_message_id,
    )

    text = (
        f'<b>Игра {html.escape(game.name)}</b>\n'
        '\n'
        f'Авторы: {game.get_number_of_authors()}\n'   # TODO: Фильтрация авторов по игре
        f'Обложки: {game.get_number_of_covers()}\n'  # TODO: Фильтрация обложек по игре
        f'Серия: {game_series_html_url}'
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_PAGE_COVER_AS_NEW_MSG, 1, None, None, game_id)
        ),
    ])

    reply_message(
        text,
        update, context,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
    )


def reply_cover(update: Update, context: CallbackContext, force_reply: bool = False):
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    author_id = game_series_id = game_id = None

    if context.match and len(context.match.groups()) == 4:
        page = int(context.match.group(1))

        try:
            author_id = int(context.match.group(2))
        except:
            pass

        try:
            game_series_id = int(context.match.group(3))
        except:
            pass

        try:
            game_id = int(context.match.group(4))
        except:
            pass

        total_covers = Cover.count_by(
            by_author=author_id,
            by_game_series=game_series_id,
            by_game=game_id,
        )
    else:
        page = 1
        total_covers = Cover.select().count()

    cover = Cover.get_by_page(
        page=page,
        by_author=author_id,
        by_game_series=game_series_id,
        by_game=game_id,
    )

    cover_text = html.escape(cover.text)
    url_source = get_html_url(cover.url_post_image, "[источник]")

    game_html_url = get_deep_linking_html_url(
        update, context,
        title=html.escape(cover.game.name),
        obj=cover.game,
    )

    game_series_html_url = get_deep_linking_html_url(
        update, context,
        title=html.escape(cover.game.series_name),
        obj=cover.game.series,
    )

    author_html_urls = [
        get_deep_linking_html_url(
            update, context,
            title=html.escape(a.name),
            obj=a,
        )
        for a in cover.get_authors()
    ]

    text = (
        f"Название: {cover_text} {url_source}\n"
        f"Игра: {game_html_url}\n"
        f"Серия: {game_series_html_url}\n"
        f"Автор(ы): {', '.join(author_html_urls)}"
    )
    if author_id or game_series_id or game_id:
        author = Author.get_by_id(author_id) if author_id else None
        game_series = GameSeries.get_by_id(game_series_id) if game_series_id else None
        game = Game.get_by_id(game_id) if game_id else None

        names = []
        if author:
            names.append(html.escape(author.name))

        if game_series:
            names.append(html.escape(game_series.name))

        if game:
            names.append(html.escape(game.name))

        text += f'\n\nФильтрация по: {", ".join(names)}'

    pattern = P.PATTERN_PAGE_COVER

    paginator = InlineKeyboardPaginator(
        page_count=total_covers,
        current_page=page,
        data_pattern=fill_string_pattern(pattern, '{page}', author_id, game_series_id, game_id)
    )
    if total_covers > 1:
        prev_page, next_page = calc_pages(page=page, start_page=1, max_page=total_covers)

        paginator.add_after(
            InlineKeyboardButton(
                text='⬅️',
                callback_data=fill_string_pattern(pattern, prev_page, author_id, game_series_id, game_id)
            ),
            InlineKeyboardButton(
                text='➡️',
                callback_data=fill_string_pattern(pattern, next_page, author_id, game_series_id, game_id)
            ),
        )

    reply_markup = paginator.markup

    if not query or force_reply:
        message.reply_photo(
            photo=cover.server_file_id,
            caption=text,
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
                caption=text,
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if 'Message is not modified' in str(e):
            return

        raise e


@log_func(log)
@process_request(log)
def on_cover(update: Update, context: CallbackContext):
    reply_cover(update, context)


@log_func(log)
@process_request(log)
def on_new_cover_msg(update: Update, context: CallbackContext):
    reply_cover(update, context, force_reply=True)


def reply_page_objects(
        update: Update,
        context: CallbackContext,
        model_title: str,
        model: Union[Author, GameSeries, Game],
        pattern_page: re.Pattern,
):
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    if context.match and len(context.match.groups()) == 1:
        page = int(context.match.group(1))
    else:
        page = 1

    total = model.count()

    items_per_page = ITEMS_PER_PAGE
    start = ((page - 1) * items_per_page) + 1
    objects = model.paginating(page=page, items_per_page=items_per_page, order_by=model.name.asc())

    # TODO: Проверить, что не будет переполнения с ITEMS_PER_PAGE
    lines = []
    for i, obj in enumerate(objects, start):
        html_url = get_deep_linking_html_url(
            update, context,
            title=html.escape(obj.name),
            obj=obj,
        )
        total_covers = obj.get_number_of_covers()
        title = f'{i}. <b>{html_url}</b> ({total_covers})'
        lines.append(title)

    text = f'{model_title} ({total}):\n' + '\n'.join(lines)

    reply_text_or_edit_with_keyboard_paginator(
        message, query, text,
        page_count=total,
        items_per_page=items_per_page,
        current_page=page,
        data_pattern=fill_string_pattern(pattern_page, '{page}'),
        parse_mode=ParseMode.HTML,
    )


@log_func(log)
@process_request(log)
def on_all_authors(update: Update, context: CallbackContext):
    reply_page_objects(
        update, context,
        model_title='Авторы',
        model=Author,
        pattern_page=P.PATTERN_PAGE_AUTHORS,
    )


@log_func(log)
@process_request(log)
def on_all_game_series(update: Update, context: CallbackContext):
    reply_page_objects(
        update, context,
        model_title='Серии игр',
        model=GameSeries,
        pattern_page=P.PATTERN_PAGE_GAME_SERIES,
    )


@log_func(log)
@process_request(log)
def on_all_game(update: Update, context: CallbackContext):
    reply_page_objects(
        update, context,
        model_title='Игры',
        model=Game,
        pattern_page=P.PATTERN_PAGE_GAMES,
    )


@log_func(log)
@process_request(log)
def on_request(update: Update, context: CallbackContext):
    reply_message(
        'Неизвестная команда 🤔',
        update=update, context=context,
        severity=SeverityEnum.ERROR,
        reply_markup=get_reply_keyboard()
    )


@log_func(log)
@process_request(log)
def on_fill_server_file_id(update: Update, _: CallbackContext):
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

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_REPLY_ALL_COVERS), on_cover))
    dp.add_handler(CallbackQueryHandler(on_cover, pattern=P.PATTERN_PAGE_COVER))
    dp.add_handler(CallbackQueryHandler(on_new_cover_msg, pattern=P.PATTERN_PAGE_COVER_AS_NEW_MSG))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_REPLY_ALL_AUTHORS), on_all_authors))
    dp.add_handler(CallbackQueryHandler(on_all_authors, pattern=P.PATTERN_PAGE_AUTHORS))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_REPLY_ALL_GAME_SERIES), on_all_game_series))
    dp.add_handler(CallbackQueryHandler(on_all_game_series, pattern=P.PATTERN_PAGE_GAME_SERIES))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_REPLY_ALL_GAMES), on_all_game))
    dp.add_handler(CallbackQueryHandler(on_all_game, pattern=P.PATTERN_PAGE_GAMES))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
