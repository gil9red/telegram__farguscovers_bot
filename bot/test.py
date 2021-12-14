#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import contextlib
from typing import Type, Iterable

from db import GameSeries, Game, Author, Cover, BaseModel, NotDefinedParameterException
from peewee import Field


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


if __name__ == '__main__':
    # Проверка, что указанные методы при заданных значениях выбросят ValueError
    for func in [GameSeries.get_by, Game.get_by, GameSeries.get_by_slug, Game.get_by_slug]:
        for value in ['', '    ', ' ! ', None]:
            try:
                with assert_exception(NotDefinedParameterException):
                    func(value)
            except AssertionError:
                print(f'Invalid test for {func} for {value!r}')
                raise

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
