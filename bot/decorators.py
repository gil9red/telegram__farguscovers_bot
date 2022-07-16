#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import functools
import logging
import time

from telegram import Update
from telegram.ext import CallbackContext

from bot.bot_debug import ExtBotDebug
from bot.db import db, TgUser, TgChat


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


def process_request(log: logging.Logger):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            func_name = func.__name__

            t = time.perf_counter_ns()
            db.start_timer()

            if not isinstance(context.bot, ExtBotDebug):
                raise Exception('Бот должен иметь тип ExtBotDebug!')
            bot: ExtBotDebug = context.bot
            bot.start_timer()

            if update:
                user = update.effective_user
                chat = update.effective_chat

                user_db = TgUser.get_from(user)
                if user_db:
                    user_db.actualize(user)

                chat_db = TgChat.get_from(chat)
                if chat_db:
                    chat_db.actualize(chat)

            result = func(update, context)

            elapsed_ms = (time.perf_counter_ns() - t) // 1_000_000
            elapsed_db_ms = db.elapsed_time_ns // 1_000_000
            elapsed_bot_ms = bot.elapsed_time_ns // 1_000_000

            log.debug(f'[{func_name}] Elapsed {elapsed_ms} ms (db/bot: {elapsed_db_ms}/{elapsed_bot_ms})')

            return result

        return wrapper
    return actual_decorator
