import os
import random
import sys
from collections import defaultdict, namedtuple, Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from enum import Enum

import redis
import requests
import telebot
from telebot import types
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
OWM_API_KEY = os.getenv('OWM_API_KEY')
REDIS_URL = os.getenv('REDIS_URL')


# Enums
class Units(Enum):
    METRIC = 'metric'
    IMPERIAL = 'imperial'

    @classmethod
    def from_str(cls, label):
        if label == cls.METRIC.value:
            return cls.METRIC
        elif label == cls.IMPERIAL.value:
            return cls.IMPERIAL
        else:
            raise NotImplementedError


class Language(Enum):
    ENGLISH = 'english'
    RUSSIAN = 'russian'

    @classmethod
    def from_str(cls, label):
        if label == cls.ENGLISH.value:
            return cls.ENGLISH
        elif label == cls.RUSSIAN.value:
            return cls.RUSSIAN
        else:
            raise NotImplementedError


class State(Enum):
    MAIN = 0
    WELCOME = 1
    FORECAST = 2
    SETTINGS = 3
    SETTING_LOCATION = 4
    SETTING_LANGUAGE = 5
    SETTING_UNITS = 6

    @classmethod
    def from_int(cls, label):
        if label in range(7):
            return cls(label)
        else:
            raise NotImplementedError

class Command(Enum):
    CURRENT = '/current'
    TOMORROW = '/tomorrow'
    FORECAST = '/forecast'
    SETTINGS = 'settings'
    LOCATION = '/location'
    LANGUAGE = '/language'
    UNITS = '/units'
    BACK = '/back'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class KeyboardReply(Enum):
    CURRENT = '⛅ Current'
    TOMORROW = '➡️️️ Tomorrow'
    FORECAST = '📆 For 4 days'
    SETTINGS = '☑️️ Settings'
    LOCATION = '🌎 Change location'
    LANGUAGE = '🔤️ Change language'
    ENGLISH = '🇺🇸 English'
    RUSSIAN = '🇷🇺 Русский'
    UNITS = '📐 Change units'
    METRIC = '📏 Metric'
    IMPERIAL = '👑 Imperial'
    BACK = '↩️ Back'


# Dataclasses
@dataclass
class Settings:
    location: str
    language: Language
    units: Units


@dataclass
class UserData:
    state: State
    settings: Settings


LocationData = namedtuple('LocationData', 'city country')
CurrentWeatherReport = namedtuple('CurrentWeatherReport', 'temp desc')
TomorrowWeatherReport = namedtuple('TomorrowWeatherReport', 'datetime temp desc')
ForecastWeatherReport = namedtuple('ForecastWeatherReport', 'date min max desc')

# Constants
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


def serialize(states):
    lines = []
    for id_, user_data in states.items():
        state = user_data.state.value
        location = user_data.settings.location
        language = user_data.settings.language.value
        units = user_data.settings.units.value
        lines.append(f'{id_}|{state}|{location}|{language}|{units}')
    return '\n'.join(lines)


def deserialize(s):
    states = {}
    lines = s.splitlines()
    for line in lines:
        id_, state, loc, lang, units = line.split('|')
        states[int(id_)] = UserData(
            state=State.from_int(int(state)),
            settings=Settings(
                location=loc,
                language=Language.from_str(lang),
                units=Units.from_str(units)
            )
        )
    return states


def get_default_user_data():
    return UserData(state=State.WELCOME,
                    settings=Settings(location='', language=Language.ENGLISH, units=Units.METRIC))


def load_from_local_db():
    try:
        with open(LOCAL_DB_PATH, encoding='utf-8') as f:
            data = defaultdict(lambda: get_default_user_data(), deserialize(f.read()))
    except FileNotFoundError:
        data = defaultdict(lambda: get_default_user_data())
    return data


def load_db_from_redis():
    redis_db = redis.from_url(REDIS_URL)
    raw_data = redis_db.get('data')
    if raw_data is None:
        data = defaultdict(lambda: get_default_user_data())
    else:
        data = defaultdict(lambda: get_default_user_data(), deserialize(raw_data.decode('utf-8')))
    return data


def load_from_db():
    if REDIS_URL is None:
        print('Using Local DB.')
        return load_from_local_db()
    else:
        print('Using Redis.')
        return load_db_from_redis()


