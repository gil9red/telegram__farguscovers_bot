#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import datetime as DT
import time

from pathlib import Path
from typing import Type, Optional, Iterable, Union

# pip install peewee
from peewee import (
    Model,
    TextField,
    ForeignKeyField,
    CharField,
    DateTimeField,
    IntegerField,
    Field,
    fn,
)
import telegram

from config import DB_FILE_NAME, DIR_DATA_VK, ITEMS_PER_PAGE
from bot.common import get_slug
from bot.debug import SqliteQueueDatabaseDebug
from third_party.shorten import shorten


class NotDefinedParameterException(Exception):
    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name
        text = f'Parameter "{self.parameter_name}" must be defined!'

        super().__init__(text)


# This working with multithreading
# SOURCE: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#sqliteq
db = SqliteQueueDatabaseDebug(
    DB_FILE_NAME,
    pragmas={
        "foreign_keys": 1,
        "journal_mode": "wal",     # WAL-mode
        "cache_size": -1024 * 64,  # 64MB page-cache
    },
    use_gevent=False,     # Use the standard library "threading" module.
    autostart=True,
    queue_max_size=64,    # Max. # of pending writes that can accumulate.
    results_timeout=5.0   # Max. time to wait for query to be executed.
)


class BaseModel(Model):
    """
    Базовая модель классов-таблиц
    """

    class Meta:
        database = db

    def get_new(self) -> Type["BaseModel"]:
        return type(self).get(self._pk_expr())

    @classmethod
    def get_first(cls) -> Type["BaseModel"]:
        return cls.select().first()

    @classmethod
    def get_last(cls) -> Type["BaseModel"]:
        return cls.select().order_by(cls.id.desc()).first()

    @classmethod
    def paginating(
        cls,
        page: int = 1,
        items_per_page: int = ITEMS_PER_PAGE,
        order_by: Field = None,
        filters: Iterable = None,
    ) -> list[Type["BaseModel"]]:
        query = cls.select()

        if filters:
            query = query.filter(*filters)

        if order_by:
            query = query.order_by(order_by)

        query = query.paginate(page, items_per_page)
        return list(query)

    @classmethod
    def get_inherited_models(cls) -> list[Type["BaseModel"]]:
        return sorted(cls.__subclasses__(), key=lambda x: x.__name__)

    @classmethod
    def print_count_of_tables(cls):
        items = []
        for sub_cls in cls.get_inherited_models():
            name = sub_cls.__name__
            count = sub_cls.select().count()
            items.append(f"{name}: {count}")

        print(", ".join(items))

    @classmethod
    def count(cls, filters: Iterable = None) -> int:
        query = cls.select()
        if filters:
            query = query.filter(*filters)
        return query.count()

    def __str__(self):
        fields = []
        for k, field in self._meta.fields.items():
            v = getattr(self, k)

            if isinstance(field, (TextField, CharField)):
                if v:
                    v = repr(shorten(v))

            elif isinstance(field, ForeignKeyField):
                k = f"{k}_id"
                if v:
                    v = v.id

            fields.append(f"{k}={v}")

        return self.__class__.__name__ + "(" + ", ".join(fields) + ")"


class GameSeries(BaseModel):
    name = TextField()
    slug = TextField(unique=True)

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional["GameSeries"]:
        slug = get_slug(slug)  # Защита от произвольных строк

        if not slug or not slug.strip():
            raise NotDefinedParameterException(parameter_name="slug")

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional["GameSeries"]:
        if not name or not name.strip():
            raise NotDefinedParameterException(parameter_name="name")

        return cls.get_by_slug(slug=get_slug(name))

    @classmethod
    def add(cls, name: str, id: int = None) -> "GameSeries":
        obj = cls.get_by(name)
        if not obj:
            obj = cls.create(
                id=id,
                name=name,
                slug=get_slug(name),
            )

        return obj

    @classmethod
    def get_unknown(cls) -> "GameSeries":
        return cls.add(name="<Без серии>", id=0)

    @classmethod
    def get_filters(
        cls,
        by_author: Union[int, "Author"] = None,
        filters: Iterable = None,
    ) -> list:
        total_filters = []

        if by_author is not None:
            cover_ids = Author2Cover.select(Author2Cover.cover).where(Author2Cover.author == by_author)
            game_ids = Cover.select(Cover.game).distinct().where(Cover.id.in_(cover_ids))
            game_series_ids = Game.select(Game.series).distinct().where(Game.id.in_(game_ids))
            total_filters.append(
                cls.id.in_(game_series_ids)
            )

        if filters:
            total_filters.extend(filters)

        return total_filters

    def get_authors(self) -> list["Author"]:
        game_ids = Game.select(Game.id).where(Game.series == self)
        cover_ids = Cover.select(Cover.id).where(Cover.game.in_(game_ids))
        query = (
            Author2Cover.select(Author2Cover.author)
            .distinct()
            .where(Author2Cover.cover.in_(cover_ids))
        )
        return [a2c.author for a2c in query]

    def get_number_of_authors(self) -> int:
        return len(self.get_authors())

    def get_games(self) -> list["Game"]:
        return list(self.games)

    def get_number_of_games(self) -> int:
        return len(self.get_games())

    def get_number_of_covers(self) -> int:
        return Cover.count_by(by_game_series=self)


