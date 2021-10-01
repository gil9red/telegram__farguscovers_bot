#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time
import datetime as DT
from pathlib import Path
from typing import Type

# pip install peewee
from peewee import (
    Model, TextField, ForeignKeyField, CharField, DateTimeField, IntegerField
)
from playhouse.sqliteq import SqliteQueueDatabase

from config import DB_FILE_NAME, DIR
from common import shorten


# This working with multithreading
# SOURCE: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#sqliteq
db = SqliteQueueDatabase(
    DB_FILE_NAME,
    pragmas={
        'foreign_keys': 1,
        'journal_mode': 'wal',    # WAL-mode
        'cache_size': -1024 * 64  # 64MB page-cache
    },
    use_gevent=False,     # Use the standard library "threading" module.
    autostart=True,
    queue_max_size=64,    # Max. # of pending writes that can accumulate.
    results_timeout=5.0   # Max. time to wait for query to be executed.
)


class BaseModel(Model):
    """
    Базовая модель для классов-таблиц
    """

    class Meta:
        database = db

    def get_new(self) -> Type['BaseModel']:
        return type(self).get(self._pk_expr())

    def __str__(self):
        fields = []
        for k, field in self._meta.fields.items():
            v = getattr(self, k)

            if isinstance(field, (TextField, CharField)):
                if v:
                    v = repr(shorten(v))

            elif isinstance(field, ForeignKeyField):
                k = f'{k}_id'
                if v:
                    v = v.id

            fields.append(f'{k}={v}')

        return self.__class__.__name__ + '(' + ', '.join(fields) + ')'


class GameSeries(BaseModel):
    name = TextField(unique=True)


class Game(BaseModel):
    name = TextField(unique=True)
    series = ForeignKeyField(GameSeries, backref='games', null=True)

    @property
    def series_name(self) -> str:
        return self.series.name if self.series else ""


class Cover(BaseModel):
    text = TextField()
    file_name = TextField(unique=True)
    url_post = TextField()
    url_post_image = TextField()
    game = ForeignKeyField(Game, backref='covers')

    @property
    def abs_file_name(self) -> Path:
        return DIR / self.file_name


class Author(BaseModel):
    name = TextField()

    @property
    def url(self) -> str:
        return f'https://vk.com/id{self.id}'


class Author2Cover(BaseModel):
    author = ForeignKeyField(Author, backref='links_to_covers')
    cover = ForeignKeyField(Cover, backref='links_to_authors')

    class Meta:
        indexes = (
            (('author', 'cover'), True),
        )


class User(BaseModel):
    first_name = TextField()
    last_name = TextField(null=True)
    username = TextField(null=True)
    language_code = TextField(null=True)
    last_activity = DateTimeField(default=DT.datetime.now)
    number_requests = IntegerField(default=0)


db.connect()
db.create_tables([GameSeries, Game, Cover, Author, Author2Cover, User])

# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)

if __name__ == '__main__':
    dumps = [
        {
            "post_id": 657,
            "post_url": "https://vk.com/farguscovers?w=wall-41666750_657",
            "post_text": "Автор идеи: [id57847587|Василий Промтов]",
            "photo_file_name": "images\\657_1.jpg",
            "photo_post_url": "https://vk.com/farguscovers?z=photo-41666750_287333392%2Fwall-41666750_657",
            "authors": [
                {
                    "id": 57847587,
                    "name": "Василий Промтов"
                }
            ],
            "cover_text": "Лето в гетто: Город Св. Андрея",
            "game_name": "Grand Theft Auto: San Andreas",
            "game_series": "Grand Theft Auto"
        }
    ]
    for dump in dumps:
        series = dump["game_series"]
        if series:
            game_series = GameSeries.get_or_none(name=series)
            if not game_series:
                game_series = GameSeries.create(name=series)
        else:
            game_series = None

        name = dump["game_name"]
        game = Game.get_or_none(name=name)
        if not game:
            game = Game.create(name=name, series=game_series)

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

            cover = Cover.create(
                text=cover_text,
                file_name=cover_file_name,
                url_post=cover_post_url,
                url_post_image=cover_photo_post_url,
                game=game
            )

        print(game)
        print(series)
        print(authors)
        print(cover)

        for author in authors:
            link = Author2Cover.get_or_none(author=author, cover=cover)
            if not link:
                link = Author2Cover.create(author=author, cover=cover)

            print(link)

    # series_sims = GameSeries.get(name="The Sims")
    # print(series_sims.id)
    # print(list(series_sims.games))
    # print(series_sims.games)
    # print()
    # for dump in series_sims.games:
    #     print(dump.name, dump.series.name)
    #
    # print("-"*10)
    #
    # for dump in Game.select():
    #     series = ""
    #     if dump.series is not None:
    #         series = dump.series.name
    #     print(dump.name, series, dump.series_name, sep=" | ")