def save_state():
    if REDIS_URL is not None:
        redis_db = redis.from_url(REDIS_URL)
        redis_db.set('data', serialize(states))
    else:
        with open(LOCAL_DB_PATH, mode='w', encoding='utf-8') as f:
            f.write(serialize(states))


# Globals
bot = telebot.TeleBot(TOKEN)
states = load_from_db()

def remove_keyboard():
    return types.ReplyKeyboardRemove(selective=False)

def get_main_keyboard():
    # FIXME const buttons
    main_buttons = [item.value for item in (KeyboardReply.CURRENT, KeyboardReply.TOMORROW, KeyboardReply.FORECAST, KeyboardReply.SETTINGS)]
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*main_buttons)
    return markup

def get_settings_keyboard():
    # FIXME const buttons
    settings_buttons = [item.value for item in (KeyboardReply.LOCATION, KeyboardReply.LANGUAGE, KeyboardReply.UNITS, KeyboardReply.BACK)]
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add(settings_buttons[0])
    markup.row(*settings_buttons[1:3])
    markup.add(settings_buttons[3])
    return markup

def get_select_location_keyboard():
    # FIXME const buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=KeyboardReply.BACK.value, callback_data=KeyboardReply.BACK.value))
    return markup

def get_select_language_keyboard():
    # FIXME const buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(text=KeyboardReply.ENGLISH.value, callback_data=KeyboardReply.ENGLISH.value),
        types.InlineKeyboardButton(text=KeyboardReply.RUSSIAN.value, callback_data=KeyboardReply.RUSSIAN.value)
    )
    markup.add(types.InlineKeyboardButton(text=KeyboardReply.BACK.value, callback_data=KeyboardReply.BACK.value))
    return markup

def get_select_units_keyboard():
    # FIXME const buttons
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(text=KeyboardReply.METRIC.value, callback_data=KeyboardReply.METRIC.value),
        types.InlineKeyboardButton(text=KeyboardReply.IMPERIAL.value, callback_data=KeyboardReply.IMPERIAL.value)
    )
    markup.add(types.InlineKeyboardButton(text=KeyboardReply.BACK.value, callback_data=KeyboardReply.BACK.value))
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 4 days 🐾",
        reply_markup=remove_keyboard()
    )
    bot.send_message(user_id, '🐈 To start, enter your city:')
    states[user_id].state = State.WELCOME
    save_state()


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.WELCOME)
def welcome_handler(message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {user_first_name}.\n🐈 To start, enter your city:')
    elif message_text[0] != '/' and check_if_location_exists(message_text):
        bot.send_chat_action(user_id, 'typing')
        location = message_text.title()
        states[user_id].settings.location = location
        bot.send_message(user_id, f'👌 Done. Current city: {location}')
        show_main_keyboard(user_id)
        states[user_id].state = State.MAIN
        save_state()
    else:
        bot.send_message(user_id, '⚠️ Location not found.\n\n🐈 To start, enter your city:')


def check_if_location_exists(location):
    try:
        querystring = {'q': location, 'appid': OWM_API_KEY}
        response = requests.get(API_URL, params=querystring)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
    else:
        return response.status_code == 200


def show_main_keyboard(user_id):
    bot.send_message(user_id, 'Choose one:', reply_markup=get_main_keyboard())


def reply_to_bad_command(message):
    bot.reply_to(message, random.choice(BAD_COMMAND_ANSWERS))


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.MAIN)
def main_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text in (Command.CURRENT, KeyboardReply.CURRENT.value):
        get_current_weather(user_id)
    elif message_text in (Command.TOMORROW, KeyboardReply.TOMORROW.value):
        get_tomorrow_weather(user_id)
    elif message_text in (Command.FORECAST, KeyboardReply.FORECAST.value):
        get_forecast(user_id)
    elif message_text in (Command.SETTINGS, KeyboardReply.SETTINGS.value):
        show_settings_and_keyboard(user_id)
        states[user_id].state = State.SETTINGS
        save_state()
    else:
        reply_to_bad_command(message)


class SimpleTimezone(tzinfo):
    def __init__(self, offset):
        self.offset = offset

    def utcoffset(self, dt):
        return timedelta(seconds=self.offset)

    def dst(self, dt):
        return timedelta(0)


