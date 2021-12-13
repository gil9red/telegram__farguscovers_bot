#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import json
from collections import defaultdict

from config import FILE_NAME_DUMP
from db import Game, GameSeries, Author, Cover, Author2Cover


def append_to_db(dump: dict):
    series = dump["game_series"]
    game_series = GameSeries.add(name=series) if series else None

    name = dump["game_name"]
    game = Game.add(name=name, series=game_series)

    authors = []
    for author_dump in dump['authors']:
        author_id = author_dump['id']

        author = Author.get_or_none(id=author_id)
        if not author:
            author_name = author_dump['name']
            author = Author.create(id=author_id, name=author_name)

        authors.append(author)

    cover_file_name = dump['photo_file_name']
    cover = Cover.get_or_none(file_name=cover_file_name)
    if not cover:
        cover_post_url = dump['post_url']
        cover_photo_post_url = dump['photo_post_url']
        cover_text = dump['cover_text']
        date_time = dump['date_time']

        cover = Cover.create(
            text=cover_text,
            file_name=cover_file_name,
            url_post=cover_post_url,
            url_post_image=cover_photo_post_url,
            game=game,
            date_time=DT.datetime.fromisoformat(date_time),
        )

    for author in authors:
        link = Author2Cover.get_or_none(author=author, cover=cover)
        if not link:
            Author2Cover.create(author=author, cover=cover)


def make_identical_authors_unique():
    """
    Функция добавит id к name тем авторам, что имеют одинаковое имя.
    Пример: 'DELETED' -> 'DELETED (id74388128)'
    """

    name_by_objects = defaultdict(list)
    for author in Author.select():
        name_by_objects[author.name].append(author)

    for objects in name_by_objects.values():
        if len(objects) == 1:
            continue

        for author in objects:
            name = author.name
            new_name = f'{name} (id{author.id})'
            print(f'Renamed: {name!r} -> {new_name!r}')

            author.name = new_name
            author.save()


if __name__ == '__main__':
    dumps = json.loads(FILE_NAME_DUMP.read_text('utf-8'))

    # Сортировка по id посту и номера картинки из имени файла
    dumps.sort(key=lambda dump: (dump['post_id'], dump['photo_file_name']))

    for dump in dumps:
        append_to_db(dump)

    # TODO: сделать в db.py функцию для вывода
    # TODO: использовать ее в __main__ в db.py
    print(
        f'Game: {Game.select().count()}, GameSeries: {GameSeries.select().count()}, '
        f'Author: {Author.select().count()}, Cover: {Cover.select().count()}, '
        f'Author2Cover: {Author2Cover.select().count()}'
    )
    # Game: 451, GameSeries: 200, Author: 164, Cover: 567, Author2Cover: 581

    make_identical_authors_unique()
    # Renamed: 'DELETED' -> 'DELETED (id74388128)'
    # Renamed: 'DELETED' -> 'DELETED (id135225390)'
    # Renamed: 'DELETED' -> 'DELETED (id230625225)'