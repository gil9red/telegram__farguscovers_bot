#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import time

from pathlib import Path
from typing import Type, Optional, List, Iterable, Union

# pip install peewee
from peewee import (
    Model, TextField, ForeignKeyField, CharField, DateTimeField, IntegerField, Field
)
from playhouse.sqliteq import SqliteQueueDatabase

from config import DB_FILE_NAME, DIR_DATA_VK, ITEMS_PER_PAGE
from bot.common import get_slug
from third_party.shorten import shorten


class NotDefinedParameterException(Exception):
    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name
        text = f'Parameter "{self.parameter_name}" must be defined!'

        super().__init__(text)


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

    @classmethod
    def get_first(cls) -> Type['BaseModel']:
        return cls.select().first()

    @classmethod
    def get_last(cls) -> Type['BaseModel']:
        return cls.select().order_by(cls.id.desc()).first()

    @classmethod
    def paginating(
            cls,
            page: int = 1,
            items_per_page: int = ITEMS_PER_PAGE,
            order_by: Field = None,
            filters: Iterable = None,
    ) -> List[Type['BaseModel']]:
        query = cls.select()

        if filters:
            query = query.filter(*filters)

        if order_by:
            query = query.order_by(order_by)

        query = query.paginate(page, items_per_page)
        return list(query)

    @classmethod
    def get_inherited_models(cls) -> List[Type['BaseModel']]:
        return sorted(cls.__subclasses__(), key=lambda x: x.__name__)

    @classmethod
    def print_count_of_tables(cls):
        items = []
        for sub_cls in cls.get_inherited_models():
            name = sub_cls.__name__
            count = sub_cls.select().count()
            items.append(f'{name}: {count}')

        print(', '.join(items))

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
        slug = get_slug(slug)  # Защита от произвольных строк

        if not slug or not slug.strip():
            raise NotDefinedParameterException(parameter_name='slug')

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional['GameSeries']:
        if not name or not name.strip():
            raise NotDefinedParameterException(parameter_name='name')

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
        slug = get_slug(slug)  # Защита от произвольных строк

        if not slug or not slug.strip():
            raise NotDefinedParameterException(parameter_name='slug')

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional['Game']:
        if not name or not name.strip():
            raise NotDefinedParameterException(parameter_name='name')

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
    text = TextField(null=False)
    file_name = TextField(unique=True)
    url_post = TextField()
    url_post_image = TextField()
    game = ForeignKeyField(Game, backref='covers')
    server_file_id = TextField(null=True)
    date_time = DateTimeField()

    @property
    def abs_file_name(self) -> Path:
        return DIR_DATA_VK / self.file_name

    @classmethod
    def get_by_page(
            cls,
            page: int = 1,
            by_author: Union[int, 'Author'] = None,
            by_game_series: Union[int, 'GameSeries'] = None,
            by_game: Union[int, 'Game'] = None,
            filters: Iterable = None,
    ) -> Optional['Cover']:
        total_filters = []

        if by_author is not None:
            total_filters.append(
                cls.id.in_(
                    # Из Author2Cover вернем cover_id по заданному автору
                    Author2Cover.select(Author2Cover.cover).where(Author2Cover.author == by_author)
                )
            )

        if by_game_series is not None:
            total_filters.append(
                cls.game.in_(
                    # Из Game вернем id по заданной серии игр
                    Game.select(Game.id).where(Game.series == by_game_series)
                )
            )

        if by_game is not None:
            total_filters.append(
                cls.game == by_game
            )

        if filters:
            total_filters.extend(filters)

        covers = cls.paginating(
            page=page,
            items_per_page=1,
            order_by=cls.id,
            filters=total_filters,
        )
        return covers[0] if covers else None

    def get_authors(self, reverse=False) -> List['Author']:
        items = [link.author for link in self.links_to_authors]
        items.sort(reverse=reverse, key=lambda x: x.id)
        return items


class Author(BaseModel):
    name = TextField()
    url = TextField(unique=True)

    @classmethod
    def add(cls, id: int, name: str, url: str = None) -> 'Author':
        if not url:
            url = f'https://vk.com/id{id}'

        obj = cls.get_or_none(id=id)
        if not obj:
            obj = cls.create(
                id=id,
                name=name,
                url=url,
            )

        return obj

    def get_covers(self, reverse=False) -> List[Cover]:
        items = [link.cover for link in self.links_to_covers]
        items.sort(reverse=reverse, key=lambda x: x.id)
        return items


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
db.create_tables(BaseModel.get_inherited_models())

# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)

if __name__ == '__main__':
    BaseModel.print_count_of_tables()
    # Author: 164, Author2Cover: 581, Cover: 567, Game: 451, GameSeries: 200, User: 0
    print()

    first = Cover.get_first()
    last = Cover.get_last()
    print(f'First cover date: {first.date_time if first else "-"}')
    print(f'Last cover date: {last.date_time if last else "-"}')
    # First cover date: 2012-08-08 00:43:29
    # Last cover date: 2020-03-17 20:00:05

    print()

    try:
        author = Author.get_by_id(57847587)
        print(f'{author}, covers:')
        for cover in author.get_covers():
            game = cover.game
            game_series = game.series
            game_series_title = game_series.name if game_series else "-"
            print(
                f'    Cover #{cover.id}, text: {cover.text!r}, game: {game.name!r}, game series: {game_series_title!r}'
            )
    except Exception as e:
        print(e)

    print()

    try:
        cover = Cover.get_by_id(1)
        print(cover)
        print(cover.get_authors())
    except Exception as e:
        print(e)
