#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import re
import unittest
from typing import Type, Iterable, List

from peewee import Field

from bot import regexp_patterns as P
from config import DEFAULT_AUTHOR_ID
from bot.db import GameSeries, Game, Author, Cover, BaseModel, NotDefinedParameterException


DEBUG = False


class TestRegexpPatterns(unittest.TestCase):
    MAX_PAGE = 9999
    MAX_ID = 999_999_999_999
    MAX_ID_DB = 999_999  # Для текущих объект в базе
    MAX_MESSAGE_ID = 99_999_999_999
    MAX_DATA_SIZE = 64

    def do_check_callback_data_value(self, pattern, *args):
        callback_data_value = P.fill_string_pattern(pattern, *args)

        size_callback_data = len(bytes(callback_data_value, "utf-8"))
        DEBUG and print(f'    Size {size_callback_data} of {callback_data_value!r}\n')
        self.assertTrue(
            size_callback_data <= self.MAX_DATA_SIZE,
            f"Превышение размера callback_data для {pattern}. Размер: {size_callback_data}"
        )

    def test_reply(self):
        for name, pattern in vars(P).items():
            if 'REPLY' not in name or not isinstance(pattern, re.Pattern):
                continue

            self.assertTrue(
                P.fill_string_pattern(
                    pattern,
                    self.MAX_ID  # Только для PATTERN_REPLY_COVER_BY_PAGE
                )
            )

    def test_pattern_authors_page(self):
        with self.subTest('Nulls'):
            self.assertEqual(
                'authors page=1 gs# g#',
                P.fill_string_pattern(P.PATTERN_AUTHORS_PAGE, 1, None, None)
            )
            self.assertEqual(
                'authors new page=1 gs# g#',
                P.fill_string_pattern(P.PATTERN_AUTHORS_NEW_PAGE, 1, None, None)
            )

        with self.subTest('Max'):
            for pattern in (P.PATTERN_AUTHORS_PAGE, P.PATTERN_AUTHORS_NEW_PAGE):
                self.do_check_callback_data_value(
                    pattern,
                    self.MAX_PAGE, self.MAX_ID_DB, self.MAX_ID_DB
                )

    def test_pattern_cover_page(self):
        with self.subTest('Nulls'):
            self.assertEqual(
                'covers page=1 a# gs# g#',
                P.fill_string_pattern(P.PATTERN_COVER_PAGE, 1, None, None, None)
            )
            self.assertEqual(
                'covers new page=1 a# gs# g#',
                P.fill_string_pattern(P.PATTERN_COVER_NEW_PAGE, 1, None, None, None)
            )

        with self.subTest('Max'):
            for pattern in (P.PATTERN_COVER_PAGE, P.PATTERN_COVER_NEW_PAGE):
                self.do_check_callback_data_value(
                    pattern,
                    self.MAX_PAGE, self.MAX_ID, self.MAX_ID_DB, self.MAX_ID_DB
                )

    def test_pattern_game_series_page(self):
        with self.subTest('Nulls'):
            self.assertEqual(
                'game series page=1 a#',
                P.fill_string_pattern(P.PATTERN_GAME_SERIES_PAGE, 1, None)
            )
            self.assertEqual(
                'game series new page=1 a#',
                P.fill_string_pattern(P.PATTERN_GAME_SERIES_NEW_PAGE, 1, None)
            )

        with self.subTest('Max'):
            for pattern in (P.PATTERN_GAME_SERIES_PAGE, P.PATTERN_GAME_SERIES_NEW_PAGE):
                self.do_check_callback_data_value(
                    pattern,
                    self.MAX_PAGE, self.MAX_ID
                )

    def test_pattern_game_series_new_card(self):
        pattern = P.PATTERN_GAME_SERIES_NEW_CARD
        self.do_check_callback_data_value(
            pattern, self.MAX_ID_DB
        )

    def test_pattern_games_page(self):
        with self.subTest('Nulls'):
            self.assertEqual(
                'games page=1 a# gs#',
                P.fill_string_pattern(P.PATTERN_GAMES_PAGE, 1, None, None)
            )
            self.assertEqual(
                'games new page=1 a# gs#',
                P.fill_string_pattern(P.PATTERN_GAMES_NEW_PAGE, 1, None, None)
            )

        with self.subTest('Max'):
            for pattern in (P.PATTERN_GAMES_PAGE, P.PATTERN_GAMES_NEW_PAGE):
                self.do_check_callback_data_value(
                    pattern,
                    self.MAX_PAGE, self.MAX_ID, self.MAX_ID_DB
                )

    def test_pattern_start_argument(self):
        self.do_check_callback_data_value(
            P.PATTERN_START_ARGUMENT,
            GameSeries.__name__, self.MAX_ID_DB, self.MAX_ID, self.MAX_ID, self.MAX_ID
        )


