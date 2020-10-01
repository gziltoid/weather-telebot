import os
from enum import Enum

from dotenv import load_dotenv, find_dotenv
from telebot import types as tt

from state import Units, Language

load_dotenv(find_dotenv())

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
OWM_API_KEY = os.getenv('OWM_API_KEY')
REDIS_URL = os.getenv('REDIS_URL')

API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
LOCAL_DB_PATH = 'db/data'

DEGREE_SIGNS = {Units.METRIC: '℃', Units.IMPERIAL: '℉'}
LANGUAGE_SIGNS = {Language.ENGLISH: '🇺🇸', Language.RUSSIAN: '🇷🇺'}
UNITS_SIGNS = {Units.METRIC: '📏', Units.IMPERIAL: '👑'}
BAD_COMMAND_ANSWERS = (
    'Sorry, I didn\'t get what you mean.',
    'Sorry, I didn\'t quite get it.',
    'Eh? I don\'t get it.',
    'Oops. Please try again.',
    'Sorry, I don\'t understand.',
    'Sorry, I didn\'t catch that.',
    'It makes no sense to me.',
    'It\'s a mystery to me.',
    'It\'s completely beyond me.',
    'I can\'t get my head around it.',
    'Sorry?',
    'Sorry, what?',
    'I’m sorry, what was that?',
    'Excuse me?',
    'Pardon?',
    'What?',
    'Hmm?',
    'Come again?',
    'This is all Greek to me.',
    'I can’t make head nor tail of what you’re saying.',
    'Bad command. Please try again.',
    'Command not recognized. Please try again.'
)


class Command(Enum):
    CURRENT = '/current'
    TOMORROW = '/tomorrow'
    FORECAST = '/forecast'
    SETTINGS = '/settings'


class KeyboardButton(Enum):
    CURRENT = '⛅ Current'
    TOMORROW = '➡️️️ Tomorrow'
    FORECAST = '📆 For 4 days'
    SETTINGS = '☑️️ Settings'
    LOCATION = '🌎 Change location'
    LANGUAGE = '🔤️ Change language'
    UNITS = '📐 Change units'
    ENGLISH = '🇺🇸 English'
    RUSSIAN = '🇷🇺 Русский'
    METRIC = '📏 Metric'
    IMPERIAL = '👑 Imperial'
    BACK = '↩️ Back'


MAIN_KEYBOARD = (
    KeyboardButton.CURRENT,
    KeyboardButton.TOMORROW,
    KeyboardButton.FORECAST,
    KeyboardButton.SETTINGS
)

SETTINGS_KEYBOARD = (
    KeyboardButton.LOCATION,
    KeyboardButton.LANGUAGE,
    KeyboardButton.UNITS,
    KeyboardButton.BACK
)

SETTING_LOCATION_KEYBOARD = (
    KeyboardButton.BACK,  # comma to make this a 1-element tuple
)

SETTING_LANGUAGE_KEYBOARD = (
    KeyboardButton.ENGLISH,
    KeyboardButton.RUSSIAN,
    KeyboardButton.BACK
)

SETTING_UNITS_KEYBOARD = (
    KeyboardButton.METRIC,
    KeyboardButton.IMPERIAL,
    KeyboardButton.BACK
)

BOT_MAIN_COMMANDS = (
    tt.BotCommand(command=Command.CURRENT.value, description='Get the current weather'),
    tt.BotCommand(command=Command.TOMORROW.value, description='Get a forecast for tomorrow'),
    tt.BotCommand(command=Command.FORECAST.value, description='Get a 4-day forecast'),
    tt.BotCommand(command=Command.SETTINGS.value, description='Change your preferences')
)
