#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import contextlib
import functools
import logging
import sys
import re

from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

import config
from config import DIR_LOGS
from third_party.reply_message import reply_message, SeverityEnum


def get_logger(file_name: str, dir_name='logs'):
    dir_name = Path(dir_name).resolve()
    dir_name.mkdir(parents=True, exist_ok=True)

    file_name = str(dir_name / Path(file_name).resolve().name) + '.log'

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s')

    fh = logging.FileHandler(file_name, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.DEBUG)

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    log.addHandler(fh)
    log.addHandler(ch)

    return log


def log_func(log: logging.Logger):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            if update:
                chat_id = user_id = first_name = last_name = username = language_code = None

                if update.effective_chat:
                    chat_id = update.effective_chat.id

                if update.effective_user:
                    user_id = update.effective_user.id
                    first_name = update.effective_user.first_name
                    last_name = update.effective_user.last_name
                    username = update.effective_user.username
                    language_code = update.effective_user.language_code

                try:
                    message = update.effective_message.text
                except:
                    message = ''

                try:
                    query_data = update.callback_query.data
                except:
                    query_data = ''

                msg = f'[chat_id={chat_id}, user_id={user_id}, ' \
                      f'first_name={first_name!r}, last_name={last_name!r}, ' \
                      f'username={username!r}, language_code={language_code}, ' \
                      f'message={message!r}, query_data={query_data!r}]'
                msg = func.__name__ + msg

                log.debug(msg)

            return func(update, context)

        return wrapper
    return actual_decorator


def process_error(log: logging.Logger, update: Update, context: CallbackContext):
    log.error('Error: %s\nUpdate: %s', context.error, update, exc_info=context.error)
    if update:
        reply_message(config.ERROR_TEXT, update, context, severity=SeverityEnum.ERROR)


def get_slug(text: Optional[str]) -> str:
    if not text:
        return ''

    text = text.strip().replace(' ', '_')
    return re.sub(r'\W', '', text).lower()


# SOURCE: https://stackoverflow.com/a/23780046/5909792
@contextlib.contextmanager
def assert_exception(exception):
    try:
        yield
    except exception:
        assert True
    else:
        assert False


log = get_logger(__file__, DIR_LOGS / 'log.txt')


if __name__ == '__main__':
    assert get_slug("") == ""
    assert get_slug('Half-Life 2: Episode Two') == 'halflife_2_episode_two'
    assert get_slug("! ! !") == "__"
    assert get_slug("123") == "123"
    assert get_slug("1 2-3") == "1_23"
    assert get_slug("  Привет World!") == "привет_world"
    assert get_slug(None) == ''
