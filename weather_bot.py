from collections import defaultdict, namedtuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, tzinfo

import os
import random
import requests
import sys
import telebot
from dotenv import load_dotenv, find_dotenv
from pprint import pprint

load_dotenv(find_dotenv())

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
OWM_API_KEY = os.getenv('OWM_API_KEY')


# Enums
class Units(Enum):
    METRIC = 'metric'
    IMPERIAL = 'imperial'


class Language(Enum):
    ENGLISH = 'en'
    RUSSIAN = 'ru'


class State(Enum):
    MAIN = 0
    WELCOME = 1
    FORECAST = 2
    SETTINGS = 3
    SETTING_LOCATION = 4
    SETTING_LANGUAGE = 5
    SETTING_UNITS = 6


# Dataclasses
@dataclass
class Settings:
    location: str
    language: Language
    units: Units


@dataclass
class User:
    state: State
    settings: Settings


# Constants
API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
DEGREE_SIGNS = {Units.METRIC: '℃', Units.IMPERIAL: '℉'}
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

# Globals
bot = telebot.TeleBot(TOKEN)

states = defaultdict(
    lambda: User(
        state=State.WELCOME,
        settings=Settings(location='', language=Language.ENGLISH, units=Units.METRIC)
    )
)

buttons = ['Current', 'Tomorrow', 'For 5 days', 'Settings']


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

    # markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # row = [telebot.types.KeyboardButton(name) for name in buttons]
    # markup.row(*buttons[:2])
    # markup.row(*buttons[2:])
    # btn = telebot.types.KeyboardButton('Location', request_location=True)
    # markup.add(btn)
    # markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    # markup.add(telebot.types.InlineKeyboardButton(text='Press me', callback_data='button:2'))
    # bot.send_message(user_id, 'wow', reply_markup=markup)
    # markup = telebot.types.ReplyKeyboardRemove(selective=False)

    bot.send_message(
        user_id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 5 days 🐾\nJust send me one of these "
        "commands:"
    )
    show_commands(user_id)
    bot.send_message(user_id, '🐈 To start, send a location pin or enter your city:')
    states[user_id].state = State.WELCOME


@bot.message_handler(content_types=['location'])
def location_handler(message):
    print('Got location:', message.location)


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.WELCOME)
def welcome_handler(message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {user_first_name}.\n🐈 To start, send a location pin or enter your city:')
    elif message_text[0] != '/' and check_if_location_exists(message_text):
        # TODO location pin
        bot.send_chat_action(user_id, 'typing')
        location = message_text.title()
        states[user_id].settings.location = location
        bot.send_message(user_id, f'Done. Current city: {location}')
        show_commands(user_id)
        states[user_id].state = State.MAIN
        # TODO switch_to_state(user_id, state, show_message)
    else:
        bot.send_message(user_id, 'Location not found.')
        bot.send_message(user_id, '🐈 To start, send a location pin or enter your city:')


def check_if_location_exists(location):
    try:
        querystring = {'q': location, 'appid': OWM_API_KEY}
        response = requests.get(API_URL, params=querystring)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
    else:
        # pprint(response.json())
        return response.status_code == 200


def show_commands(user_id):
    bot.send_message(user_id, '''⛅ /current - get the current weather for a location
➡️️️ /tomorrow - get a forecast for tomorrow
📆 /forecast - get a 5-day forecast
☑️️ /settings - change your preferences''')


def reply_to_bad_command(message):
    bot.reply_to(message, random.choice(BAD_COMMAND_ANSWERS))


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.MAIN)
def main_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text == '/current':
        get_current_weather(user_id)
        show_commands(user_id)
    elif message_text == '/tomorrow':
        get_tomorrow_weather(user_id)
        show_commands(user_id)
    elif message_text == '/forecast':
        get_forecast(user_id)
        show_commands(user_id)
    elif message_text == '/settings':
        show_settings(user_id)
        states[user_id].state = State.SETTINGS
    else:
        reply_to_bad_command(message)


# TODO OWM API module
def get_current_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    querystring = {
        'q': settings.location,
        'lang': settings.language.value,
        'units': settings.units.value,
        'appid': OWM_API_KEY,
    }
    response = request_forecast(querystring)
    if response is not None:
        pprint(response['list'][0])
        # FIXME try/except
        location_data, report = get_current_weather_from_response(response)
        units = states[user_id].settings.units
        bot.send_message(user_id,
                         f"Current weather in {location_data.city}, {location_data.country}: "
                         f"{report.temp}{DEGREE_SIGNS[units]}, {report.desc}")
    else:
        bot.send_message(user_id, 'Oops. Try again.')


LocationData = namedtuple('LocationData', 'city country')
CurrentWeatherReport = namedtuple('CurrentWeatherReport', 'temp desc')
TomorrowWeatherReport = namedtuple('TomorrowWeatherReport', 'datetime temp desc')
ForecastWeatherReport = namedtuple('ForecastWeatherReport', 'date min max desc')


def get_current_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        temp = int(round(response['list'][0]['main']['temp']))
        desc = response['list'][0]['weather'][0]['description']
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None
    return LocationData(city=city, country=country), CurrentWeatherReport(temp=temp, desc=desc)


def request_forecast(querystring):
    try:
        response = requests.get(API_URL, params=querystring)
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None
    if response.status_code == 200:
        return response.json()
    return None


def get_tomorrow_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    querystring = {
        'q': settings.location,
        'lang': settings.language.value,
        'units': settings.units.value,
        'appid': OWM_API_KEY,
    }
    response = request_forecast(querystring)
    if response is not None:
        pprint(response['list'][0])
        units = states[user_id].settings.units
        location_data, reports = get_tomorrow_weather_from_response(response)
        if location_data is not None:
            message = f"{reports[0].datetime.strftime('%B %d')} - {location_data.city}, {location_data.country}:\n"
            for report in reports:
                message += f"{report.datetime.strftime('%H:%M')}: {report.temp}{DEGREE_SIGNS[units]}, {report.desc}\n"
            bot.send_message(user_id, message)
            return
    bot.send_message(user_id, 'Server error. Try again.')


