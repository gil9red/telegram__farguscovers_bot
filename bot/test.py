#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import contextlib
from typing import Type, Iterable, List

from peewee import Field

from bot import regexp_patterns
from db import GameSeries, Game, Author, Cover, BaseModel, NotDefinedParameterException
from third_party.regexp import fill_string_pattern


# SOURCE: https://stackoverflow.com/a/23780046/5909792
@contextlib.contextmanager
def assert_exception(exception: Type[BaseException]):
    try:
        yield
    except exception:
        assert True
    else:
        assert False


def test_paginating(model: Type[BaseModel], order_by: Field = None, filters: Iterable = None):
    paginate_by_part = 3
    paginate_by_full = 9

    if not order_by:
        order_by = model.id
    
    objs_full = model.paginating(page=1, items_per_page=paginate_by_full, order_by=order_by, filters=filters)
    assert len(objs_full) == paginate_by_full

    objs_page1 = model.paginating(page=1, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
    assert len(objs_page1) == paginate_by_part
    assert objs_full[:3] == objs_page1

    objs_page2 = model.paginating(page=2, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
    assert len(objs_page2) == paginate_by_part
    assert objs_full[3:6] == objs_page2

    objs_page3 = model.paginating(page=3, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
    assert len(objs_page3) == paginate_by_part
    assert objs_full[6:] == objs_page3


def test_regexp_patterns(debug=False):
    max_page = 999
    max_id = 999_999_999_999
    max_callback_data_size = 64

    for name, value in vars(regexp_patterns).items():
        if name.startswith('PATTERN_PAGE_'):
            debug and print(f'{name} = {value}')

            callback_data_value = fill_string_pattern(value, max_page, max_id)
            size_callback_data = len(bytes(callback_data_value, "utf-8"))

            debug and print(f'    Size {size_callback_data} of {callback_data_value!r}')

            assert size_callback_data <= max_callback_data_size, \
                f"Превышение размера callback_data для {name!r}. Размер: {size_callback_data}"

            debug and print()


def test_get_by_page_of_cover():
    def _get_items(page: int = 1, **kwargs) -> List[Cover]:
        items = []

        while cover := Cover.get_by_page(page=page, **kwargs):
            page += 1
            items.append(cover)

        return items

    assert Cover.get_by_page(page=1) == Cover.get_first()

    assert Cover.get_by_page(page=999999) is None
    assert not Cover.get_by_page(page=999999)
    items = _get_items(page=999999)
    assert not items
    assert len(items) == 0

    author_id = 3917270
    author = Author.get_by_id(author_id)
    items = _get_items(by_author=author_id)
    assert items
    assert items == _get_items(by_author=author)
    assert Cover.get_by_page(page=1, by_author=author_id) == author.get_covers()[0]
    assert Cover.get_by_page(page=1, by_author=author) == author.get_covers()[0]
    assert not _get_items(by_author=author_id, filters=[Cover.id == -1])  # Невыполнимое условие

    game_series_id = 26
    game_series = GameSeries.get_by_id(game_series_id)
    items = _get_items(by_game_series=game_series_id)
    assert items
    assert items == _get_items(by_game_series=game_series)
    assert not _get_items(by_game_series=author_id, filters=[Cover.id == -1])  # Невыполнимое условие

    game_id = 32
    game = GameSeries.get_by_id(game_id)
    items = _get_items(by_game=game_id)
    assert items
    assert items == _get_items(by_game=game)
    assert not _get_items(by_game=author_id, filters=[Cover.id == -1])  # Невыполнимое условие


def test_get_by_on_exception():
    # Проверка, что указанные методы при заданных значениях выбросят ValueError
    for func in [GameSeries.get_by, Game.get_by, GameSeries.get_by_slug, Game.get_by_slug]:
        for value in ['', '    ', ' ! ', None]:
            try:
                with assert_exception(NotDefinedParameterException):
                    func(value)
            except AssertionError:
                print(f'Invalid test for {func} for {value!r}')
                raise


def test_game_get_by_on_valid():
    game_by_name = Game.get_by('Max Payne 2: The Fall of Max Payne')
    assert game_by_name

    game_by_id = Game.get_by_id(game_by_name.id)
    assert game_by_id

    game_by_slug = Game.get_by_slug(game_by_name.slug)
    assert game_by_slug

    assert game_by_name == game_by_id
    assert game_by_name == game_by_slug


def test_game_series_get_by_on_valid():
    game_series_by_name = GameSeries.get_by('Warhammer 40,000')
    assert game_series_by_name

    game_series_by_id = GameSeries.get_by_id(game_series_by_name.id)
    assert game_series_by_id

    game_series_by_slug = GameSeries.get_by_slug(game_series_by_name.slug)
    assert game_series_by_slug

    assert game_series_by_name == game_series_by_id
    assert game_series_by_name == game_series_by_slug


if __name__ == '__main__':
    test_regexp_patterns()

    test_get_by_on_exception()
    test_game_series_get_by_on_valid()
    test_game_get_by_on_valid()

    assert Cover.get_first() == Cover.get_by_id(1)
    assert Cover.get_first().id == Cover.get_by_id(1).id
    assert Cover.get_last() == list(Cover.select().order_by(Cover.id.desc()))[0]
    assert Cover.get_last().id == list(Cover.select().order_by(Cover.id.desc()))[0].id

    test_paginating(Author)
    filters = [Author.name.startswith('Макс')]
    test_paginating(Author, filters=filters)
    test_paginating(Author, order_by=Author.id.desc(), filters=filters)

    test_paginating(GameSeries)
    filters = [GameSeries.name.startswith('A')]
    test_paginating(GameSeries, filters=filters)
    test_paginating(GameSeries, order_by=GameSeries.id.desc(), filters=filters)

    test_paginating(Game)
    filters = [Game.name.startswith('A'), Game.slug.startswith('a')]
    test_paginating(Game, filters=filters)
    test_paginating(Game, order_by=Game.id.desc(), filters=filters)

    test_paginating(Cover)
    # Фильтр обложек по играм "Grand Theft Auto"
    filters = [
        Cover.game.in_(
            Game.select().filter(
                Game.name.contains('Grand Theft Auto')
            )
        )
    ]
    test_paginating(Cover, filters=filters)
    test_paginating(Cover, order_by=Cover.id.desc(), filters=filters)

    cover = Cover.get_by_id(1)
    assert cover.date_time
    assert cover.abs_file_name.exists()
    assert cover.get_authors()
    assert cover.get_authors()[0]
    assert cover.get_authors()[0].get_covers()
    assert cover.get_authors()[0].get_covers() == cover.get_authors()[0].get_covers(reverse=True)[::-1]
    assert cover.get_authors()[0].get_covers()[::-1] == cover.get_authors()[0].get_covers(reverse=True)

    test_get_by_page_of_cover()