# TODO OWM API module, detailed report
def get_current_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        location_data, report = get_current_weather_from_response(response)
        if location_data is not None:
            units = states[user_id].settings.units
            message = f"<i>Current weather in {location_data.city}, {location_data.country}: " \
                      f"{report.temp}{DEGREE_SIGNS[units]}, {report.desc}</i>"
            bot.send_message(user_id, message, parse_mode='HTML')
            return
    bot.send_message(user_id, '⁉️ Server error. Please try again.')


def get_tomorrow_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = states[user_id].settings.units
        location_data, reports = get_tomorrow_weather_from_response(response)
        if location_data is not None:
            lines = [f"<u>{reports[0].datetime.strftime('%B %d')} - {location_data.city}, {location_data.country}:</u>"]
            for report in reports:
                lines.append(f"<i><b>{report.datetime.strftime('%H:%M')}</b>: {report.temp}{DEGREE_SIGNS[units]}, {report.desc}</i>")
            bot.send_message(user_id, '\n'.join(lines), parse_mode='HTML')
            return
    bot.send_message(user_id, '⁉️ Server error. Please try again.')


def get_forecast(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = states[user_id].settings.units
        location_data, reports = get_forecast_from_response(response)
        if location_data is not None:
            lines = [f'<u>4-day forecast for {location_data.city}, {location_data.country}:</u>']
            for report in reports:
                lines.append(
                    f"<i><b>{report.date.strftime('%b %d')}</b>: {report.min}-{report.max}{DEGREE_SIGNS[units]}, {report.desc}</i>")
            bot.send_message(user_id, '\n'.join(lines), parse_mode='HTML')
            return
    bot.send_message(user_id, '⁉️ Server error. Please try again.')


def request_forecast(location, language, units):
    querystring = {
        'q': location,
        'lang': language[:2],
        'units': units,
        'appid': OWM_API_KEY,
    }
    try:
        response = requests.get(API_URL, params=querystring)
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None
    if response.status_code == 200:
        return response.json()
    return None


# TODO change OWM API endpoint
def get_current_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        temp = int(round(response['list'][0]['main']['temp']))
        desc = response['list'][0]['weather'][0]['description']
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), CurrentWeatherReport(temp=temp, desc=desc)


def response_day_to_local_time(day, tzoffset):
    return datetime.fromtimestamp(int(day['dt']), tz=SimpleTimezone(tzoffset))


def get_tomorrow_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        today = response_day_to_local_time(response['list'][0], tzoffset)
        tomorrow = (today + timedelta(days=+1))
        reports = []
        for interval in response['list']:
            dt = response_day_to_local_time(interval, tzoffset)
            if dt.day == today.day:
                continue
            elif dt.day == tomorrow.day:
                temp = int(round(interval['main']['temp']))
                desc = interval['weather'][0]['description']
                reports.append(TomorrowWeatherReport(datetime=dt, temp=temp, desc=desc))
            else:
                break
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), reports


def get_forecast_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        today = response_day_to_local_time(response['list'][0], tzoffset)
        reports = []
        days = []
        for i, interval in enumerate(response['list']):
            dt = response_day_to_local_time(interval, tzoffset)
            if dt.day == today.day:
                continue
            else:
                shift = 8
                for d in range(4):
                    days.append(response['list'][i + shift * d: i + shift * (d + 1)])
                break

        for day in days:
            dt = response_day_to_local_time(day[0], tzoffset)
            day_temps = []
            for interval in day:
                temp = int(round(interval['main']['temp']))
                desc = interval['weather'][0]['description']
                day_temps.append((temp, desc))

            min_temp = min(day_temps, key=lambda t_d: t_d[0])[0]
            max_temp = max(day_temps, key=lambda t_d: t_d[0])[0]
            day_desc = Counter(tup[1] for tup in day_temps).most_common(1)[0][0]
            reports.append(ForecastWeatherReport(date=dt, min=min_temp, max=max_temp, desc=day_desc))
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), reports


