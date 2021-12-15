#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import re


# Пагинация обложек
PATTERN_PAGE_COVER = re.compile(r'^cover#(\d+)$')

# Пагинация обложек по игре
PATTERN_PAGE_COVER_BY_GAME = re.compile(r'^cover#(\d+)_by_game_id=(\d+)$')

# Пагинация обложек по серии игр
PATTERN_PAGE_COVER_BY_GAME_SERIES = re.compile(r'^cover#(\d+)_by_game_series_id=(\d+)$')

# Пагинация обложек по автору
PATTERN_PAGE_COVER_BY_AUTHOR = re.compile(r'^cover#(\d+)_by_author_id=(\d+)$')

# NOTE: Пока не используется:
# # Пагинация авторов с сортировкой по названию. Сортировка по возрастанию
# PATTERN_PAGE_AUTHORS_BY_NAME = re.compile(r'^authors#(\d+)_by_name__asc$')
#
# # Пагинация авторов с сортировкой по количеству обложек. Сортировка по убыванию
# PATTERN_PAGE_AUTHORS_BY_COVERS = re.compile(r'^authors#(\d+)_by_covers__desc$')
#
# # Пагинация игр с сортировкой по названию. Сортировка по возрастанию
# PATTERN_PAGE_GAMES_BY_NAME = re.compile(r'^games#(\d+)_by_name__asc$')
#
# # Пагинация игр с сортировкой по количеству обложек. Сортировка по убыванию
# PATTERN_PAGE_GAMES_BY_COVERS = re.compile(r'^games#(\d+)_by_covers__desc$')
#
# # Пагинация серий игр с сортировкой по названию. Сортировка по возрастанию
# PATTERN_PAGE_GAME_SERIES_BY_NAME = re.compile(r'^game_series#(\d+)_by_name__asc$')
#
# # Пагинация серий игр с сортировкой по количеству обложек. Сортировка по убыванию
# PATTERN_PAGE_GAME_SERIES_BY_COVERS = re.compile(r'^game_series#(\d+)_by_covers__desc$')
