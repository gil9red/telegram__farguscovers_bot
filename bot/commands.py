#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import html
import re
import time
from typing import Union, Iterator

from telegram import (
    Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ReplyKeyboardMarkup
)
from telegram.error import BadRequest
from telegram.ext import (
    Dispatcher, CallbackContext, MessageHandler, CommandHandler, Filters, CallbackQueryHandler
)

# pip install python-telegram-bot-pagination
from telegram_bot_pagination import InlineKeyboardPaginator

from bot.common import (
    process_error, log, reply_message, FILTER_BY_ADMIN, SeverityEnum, get_deep_linking,
    is_equal_inline_keyboards, reply_text_or_edit_with_keyboard_paginator, add_prev_next_buttons
)
from bot.decorators import log_func, process_request
from bot.db import Field, Cover, Author, GameSeries, Game, ITEMS_PER_PAGE
from bot import regexp_patterns as P
from bot.regexp_patterns import fill_string_pattern
from config import PLEASE_WAIT


PLEASE_WAIT_INFO = SeverityEnum.INFO.value.format(text=PLEASE_WAIT)


def get_int_from_match(match: re.Match, name: str, default: int = None) -> int:
    try:
        return int(match[name])
    except:
        return default


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    commands = [
        [fill_string_pattern(P.PATTERN_COVERS_REPLY_ALL)],
        [
            fill_string_pattern(P.PATTERN_AUTHORS_REPLY_ALL),
            fill_string_pattern(P.PATTERN_GAME_SERIES_REPLY_ALL),
            fill_string_pattern(P.PATTERN_GAMES_REPLY_ALL)
        ],
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


def get_html_url(url: str, title: str) -> str:
    return f'<a href="{url}">{title}</a>'


def get_deep_linking_start_arg_html_url(
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
        reply_from_start_argument(update, context)

        # Удаление сообщения с /start, что останется после клика на ссылку
        update.effective_message.delete()

        return

    text = (
        'Бот для отображения обложек с стены группы ВК https://vk.com/farguscovers\n\n'
        f'Всего {Cover.count()} обложек за период '
        f'{Cover.get_first().date_time.year}-{Cover.get_last().date_time.year}'
    )

    reply_message(
        text,
        update, context,
        reply_markup=get_reply_keyboard(),
    )


def reply_from_start_argument(
        update: Update,
        context: CallbackContext
):
    start_argument = context.args[0]

    m = P.PATTERN_START_ARGUMENT.match(start_argument)
    class_name = m['class_name']
    object_id = get_int_from_match(m, 'object_id')
    message_id = get_int_from_match(m, 'message_id')

    match class_name:
        case Author.__name__:
            reply_author_card(update, context, author_id=object_id, reply_to_message_id=message_id)

        case GameSeries.__name__:
            reply_game_series_card(update, context, game_series_id=object_id, reply_to_message_id=message_id)

        case Game.__name__:
            reply_game_card(update, context, game_id=object_id, reply_to_message_id=message_id)

        case _:
            raise Exception(f'Неподдерживаемый тип {class_name!r}')


def reply_author_card(
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
        f'Обложки: {author.get_number_of_covers()}\n'
        f'Серии: {author.get_number_of_game_series()}\n'
        f'Игры: {author.get_number_of_games()}'
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_COVER_NEW_PAGE, 1, author_id, None, None)
        ),
        InlineKeyboardButton(
            text='Серии',
            callback_data=fill_string_pattern(P.PATTERN_GAME_SERIES_NEW_PAGE, 1, author_id)
        ),
        InlineKeyboardButton(
            text='Игры',
            callback_data=fill_string_pattern(P.PATTERN_GAMES_NEW_PAGE, 1, author_id, None)
        ),
    ])

    reply_message(
        text,
        update, context,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
    )