class Game(BaseModel):
    name = TextField()
    slug = TextField(unique=True)
    series = ForeignKeyField(GameSeries, backref="games", null=True)

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional["Game"]:
        slug = get_slug(slug)  # Защита от произвольных строк

        if not slug or not slug.strip():
            raise NotDefinedParameterException(parameter_name="slug")

        return cls.get_or_none(slug=slug)

    @classmethod
    def get_by(cls, name: str) -> Optional["Game"]:
        if not name or not name.strip():
            raise NotDefinedParameterException(parameter_name="name")

        return cls.get_by_slug(slug=get_slug(name))

    @classmethod
    def add(cls, name: str, series: GameSeries = None) -> "Game":
        obj = cls.get_by(name)
        if not obj:
            obj = cls.create(
                name=name,
                slug=get_slug(name),
                series=series,
            )

        return obj

    @classmethod
    def get_filters(
        cls,
        by_author: Union[int, "Author"] = None,
        by_game_series: Union[int, "GameSeries"] = None,
        filters: Iterable = None,
    ) -> list:
        total_filters = []

        if by_author is not None:
            cover_ids = Author2Cover.select(Author2Cover.cover).where(Author2Cover.author == by_author)
            game_ids = Cover.select(Cover.game).distinct().where(Cover.id.in_(cover_ids))
            total_filters.append(
                cls.id.in_(game_ids)
            )

        if by_game_series is not None:
            total_filters.append(
                cls.series == by_game_series
            )

        if filters:
            total_filters.extend(filters)

        return total_filters

    @property
    def series_name(self) -> str:
        return self.series.name if self.series else ""

    def get_authors(self) -> list["Author"]:
        cover_ids = Cover.select(Cover.id).where(Cover.game == self)
        query = (
            Author2Cover.select(Author2Cover.author)
            .distinct()
            .where(Author2Cover.cover.in_(cover_ids))
        )
        return [a2c.author for a2c in query]

    def get_number_of_authors(self) -> int:
        return len(self.get_authors())

    def get_number_of_covers(self) -> int:
        return Cover.count_by(by_game=self)