def get_tomorrow_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        today = response_day_to_local_time(response['list'][0], tzoffset)
        tomorrow = (today + timedelta(days=+1))
        reports = []
        for day in response['list']:
            dt = response_day_to_local_time(day, tzoffset)
            if dt.day == today.day:
                continue
            elif dt.day == tomorrow.day:
                temp = int(round(day['main']['temp']))
                desc = day['weather'][0]['description']
                reports.append(TomorrowWeatherReport(datetime=dt, temp=temp, desc=desc))
            else:
                break
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), reports


class SimpleTimezone(tzinfo):
    def __init__(self, offset):
        self.offset = offset

    def utcoffset(self, dt):
        return timedelta(seconds=self.offset)

    def dst(self, dt):
        return timedelta(0)


def response_day_to_local_time(day, tzoffset):
    return datetime.fromtimestamp(int(day['dt']), tz=SimpleTimezone(tzoffset))


def get_forecast(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    location = states[user_id].settings.location
    querystring = {
        'q': settings.location,
        'lang': settings.language.value,
        'units': settings.units.value,
        'appid': OWM_API_KEY,
    }
    response = request_forecast(querystring)
    if response is not None:
        pprint(response['list'][0])
        units = states[user_id].settings.units
        # FIXME try/except
        location_data, reports = get_forecast_from_response(response)
        message = f'{reports[0].date} - {location_data.city}, {location_data.country}:\n'
        for report in reports:
            message += f"{report.time}: {report.temp}{DEGREE_SIGNS[units]}, {report.desc}\n"
        bot.send_message(user_id, message)
        bot.send_message(user_id, f'5-day forecast for {location}: YY')
    else:
        bot.send_message(user_id, 'Oops. Try again.')

def get_forecast_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        reports = []
        for day in response['list']:
            dt = response_day_to_local_time(day, tzoffset)
            temp = int(round(day['main']['temp']))
            desc = day['weather'][0]['description']
            time = dt.strftime('%H:%M')
            # TODO Sep 21, min: 21, max: 30 sunny
            # reports.append(WeatherReport(date=dt.strftime('%B %d'), time=None, temp=temp, desc=desc))
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None
    return LocationData(city=city, country=country), reports

def show_settings(user_id):
    location = states[user_id].settings.location
    language = states[user_id].settings.language.value
    units = states[user_id].settings.units.value
    bot.send_message(
        user_id,
        f'''Settings:
🌎 /location - change your location (current: {location})
🔤️ /language - select a forecast language (current: {language})
📐 /units - change your unit preferences (current: {units})
↩️ /back - back to Weather''')


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTINGS)
def settings_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text == '/location':
        show_location(user_id)
        states[user_id].state = State.SETTING_LOCATION
    elif message_text == '/language':
        show_language(user_id)
        states[user_id].state = State.SETTING_LANGUAGE
    elif message_text == '/units':
        show_units(user_id)
        states[user_id].state = State.SETTING_UNITS
    elif message_text == '/back':
        show_commands(user_id)
        states[user_id].state = State.MAIN
    else:
        reply_to_bad_command(message)


def show_location(user_id):
    location = states[user_id].settings.location
    bot.send_message(
        user_id,
        f'Current location: {location}.\n/back - back to Settings\nSend a location pin or enter your city:')


def show_language(user_id):
    language = states[user_id].settings.language.value
    bot.send_message(user_id, f'Current forecast language: {language}.\n/back - back to Settings\nSelect a forecast '
                              f'language: 🇺🇸 en | 🇷🇺 ru')


def show_units(user_id):
    units = states[user_id].settings.units.value
    bot.send_message(
        user_id,
        f'Current units: {units}.\n/back - back to Settings\nChoose units: 📏 metric | 👑 imperial')


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LOCATION)
def setting_location_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text != '/back':
        # TODO location pin
        if check_if_location_exists(message_text):
            states[user_id].settings.location = message_text.title()
            location = states[user_id].settings.location
            bot.send_message(user_id, f'Updated. Current city: {location}')
            show_settings(user_id)
            states[user_id].state = State.SETTINGS
        else:
            bot.send_message(user_id, 'Location not found.')
            bot.send_message(user_id, 'To start, send a location pin or enter your city:')
    else:
        show_settings(user_id)
        states[user_id].state = State.SETTINGS


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'en', 'ru']:
        if message_text == 'en':
            # TODO extract method
            language = Language.ENGLISH
            states[user_id].settings.language = language
            bot.send_message(user_id, f'Updated. Current language: {language.value}.')
        elif message_text == 'ru':
            language = Language.RUSSIAN
            states[user_id].settings.language = language
            bot.send_message(user_id, f'Updated. Current language: {language.value}.')
        show_settings(user_id)
        states[user_id].state = State.SETTINGS
    else:
        reply_to_bad_command(message)


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_UNITS)
def setting_units_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'imperial', 'metric']:
        if message_text == 'metric':
            # TODO extract method
            units = Units.METRIC
            states[user_id].settings.units = units
            bot.send_message(user_id, f'Updated. Current units: {units.value}.')
        elif message_text == 'imperial':
            units = Units.IMPERIAL
            states[user_id].settings.units = units
            bot.send_message(user_id, f'Updated. Current units: {units.value}.')
        show_settings(user_id)
        states[user_id].state = State.SETTINGS
    else:
        reply_to_bad_command(message)


if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)

    bot.polling()
