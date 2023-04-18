#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import datetime as DT
import json
from collections import defaultdict

from config import (
    FILE_NAME_DUMP,
    DEFAULT_AUTHOR_NAME,
    DEFAULT_AUTHOR_URL,
    DEFAULT_AUTHOR_ID,
)
from bot.db import Game, GameSeries, Author, Cover, Author2Cover, BaseModel


def append_to_db(dump: dict):
    series = dump["game_series"]
    game_series = GameSeries.add(name=series) if series else None

    name = dump["game_name"]
    game = Game.add(name=name, series=game_series)

    authors = []
    for author_dump in dump["authors"]:
        author_id = author_dump["id"]
        author_name = author_dump["name"]

        author = Author.add(id=author_id, name=author_name)
        authors.append(author)

    # Пусть у каждой обложки будет автор, по умолчанию, это сама группа
    if not authors:
        author = Author.add(
            id=DEFAULT_AUTHOR_ID, name=DEFAULT_AUTHOR_NAME, url=DEFAULT_AUTHOR_URL
        )
        authors.append(author)

    cover_file_name = dump["photo_file_name"]
    cover = Cover.get_or_none(file_name=cover_file_name)
    if not cover:
        cover_post_url = dump["post_url"]
        cover_photo_post_url = dump["photo_post_url"]
        cover_text = dump["cover_text"]
        date_time = dump["date_time"]

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
            new_name = f"{name} (id{author.id})"
            print(f"Renamed: {name!r} -> {new_name!r}")

            author.name = new_name
            author.save()


if __name__ == "__main__":
    dumps = json.loads(FILE_NAME_DUMP.read_text("utf-8"))

    # Сортировка по id посту и номера картинки из имени файла
    dumps.sort(key=lambda dump: (dump["post_id"], dump["photo_file_name"]))

    for dump in dumps:
        append_to_db(dump)

    for game in list(Game.select().where(Game.series.is_null())):
        game.series = GameSeries.get_unknown()
        game.save()

    BaseModel.print_count_of_tables()
    # Author: 165, Author2Cover: 607, Cover: 567, Game: 451, GameSeries: 200, TgChat: 2, TgUser: 2

    make_identical_authors_unique()
    # Renamed: 'DELETED' -> 'DELETED (id74388128)'
    # Renamed: 'DELETED' -> 'DELETED (id135225390)'
    # Renamed: 'DELETED' -> 'DELETED (id230625225)'
