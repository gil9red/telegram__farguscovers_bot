#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import re


def fill_string_pattern(pattern: re.Pattern, *args) -> str:
    pattern = pattern.pattern
    pattern = pattern.strip('^$')
    return re.sub(r'\(.+?\)', '{}', pattern).format(*args)