class TestDb(unittest.TestCase):
    def test_get_by_raises_exception(self):
        # Проверка, что указанные методы при заданных значениях выбросят ValueError
        for func in [GameSeries.get_by, Game.get_by, GameSeries.get_by_slug, Game.get_by_slug]:
            for value in ['', '    ', ' ! ', None]:
                with self.subTest(func=func, value=value):
                    with self.assertRaises(NotDefinedParameterException):
                        func(value)

    def test_get_by(self):
        for cls, name in [
            (GameSeries, 'Warhammer 40,000'),
            (Game, 'Max Payne 2: The Fall of Max Payne'),
        ]:
            with self.subTest(cls=cls, name=name):
                obj_by_name = cls.get_by(name)
                self.assertTrue(obj_by_name)

                obj_by_id = cls.get_by_id(obj_by_name.id)
                self.assertTrue(obj_by_id)

                obj_by_slug = cls.get_by_slug(obj_by_name.slug)
                self.assertTrue(obj_by_slug)

                self.assertEqual(obj_by_name, obj_by_id)
                self.assertEqual(obj_by_name, obj_by_slug)

    def test_get_first(self):
        for cls in BaseModel.get_inherited_models():
            with self.subTest(name=cls.__name__):
                items = list(cls.select().order_by(cls.id))
                assert cls.get_first() == (items[0] if items else None)

    def test_get_last(self):
        for cls in BaseModel.get_inherited_models():
            with self.subTest(name=cls.__name__):
                items = list(cls.select().order_by(cls.id))
                assert cls.get_last() == (items[-1] if items else None)


