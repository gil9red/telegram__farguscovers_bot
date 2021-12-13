#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time
import datetime as DT

from pathlib import Path
from typing import Type, Optional

# pip install peewee
from peewee import (
    Model, TextField, ForeignKeyField, CharField, DateTimeField, IntegerField
)
from playhouse.sqliteq import SqliteQueueDatabase

from config import DB_FILE_NAME, DIR_DATA_VK
from bot.common import get_slug
from third_party.shorten import shorten


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
    name = TextField()
    slug = TextField(unique=True)

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional['GameSeries']:
        if not slug or not slug.strip():
            raise ValueError('Parameter "slug" must be defined!')

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional['GameSeries']:
        if not name or not name.strip():
            raise ValueError('Parameter "name" must be defined!')

        return cls.get_by_slug(slug=get_slug(name))

    @classmethod
    def add(cls, name: str) -> 'GameSeries':
        obj = cls.get_by(name)
        if not obj:
            obj = cls.create(
                name=name,
                slug=get_slug(name),
            )

        return obj


class Game(BaseModel):
    name = TextField()
    slug = TextField(unique=True)
    series = ForeignKeyField(GameSeries, backref='games', null=True)

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional['Game']:
        if not slug or not slug.strip():
            raise ValueError('Parameter "slug" must be defined!')

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional['Game']:
        if not name or not name.strip():
            raise ValueError('Parameter "name" must be defined!')

        return cls.get_by_slug(slug=get_slug(name))

    @classmethod
    def add(cls, name: str, series: GameSeries = None) -> 'Game':
        obj = cls.get_by(name)
        if not obj:
            obj = cls.create(
                name=name,
                slug=get_slug(name),
                series=series,
            )

        return obj

    @property
    def series_name(self) -> str:
        return self.series.name if self.series else ""


class Cover(BaseModel):
    text = TextField()
    file_name = TextField(unique=True)
    url_post = TextField()
    url_post_image = TextField()
    game = ForeignKeyField(Game, backref='covers')
    server_file_id = TextField(null=True)
    date_time = DateTimeField()

    @property
    def abs_file_name(self) -> Path:
        return DIR_DATA_VK / self.file_name


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
    # Проверка, что указанные методы при заданных значениях выбросят ValueError
    from bot.common import assert_exception
    for func in [GameSeries.get_by, Game.get_by]:
        for value in ['', '    ', ' ! ', None]:
            try:
                with assert_exception(ValueError):
                    func(value)
            except AssertionError:
                print(f'Invalid test for {func} for {value!r}')
                raise

    # TODO: вывести статистику по кол-ву: авторов, игр, серий, обложек
    #       взять из fill_db.py

    # TODO: вывести первую и последнюю обложку с указанием даты
    print(Cover.select().first().date_time)
    print(Cover.select().order_by(Cover.id.desc()).first().date_time)
    print()

    author = Author.get_by_id(57847587)
    print(author)
    # TODO: добавить в Author метод для получения обложек
    # TODO: добавить в Cover метод для получения авторов
    # TODO: добавить пример вывода авторов из конкретной обложки
    for link in author.links_to_covers:
        print(f'    Cover: {link.cover}')
        print(f'    Game: {link.cover.game}')
        print(f'    Series: {link.cover.game.series}')
        print()

    print()

    cover = Cover.get_by_id(1)
    print(cover)
    print(type(cover.date_time), cover.date_time, cover.date_time.date())
    print(cover.abs_file_name.exists(), cover.abs_file_name)