def reply_game_series_card(
        update: Update,
        context: CallbackContext,
        game_series_id: int,
        reply_to_message_id: int = None
):
    game_series = GameSeries.get_by_id(game_series_id)

    text = (
        f'<b>Серия {html.escape(game_series.name)}</b>\n'
        '\n'
        f'Обложки: {game_series.get_number_of_covers()}\n'
        f'Авторы: {game_series.get_number_of_authors()}\n'
        f'Игр: {game_series.get_number_of_games()}'
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_COVER_NEW_PAGE, 1, None, game_series_id, None)
        ),
        InlineKeyboardButton(
            text='Авторы',
            callback_data=fill_string_pattern(P.PATTERN_AUTHORS_NEW_PAGE, 1, game_series_id, None)
        ),
        InlineKeyboardButton(
            text='Игры',
            callback_data=fill_string_pattern(P.PATTERN_GAMES_NEW_PAGE, 1, None, game_series_id)
        ),
    ])

    reply_message(
        text,
        update, context,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id,
    )


def reply_game_card(
        update: Update,
        context: CallbackContext,
        game_id: int,
        reply_to_message_id: int = None
):
    message = update.effective_message
    game = Game.get_by_id(game_id)

    message = message.reply_text(
        text=PLEASE_WAIT_INFO,
        reply_to_message_id=reply_to_message_id,
        quote=True,
    )

    game_series_html_url = get_deep_linking_start_arg_html_url(
        update, context,
        title=html.escape(game.series_name),
        obj=game.series,
        reply_to_message_id=message.message_id,
    )

    text = (
        f'<b>Игра {html.escape(game.name)}</b>\n'
        '\n'
        f'Обложки: {game.get_number_of_covers()}\n'
        f'Авторы: {game.get_number_of_authors()}\n'
        f'Серия: {game_series_html_url}'
    )

    markup = InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(
            text='Обложки',
            callback_data=fill_string_pattern(P.PATTERN_COVER_NEW_PAGE, 1, None, None, game_id)
        ),
        InlineKeyboardButton(
            text='Авторы',
            callback_data=fill_string_pattern(P.PATTERN_AUTHORS_NEW_PAGE, 1, None, game_id)
        ),
        InlineKeyboardButton(
            text='Серия',
            callback_data=fill_string_pattern(P.PATTERN_GAME_SERIES_NEW_CARD, game.series.id)
        ),
    ])
    message.edit_text(
        text=text,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )


def get_cover_text(
        update: Update,
        context: CallbackContext,
        cover: Cover,
        reply_to_message_id: int,
        author_id: int = None,
        game_series_id: int = None,
        game_id: int = None,
) -> str:
    cover_text = html.escape(cover.text)
    url_source = get_html_url(cover.url_post_image, "[источник]")

    game_html_url = get_deep_linking_start_arg_html_url(
        update, context,
        title=html.escape(cover.game.name),
        obj=cover.game,
        reply_to_message_id=reply_to_message_id,
    )

    game_series_html_url = get_deep_linking_start_arg_html_url(
        update, context,
        title=html.escape(cover.game.series_name),
        obj=cover.game.series,
        reply_to_message_id=reply_to_message_id,
    )

    author_html_urls = [
        get_deep_linking_start_arg_html_url(
            update, context,
            title=html.escape(a.name),
            obj=a,
            reply_to_message_id=reply_to_message_id,
        )
        for a in cover.get_authors()
    ]

    text = (
        f"<b>{cover_text}</b> {url_source}\n"
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

    return text


def reply_cover_page_card(update: Update, context: CallbackContext, as_new_msg: bool = False):
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    page = 1
    author_id = game_series_id = game_id = None
    if context.match and context.match.groups():
        page = get_int_from_match(context.match, 'page', default=page)
        author_id = get_int_from_match(context.match, 'author_id')
        game_series_id = get_int_from_match(context.match, 'game_series_id')
        game_id = get_int_from_match(context.match, 'game_id')

        total_covers = Cover.count_by(
            by_author=author_id,
            by_game_series=game_series_id,
            by_game=game_id,
        )
    else:
        total_covers = Cover.count()

    cover = Cover.get_by_page(
        page=page,
        by_author=author_id,
        by_game_series=game_series_id,
        by_game=game_id,
    )

    pattern = P.PATTERN_COVER_PAGE

    paginator = InlineKeyboardPaginator(
        page_count=total_covers,
        current_page=page,
        data_pattern=fill_string_pattern(pattern, '{page}', author_id, game_series_id, game_id)
    )
    add_prev_next_buttons(paginator)

    reply_markup = paginator.markup

    if not query or as_new_msg:
        message = message.reply_photo(
            photo=cover.server_file_id,
            caption=PLEASE_WAIT_INFO,
            quote=True,
        )

        text = get_cover_text(
            update=update, context=context,
            cover=cover,
            reply_to_message_id=message.message_id,
            author_id=author_id,
            game_series_id=game_series_id,
            game_id=game_id,
        )

        message.edit_caption(
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )

        return

    # Fix error: "telegram.error.BadRequest: Message is not modified"
    if query and is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
        return

    try:
        text = get_cover_text(
            update=update, context=context,
            cover=cover,
            reply_to_message_id=message.message_id,
            author_id=author_id,
            game_series_id=game_series_id,
            game_id=game_id,
        )

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
def on_cover_card(update: Update, context: CallbackContext):
    reply_cover_page_card(update, context)


@log_func(log)
@process_request(log)
def on_cover_card_as_new_msg(update: Update, context: CallbackContext):
    reply_cover_page_card(update, context, as_new_msg=True)


def reply_page_objects(
        update: Update,
        context: CallbackContext,
        model_title: str,
        model: Union[Author, GameSeries, Game],
        paginator_pattern: str,
        filters: Iterator[Field] = None,
        as_new_msg=False,
):
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    # Если это не callback-запрос или есть нужно новое сообщение
    force_edit: bool = False
    if not query or as_new_msg:
        message = message.reply_text(
            text=PLEASE_WAIT_INFO,
            quote=True,
        )
        # После такого можно будет только редактировать сообщение
        force_edit = True

    page = get_int_from_match(context.match, 'page', default=1)

    items_per_page = ITEMS_PER_PAGE
    start = ((page - 1) * items_per_page) + 1
    objects = model.paginating(
        page=page,
        items_per_page=items_per_page,
        filters=filters,
        order_by=model.name.asc()
    )

    # TODO: Проверить, что не будет переполнения с ITEMS_PER_PAGE
    lines = []
    for i, obj in enumerate(objects, start):
        html_url = get_deep_linking_start_arg_html_url(
            update, context,
            title=html.escape(obj.name),
            obj=obj,
            reply_to_message_id=message.message_id,
        )
        total_covers = obj.get_number_of_covers()
        title = f'{i}. <b>{html_url}</b> ({total_covers})'
        lines.append(title)

    total = model.count(filters)

    text = f'{model_title} ({total}):\n' + '\n'.join(lines)

    reply_text_or_edit_with_keyboard_paginator(
        message, query,
        text=text,
        page_count=total,
        items_per_page=items_per_page,
        current_page=page,
        paginator_pattern=paginator_pattern,
        parse_mode=ParseMode.HTML,
        as_new_msg=as_new_msg,
        force_edit=force_edit,
        quote=True,
    )


def reply_author_page_list(
        update: Update,
        context: CallbackContext,
        as_new_msg=False,
):
    game_series_id = get_int_from_match(context.match, 'game_series_id')
    game_id = get_int_from_match(context.match, 'game_id')

    model = Author

    reply_page_objects(
        update=update, context=context,
        model_title='Авторы',
        model=model,
        paginator_pattern=fill_string_pattern(
            P.PATTERN_AUTHORS_PAGE,
            '{page}',
            game_series_id,
            game_id
        ),
        filters=model.get_filters(
            by_game_series=game_series_id,
            by_game=game_id,
        ),
        as_new_msg=as_new_msg,
    )


@log_func(log)
@process_request(log)
def on_author_page_list(update: Update, context: CallbackContext):
    reply_author_page_list(update, context)


@log_func(log)
@process_request(log)
def on_author_list_as_new_msg(update: Update, context: CallbackContext):
    reply_author_page_list(update, context, as_new_msg=True)


def reply_game_series_page_list(
        update: Update,
        context: CallbackContext,
        as_new_msg=False,
):
    author_id = get_int_from_match(context.match, 'author_id')

    model = GameSeries

    reply_page_objects(
        update=update, context=context,
        model_title='Серии игр',
        model=model,
        paginator_pattern=fill_string_pattern(
            P.PATTERN_GAME_SERIES_PAGE,
            '{page}',
            author_id,
        ),
        filters=model.get_filters(
            by_author=author_id,
        ),
        as_new_msg=as_new_msg,
    )


@log_func(log)
@process_request(log)
def on_game_series_page_list(update: Update, context: CallbackContext):
    reply_game_series_page_list(update, context)


@log_func(log)
@process_request(log)
def on_game_series_list_as_new_msg(update: Update, context: CallbackContext):
    reply_game_series_page_list(update, context, as_new_msg=True)


@log_func(log)
@process_request(log)
def on_game_series_card(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    game_series_id = get_int_from_match(context.match, 'game_series_id')
    reply_game_series_card(update, context, game_series_id=game_series_id)


def reply_game_page_list(
        update: Update,
        context: CallbackContext,
        as_new_msg=False,
):
    author_id = get_int_from_match(context.match, 'author_id')
    game_series_id = get_int_from_match(context.match, 'game_series_id')

    model = Game

    reply_page_objects(
        update=update, context=context,
        model_title='Игры',
        model=model,
        paginator_pattern=fill_string_pattern(
            P.PATTERN_GAMES_PAGE,
            '{page}',
            author_id,
            game_series_id
        ),
        filters=model.get_filters(
            by_author=author_id,
            by_game_series=game_series_id,
        ),
        as_new_msg=as_new_msg,
    )


@log_func(log)
@process_request(log)
def on_game_page_list(update: Update, context: CallbackContext):
    reply_game_page_list(update, context)


@log_func(log)
@process_request(log)
def on_game_list_as_new_msg(update: Update, context: CallbackContext):
    reply_game_page_list(update, context, as_new_msg=True)


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

    title_progress = SeverityEnum.INFO.value.format(text='Загрузка обложек.')

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

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_COVERS_REPLY_ALL), on_cover_card))
    dp.add_handler(CallbackQueryHandler(on_cover_card, pattern=P.PATTERN_COVER_PAGE))
    dp.add_handler(CallbackQueryHandler(on_cover_card_as_new_msg, pattern=P.PATTERN_COVER_NEW_PAGE))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_AUTHORS_REPLY_ALL), on_author_page_list))
    dp.add_handler(CallbackQueryHandler(on_author_page_list, pattern=P.PATTERN_AUTHORS_PAGE))
    dp.add_handler(CallbackQueryHandler(on_author_list_as_new_msg, pattern=P.PATTERN_AUTHORS_NEW_PAGE))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_GAME_SERIES_REPLY_ALL), on_game_series_page_list))
    dp.add_handler(CallbackQueryHandler(on_game_series_page_list, pattern=P.PATTERN_GAME_SERIES_PAGE))
    dp.add_handler(CallbackQueryHandler(on_game_series_list_as_new_msg, pattern=P.PATTERN_GAME_SERIES_NEW_PAGE))
    dp.add_handler(CallbackQueryHandler(on_game_series_card, pattern=P.PATTERN_GAME_SERIES_NEW_CARD))

    dp.add_handler(MessageHandler(Filters.regex(P.PATTERN_GAMES_REPLY_ALL), on_game_page_list))
    dp.add_handler(CallbackQueryHandler(on_game_page_list, pattern=P.PATTERN_GAMES_PAGE))
    dp.add_handler(CallbackQueryHandler(on_game_list_as_new_msg, pattern=P.PATTERN_GAMES_NEW_PAGE))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
