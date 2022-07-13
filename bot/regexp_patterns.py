#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import re

from third_party.regexp import fill_string_pattern as _fill_string_pattern


def fill_string_pattern(pattern: re.Pattern, *args) -> str:
    # Замена None на пустые строки
    args = [arg if arg is not None else '' for arg in args]
    return _fill_string_pattern(pattern, *args)


COMMAND_FILL_SERVER_FILE_ID = 'fill_server_file_id'

PATTERN_COVERS_REPLY_HELP = re.compile(r'^Помощь$', flags=re.IGNORECASE)

# Запрос обложек и их пагинация
COMMAND_COVERS_ALL = 'covers_all'
PATTERN_COVERS_REPLY_ALL = re.compile(r'^Обложки$', flags=re.IGNORECASE)
PATTERN_COVER_PAGE = re.compile(
    r'^covers page=(?P<page>\d+) a#(?P<author_id>\d*) gs#(?P<game_series_id>\d*) g#(?P<game_id>\d*)$'
)
PATTERN_COVER_NEW_PAGE = re.compile(
    r'^covers new page=(?P<page>\d+) a#(?P<author_id>\d*) gs#(?P<game_series_id>\d*) g#(?P<game_id>\d*)$'
)

COMMAND_AUTHORS_ALL = 'authors_all'
PATTERN_AUTHORS_REPLY_ALL = re.compile(r'^Авторы$', flags=re.IGNORECASE)
PATTERN_AUTHORS_PAGE = re.compile(
    r'^authors page=(?P<page>\d+) gs#(?P<game_series_id>\d*) g#(?P<game_id>\d*)$'
)
PATTERN_AUTHORS_NEW_PAGE = re.compile(
    r'^authors new page=(?P<page>\d+) gs#(?P<game_series_id>\d*) g#(?P<game_id>\d*)$'
)

COMMAND_GAME_SERIES_ALL = 'game_series_all'
PATTERN_GAME_SERIES_REPLY_ALL = re.compile(r'^Серии игр$', flags=re.IGNORECASE)
PATTERN_GAME_SERIES_PAGE = re.compile(
    r'^game series page=(?P<page>\d+) a#(?P<author_id>\d*)$'
)
PATTERN_GAME_SERIES_NEW_PAGE = re.compile(
    r'^game series new page=(?P<page>\d+) a#(?P<author_id>\d*)$'
)
PATTERN_GAME_SERIES_NEW_CARD = re.compile(r'^game series new #(?P<game_series_id>\d+)$')

COMMAND_GAMES_ALL = 'games_all'
PATTERN_GAMES_REPLY_ALL = re.compile(r'^Игры$', flags=re.IGNORECASE)
PATTERN_GAMES_PAGE = re.compile(
    r'^games page=(?P<page>\d+) a#(?P<author_id>\d*) gs#(?P<game_series_id>\d*)$'
)
PATTERN_GAMES_NEW_PAGE = re.compile(
    r'^games new page=(?P<page>\d+) a#(?P<author_id>\d*) gs#(?P<game_series_id>\d*)$'
)

PATTERN_START_ARGUMENT = re.compile(
    r'^(?P<class_name>[a-zA-Z]+)_(?P<object_id>\d+)_(?P<message_id>\d+)$'
)