class Cover(BaseModel):
    text = TextField(null=False)
    file_name = TextField(unique=True)
    url_post = TextField()
    url_post_image = TextField()
    game = ForeignKeyField(Game, backref="covers")
    server_file_id = TextField(null=True)
    date_time = DateTimeField()

    @property
    def abs_file_name(self) -> Path:
        return DIR_DATA_VK / self.file_name

    @classmethod
    def get_filters(
        cls,
        by_author: Union[int, "Author"] = None,
        by_game_series: Union[int, "GameSeries"] = None,
        by_game: Union[int, "Game"] = None,
        filters: Iterable = None,
    ) -> list:
        total_filters = []

        if by_author is not None:
            total_filters.append(
                cls.id.in_(
                    # Из Author2Cover вернем cover_id по заданному автору
                    Author2Cover.select(Author2Cover.cover).where(
                        Author2Cover.author == by_author
                    )
                )
            )

        if by_game_series is not None:
            total_filters.append(
                cls.game.in_(
                    # Из Game вернем id по заданной серии игр
                    Game.select(Game.id)
                    .distinct()
                    .where(Game.series == by_game_series)
                )
            )

        if by_game is not None:
            total_filters.append(
                cls.game == by_game
            )

        if filters:
            total_filters.extend(filters)

        return total_filters

    @classmethod
    def count_by(
        cls,
        by_author: Union[int, "Author"] = None,
        by_game_series: Union[int, "GameSeries"] = None,
        by_game: Union[int, "Game"] = None,
        filters: Iterable = None,
    ) -> int:
        total_filters = cls.get_filters(
            by_author=by_author,
            by_game_series=by_game_series,
            by_game=by_game,
            filters=filters,
        )
        return cls.count(total_filters)

    @classmethod
    def get_by_page(
        cls,
        page: int = 1,
        by_author: Union[int, "Author"] = None,
        by_game_series: Union[int, "GameSeries"] = None,
        by_game: Union[int, "Game"] = None,
        filters: Iterable = None,
    ) -> Optional["Cover"]:
        total_filters = cls.get_filters(
            by_author=by_author,
            by_game_series=by_game_series,
            by_game=by_game,
            filters=filters,
        )

        covers = cls.paginating(
            page=page,
            items_per_page=1,
            order_by=cls.date_time,
            filters=total_filters,
        )
        return covers[0] if covers else None

    @classmethod
    def get_page(
        cls,
        need_cover_id: int,
        by_author: Union[int, "Author"] = None,
        by_game_series: Union[int, "GameSeries"] = None,
        by_game: Union[int, "Game"] = None,
        filters: Iterable = None,
    ) -> int:
        total_filters = cls.get_filters(
            by_author=by_author,
            by_game_series=by_game_series,
            by_game=by_game,
            filters=filters,
        )
        query = cls.select(
            fn.row_number().over(order_by=[cls.date_time]).alias("page"),
            cls.id
        )
        if total_filters:
            query = query.where(*total_filters)
        query = query.order_by(cls.date_time)

        for page, cover_id in query.tuples():
            if cover_id == need_cover_id:
                return page

        raise Exception(
            f"Не удалось определить номер для #{need_cover_id} по {total_filters}"
        )

    def get_authors(self, reverse=False) -> list["Author"]:
        items = []
        for link in self.links_to_authors:
            author = link.author
            if author not in items:
                items.append(author)
        items.sort(reverse=reverse, key=lambda x: x.id)
        return items

    @classmethod
    def find(cls, text: str) -> list["Cover"]:
        items = []
        if not text:
            return items

        # NOTE: Элементов в базе мало, поэтому эта реализация работает быстро,
        #       но, конечно, лучше если поиск будет идти через саму базу
        #       Нужно помнить, что в SQLITE поиск через LIKE не регистро-независимый для
        #       не-ASCII, туда же идет и работа функций UPPER и LOWER
        for cover in cls.select():
            full_text = (
                cover.text
                + cover.game.name
                + cover.game.series_name
                + "".join(a.name for a in cover.get_authors())
            )
            if text.upper() in full_text.upper():
                items.append(cover)

        return items


class Author(BaseModel):
    name = TextField()
    url = TextField(unique=True)

    @classmethod
    def add(cls, id: int, name: str, url: str = None) -> "Author":
        if not url:
            url = f"https://vk.com/id{id}"

        obj = cls.get_or_none(id=id)
        if not obj:
            obj = cls.create(
                id=id,
                name=name,
                url=url,
            )

        return obj

    @classmethod
    def get_filters(
        cls,
        by_game_series: Union[int, "GameSeries"] = None,
        by_game: Union[int, "Game"] = None,
        filters: Iterable = None,
    ) -> list:
        total_filters = []

        if by_game_series is not None:
            game_ids = Game.select(Game.id).distinct().where(Game.series == by_game_series)
            cover_ids = Cover.select(Cover.id).where(Cover.game.in_(game_ids))
            author_ids = Author2Cover.select(Author2Cover.author).distinct().where(Author2Cover.cover.in_(cover_ids))
            total_filters.append(
                cls.id.in_(author_ids)
            )

        if by_game is not None:
            cover_ids = Cover.select(Cover.id).where(Cover.game == by_game)
            author_ids = (
                Author2Cover.select(Author2Cover.author)
                .distinct()
                .where(Author2Cover.cover.in_(cover_ids))
            )
            total_filters.append(
                cls.id.in_(author_ids)
            )

        if filters:
            total_filters.extend(filters)

        return total_filters

    def get_covers(self, reverse=False) -> list[Cover]:
        items = [link.cover for link in self.links_to_covers]
        items.sort(reverse=reverse, key=lambda x: x.id)
        return items

    def get_number_of_covers(self) -> int:
        return Cover.count_by(by_author=self)

    def get_games(self) -> list[Game]:
        items = []
        for link in self.links_to_covers:
            game = link.cover.game
            if game not in items:
                items.append(game)

        return items

    def get_number_of_games(self) -> int:
        return len(self.get_games())

    def get_game_series(self) -> list[GameSeries]:
        items = []
        for link in self.links_to_covers:
            series = link.cover.game.series
            if series not in items:
                items.append(series)

        return items

    def get_number_of_game_series(self) -> int:
        return len(self.get_game_series())