class TestDbPaginating(unittest.TestCase):
    def _utils_test_paginating(self, model: Type[BaseModel], order_by: Field = None, filters: Iterable = None):
        paginate_by_part = 3
        paginate_by_full = 9

        if not order_by:
            order_by = model.id

        objs_full = model.paginating(page=1, items_per_page=paginate_by_full, order_by=order_by, filters=filters)
        self.assertEqual(len(objs_full), paginate_by_full)

        objs_page1 = model.paginating(page=1, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
        self.assertEqual(len(objs_page1), paginate_by_part)
        self.assertEqual(objs_full[:3], objs_page1)

        objs_page2 = model.paginating(page=2, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
        self.assertEqual(len(objs_page2), paginate_by_part)
        self.assertEqual(objs_full[3:6], objs_page2)

        objs_page3 = model.paginating(page=3, items_per_page=paginate_by_part, order_by=order_by, filters=filters)
        self.assertEqual(len(objs_page3), paginate_by_part)
        self.assertEqual(objs_full[6:], objs_page3)

    def _utils_run_testing_for(self, model: Type[BaseModel], filters: Iterable):
        with self.subTest(msg='Default', model=model):
            self._utils_test_paginating(model)

        with self.subTest(msg='With filters', model=model):
            self._utils_test_paginating(model, filters=filters)

        with self.subTest(msg='With reverse', model=model):
            self._utils_test_paginating(model, order_by=model.id.desc())

        with self.subTest(msg='With filters + reverse', model=model):
            self._utils_test_paginating(model, order_by=model.id.desc(), filters=filters)

    def test_paginating_Author(self):
        filters = [Author.name.startswith('Макс')]
        self._utils_run_testing_for(Author, filters)

    def test_paginating_GameSeries(self):
        filters = [GameSeries.name.startswith('A')]
        self._utils_run_testing_for(GameSeries, filters)

    def test_paginating_Game(self):
        filters = [Game.name.startswith('A'), Game.slug.startswith('a')]
        self._utils_run_testing_for(Game, filters)

    def test_paginating_Cover(self):
        # Фильтр обложек по играм "Grand Theft Auto"
        filters = [
            Cover.game.in_(
                Game.select().filter(
                    Game.name.contains('Grand Theft Auto')
                )
            )
        ]
        self._utils_run_testing_for(Cover, filters)

    def test_Cover_get_by_page(self):
        def _get_items(page: int = 1, **kwargs) -> List[Cover]:
            items = []

            while cover := Cover.get_by_page(page=page, **kwargs):
                page += 1
                items.append(cover)

            return items

        with self.subTest(page=1):
            self.assertEqual(Cover.get_by_page(page=1), Cover.get_first())

        non_existent_page_number = 999999
        with self.subTest('non_existent_page_number', page=non_existent_page_number):
            self.assertIsNone(Cover.get_by_page(page=non_existent_page_number))
            self.assertFalse(Cover.get_by_page(page=non_existent_page_number))
            items = _get_items(page=non_existent_page_number)
            self.assertFalse(items)
            self.assertFalse(len(items))

        for author_id in [3917270, DEFAULT_AUTHOR_ID]:
            with self.subTest(by_author=author_id):
                author = Author.get_by_id(author_id)
                items = _get_items(by_author=author_id)
                self.assertTrue(items)
                self.assertEqual(items, _get_items(by_author=author))
                self.assertFalse(_get_items(by_author=author_id, filters=[Cover.id == -1]))

                self.assertEqual(Cover.get_by_page(page=1, by_author=author_id), author.get_covers()[0])
                self.assertEqual(Cover.get_by_page(page=1, by_author=author), author.get_covers()[0])

        for game_series_id in [26]:
            with self.subTest(by_game_series=game_series_id):
                game_series = GameSeries.get_by_id(game_series_id)
                items = _get_items(by_game_series=game_series_id)
                self.assertTrue(items)
                self.assertEqual(items, _get_items(by_game_series=game_series))
                self.assertFalse(_get_items(by_game_series=game_series, filters=[Cover.id == -1]))

        for game_id in [32]:
            with self.subTest(game_id=game_id):
                game = Game.get_by_id(game_id)
                items = _get_items(by_game=game_id)
                self.assertTrue(items)
                self.assertEqual(items, _get_items(by_game=game))
                self.assertFalse(_get_items(by_game=game, filters=[Cover.id == -1]))


class TestDbCover(unittest.TestCase):
    COVER_ID = None

    def setUp(self):
        if self.COVER_ID:
            self.cover = Cover.get_by_id(self.COVER_ID)
        else:
            self.cover = Cover.get_first()

        self.assertIsNotNone(self.cover)

    def test_text(self):
        self.assertTrue(self.cover.text)
        self.assertIsInstance(self.cover.text, str)

    def test_file_name(self):
        self.assertTrue(self.cover.file_name)
        self.assertIsInstance(self.cover.file_name, str)

    def test_url_post(self):
        self.assertTrue(self.cover.url_post)
        self.assertIsInstance(self.cover.url_post, str)

    def test_url_post_image(self):
        self.assertTrue(self.cover.url_post_image)
        self.assertIsInstance(self.cover.url_post_image, str)

    def test_game(self):
        self.assertTrue(self.cover.game)
        self.assertIsInstance(self.cover.game, Game)
        self.assertTrue(self.cover.game.id)

    def test_date_time(self):
        self.assertTrue(self.cover.date_time)
        self.assertIsInstance(self.cover.date_time, DT.datetime)

    def test_abs_file_name(self):
        self.assertTrue(self.cover.abs_file_name.exists())

        img_data = self.cover.abs_file_name.read_bytes()
        self.assertTrue(img_data)
        self.assertTrue(b'JFIF' in img_data, f'File {self.cover.abs_file_name} is not JPG image!')

    def test_get_authors(self):
        authors = self.cover.get_authors()
        self.assertIsInstance(authors, list)

        author = authors[0]
        self.assertTrue(author)

        covers = author.get_covers()
        self.assertTrue(covers)
        self.assertEqual(covers, author.get_covers(reverse=True)[::-1])
        self.assertEqual(covers[::-1], author.get_covers(reverse=True))

    def test_count_by(self):
        self.assertEqual(Cover.count_by(), Cover.count())
        self.assertEqual(
            Cover.count_by(by_author=None, by_game_series=None, by_game=None),
            Cover.count()
        )

        by_author = None
        by_game_series = None
        by_game = None
        cover_filters = dict(
            by_author=by_author,
            by_game_series=by_game_series,
            by_game=by_game,
        )
        self.assertEqual(
            Cover.count_by(by_author=by_author, by_game_series=by_game_series, by_game=by_game),
            Cover.count_by(**cover_filters)
        )

    def test_get_page(self):
        page = 1
        for by_author, by_game_series, by_game in [
            (None, None, None),
            (Author.get_first(), None, None),
            (Author.get_last(), None, None),
            (None, GameSeries.get_first(), None),
            (None, GameSeries.get_last(), None),
            (None, None, Game.get_first()),
            (None, None, Game.get_last()),
        ]:
            with self.subTest(
                    page=page,by_author=by_author,
                    by_game_series=by_game_series,
                    by_game=by_game,
            ):
                cover = Cover.get_by_page(
                    page=page,
                    by_author=by_author,
                    by_game_series=by_game_series,
                    by_game=by_game,
                )
                self.assertEqual(
                    page,
                    Cover.get_page(
                        need_cover_id=cover.id,
                        by_author=by_author,
                        by_game_series=by_game_series,
                        by_game=by_game,
                    )
                )


class TestDbCoverAll(unittest.TestCase):
    def test_all_covers(self):
        for cover in Cover.select(Cover.id).order_by(Cover.id):
            cover_id = cover.id

            for test_method in filter(lambda x: x.startswith('test_'), dir(TestDbCover)):
                with self.subTest(cover_id=cover_id, test_method=test_method):
                    TestDbCover.COVER_ID = cover_id

                    result = TestDbCover(test_method).run()
                    self.assertTrue(result.wasSuccessful())


if __name__ == '__main__':
    unittest.main()
