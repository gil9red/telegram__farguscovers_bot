#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time
from typing import Any

from playhouse.sqliteq import SqliteQueueDatabase
from telegram.ext import ExtBot


class ExtBotDebug(ExtBot):
    elapsed_time_ns: int = 0

    def start_timer(self):
        self.elapsed_time_ns = 0

    def _post(self, *args, **kwargs) -> Any:
        t = time.perf_counter_ns()
        result = super()._post(*args, **kwargs)
        self.elapsed_time_ns += time.perf_counter_ns() - t
        return result


class SqliteQueueDatabaseDebug(SqliteQueueDatabase):
    elapsed_time_ns: int = 0

    def start_timer(self):
        self.elapsed_time_ns = 0

    def execute_sql(self, *args, **kwargs) -> Any:
        t = time.perf_counter_ns()
        result = super().execute_sql(*args, **kwargs)
        self.elapsed_time_ns += time.perf_counter_ns() - t
        return result
