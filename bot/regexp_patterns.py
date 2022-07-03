#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import re


# Пагинация обложек
PATTERN_PAGE_COVER = re.compile(r'^page of cover#(\d+) a#(.+) gs#(.+) g#(.+)$')

PATTERN_PAGE_COVER_AS_NEW_MSG = re.compile(r'^page as new msg of cover#(\d+) a#(.+) gs#(.+) g#(.+)$')

PATTERN_REPLY_ALL_COVERS = re.compile(r'^Все обложки$', flags=re.IGNORECASE)

PATTERN_REPLY_ALL_AUTHORS = re.compile(r'^Авторы$', flags=re.IGNORECASE)
PATTERN_PAGE_AUTHORS = re.compile(r'^page of authors#(\d+)$')

PATTERN_REPLY_ALL_GAME_SERIES = re.compile(r'^Серии игр$', flags=re.IGNORECASE)
PATTERN_PAGE_GAME_SERIES = re.compile(r'^page of game series#(\d+)$')

PATTERN_REPLY_ALL_GAMES = re.compile(r'^Игры$', flags=re.IGNORECASE)
PATTERN_PAGE_GAMES = re.compile(r'^page of games #(\d+)$')

PATTERN_START_ARGUMENT = re.compile(r'^(?P<class_name>\w+)_(?P<object_id>\d+)_(?P<message_id>\d+)$')