def show_settings_and_keyboard(user_id):
    location = states[user_id].settings.location
    language = states[user_id].settings.language
    units = states[user_id].settings.units
    bot.send_message(
        user_id,
        f'Current: 📍 {location} | {LANGUAGE_SIGNS[language]} {language.value.title()} | {UNITS_SIGNS[units]} {units.value}',
        reply_markup=get_settings_keyboard()
    )


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTINGS)
def settings_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text in (Command.LOCATION.value, KeyboardReply.LOCATION.value):
        show_location_and_keyboard(user_id)
        states[user_id].state = State.SETTING_LOCATION
        save_state()
    elif message_text in (Command.LANGUAGE.value, KeyboardReply.LANGUAGE.value):
        show_language_and_keyboard(user_id)
        states[user_id].state = State.SETTING_LANGUAGE
        save_state()
    elif message_text in (Command.UNITS.value, KeyboardReply.UNITS.value):
        show_units_and_keyboard(user_id)
        states[user_id].state = State.SETTING_UNITS
        save_state()
    elif message_text in (Command.BACK.value, KeyboardReply.BACK.value):
        show_current_city(user_id)
        show_main_keyboard(user_id)
        # TODO switch_to_state(user_id, to_state)
        states[user_id].state = State.MAIN
        save_state()
    else:
        reply_to_bad_command(message)


def show_current_city(user_id):
    bot.send_message(user_id, f'📍 Current city: {states[user_id].settings.location}')


def show_location_and_keyboard(user_id):
    bot.send_message(
        user_id,
        f'📍 Current location: {states[user_id].settings.location}.\n\n🐈 Enter your city:',
        reply_markup=get_select_location_keyboard()
    )


def show_language_and_keyboard(user_id):
    language = states[user_id].settings.language
    bot.send_message(
        user_id,
        f'Current forecast language: {LANGUAGE_SIGNS[language]} {language.value.title()}.\n\nChoose a forecast language:',
        reply_markup=get_select_language_keyboard()
    )


def show_units_and_keyboard(user_id):
    units = states[user_id].settings.units
    bot.send_message(
        user_id,
        f'Current units: {UNITS_SIGNS[units]} {units.value}.\n\nChoose units:',
        reply_markup=get_select_units_keyboard()
    )


# TODO location pin
@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LOCATION)
def setting_location_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text not in (Command.BACK.value, KeyboardReply.BACK.value):
        if check_if_location_exists(message_text):
            states[user_id].settings.location = message_text.title()
            location = states[user_id].settings.location
            bot.send_message(user_id, f'✔️ Updated. Current city: {location}')
            show_settings_and_keyboard(user_id)
            states[user_id].state = State.SETTINGS
            save_state()
        else:
            bot.send_message(user_id, '⚠️ Location not found.\n\n🐈 To start, enter your city:')
    else:
        show_settings_and_keyboard(user_id)
        states[user_id].state = State.SETTINGS
        save_state()


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text in (Command.BACK.value, KeyboardReply.BACK.value, KeyboardReply.ENGLISH.value, KeyboardReply.RUSSIAN.value):
        if message_text not in (Command.BACK.value, KeyboardReply.BACK.value):
            language = Language.ENGLISH if message_text == KeyboardReply.ENGLISH.value else Language.RUSSIAN
            states[user_id].settings.language = language
            bot.send_message(user_id, f'✔️ Updated. Current language: {LANGUAGE_SIGNS[language]} {language.value.title()}.')
        show_settings_and_keyboard(user_id)
        states[user_id].state = State.SETTINGS
        save_state()
    else:
        reply_to_bad_command(message)


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_UNITS)
def setting_units_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text in (Command.BACK.value, KeyboardReply.BACK.value, KeyboardReply.IMPERIAL.value, KeyboardReply.METRIC.value):
        if message_text not in (Command.BACK.value, KeyboardReply.BACK.value):
            units = Units.METRIC if message_text == KeyboardReply.METRIC.value else Units.IMPERIAL
            states[user_id].settings.units = units
            bot.send_message(user_id, f'✔️ Updated. Current units: {UNITS_SIGNS[units]} {units.value}.')
        show_settings_and_keyboard(user_id)
        states[user_id].state = State.SETTINGS
        save_state()
    else:
        reply_to_bad_command(message)


if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)
    if REDIS_URL is None:
        sys.stderr.write('Warning: REDIS_URL is not set, using local DB.' + os.linesep)

    bot.polling()


def test_serialization():
    data0 = get_default_user_data()
    data1 = get_default_user_data()
    data0.settings.location = 'Москва'
    data0.state = State.FORECAST
    data0.settings.units = Units.IMPERIAL
    data1.settings.location = 'San Jose'
    data1.state = State.MAIN
    data1.settings.language = Language.RUSSIAN

    states = {123: data0, 456: data1}
    encoded = serialize(states)
    decoded = deserialize(encoded)
    assert (states == decoded)