class Author2Cover(BaseModel):
    author = ForeignKeyField(Author, backref="links_to_covers")
    cover = ForeignKeyField(Cover, backref="links_to_authors")

    class Meta:
        indexes = (
            (("author", "cover"), True),
        )


class TgUser(BaseModel):
    first_name = TextField()
    last_name = TextField(null=True)
    username = TextField(null=True)
    language_code = TextField(null=True)
    last_activity = DateTimeField(default=DT.datetime.now)
    number_requests = IntegerField(default=0)

    @classmethod
    def add(
        cls,
        id: int,
        first_name: str,
        last_name: str = None,
        username: str = None,
        language_code: str = None,
    ) -> "TgUser":
        obj = cls.get_or_none(cls.id == id)
        if not obj:
            obj = cls.create(
                id=id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                language_code=language_code,
            )

        return obj

    @classmethod
    def get_from(cls, user: Optional[telegram.User]) -> Optional["TgUser"]:
        if not user:
            return

        return cls.add(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        )

    def actualize(self, user: Optional[telegram.User], inc_number_requests=True):
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.username = user.username
        self.language_code = user.language_code
        self.last_activity = DT.datetime.now()

        self.save()

        if inc_number_requests:
            self.inc_number_requests()

    def inc_number_requests(self):
        cls = type(self)
        query = self.update(number_requests=cls.number_requests + 1).where(
            cls.id == self.id
        )
        query.execute()


# SOURCE: https://core.telegram.org/bots/api#chat
class TgChat(BaseModel):
    type = TextField()
    title = TextField(null=True)
    username = TextField(null=True)
    first_name = TextField(null=True)
    last_name = TextField(null=True)
    description = TextField(null=True)
    last_activity = DateTimeField(default=DT.datetime.now)
    number_requests = IntegerField(default=0)

    @classmethod
    def add(
        cls,
        id: int,
        type: str = None,
        title: str = None,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        description: str = None,
    ) -> "TgChat":
        obj = cls.get_or_none(cls.id == id)
        if not obj:
            obj = cls.create(
                id=id,
                type=type,
                title=title,
                username=username,
                first_name=first_name,
                last_name=last_name,
                description=description,
            )

        return obj

    @classmethod
    def get_from(cls, chat: Optional[telegram.Chat]) -> Optional["TgChat"]:
        if not chat:
            return

        return cls.add(
            id=chat.id,
            type=chat.type,
            title=chat.title,
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
            description=chat.description,
        )

    def actualize(self, chat: Optional[telegram.Chat], inc_number_requests=True):
        self.type = chat.type
        self.title = chat.title
        self.username = chat.username
        self.first_name = chat.first_name
        self.last_name = chat.last_name
        self.description = chat.description
        self.last_activity = DT.datetime.now()

        self.save()

        if inc_number_requests:
            self.inc_number_requests()

    def inc_number_requests(self):
        cls = type(self)
        query = self.update(number_requests=cls.number_requests + 1).where(
            cls.id == self.id
        )
        query.execute()

    def is_first_request(self) -> bool:
        return self.number_requests in (0, 1)


db.connect()
db.create_tables(BaseModel.get_inherited_models())

# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)

if __name__ == "__main__":
    BaseModel.print_count_of_tables()
    # Author: 165, Author2Cover: 607, Cover: 567, Game: 451, GameSeries: 200, TgChat: 16, TgUser: 16
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
        print(f"{author}, covers:")
        for cover in author.get_covers():
            game = cover.game
            print(
                f"    Cover #{cover.id}, text: {cover.text!r}, game: {game.name!r}, game series: {game.series.name!r}"
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

    print()
    print(
        Cover.count_by(
            by_author=57847587,
            by_game_series=GameSeries.get_by("Mafia"),
            by_game=Game.get_by("Mafia 2"),
        )
    )

    print()
    print(Game.select().where(Game.series.is_null()).count())
