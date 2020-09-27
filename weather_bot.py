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
    ENGLISH = 'en'
    RUSSIAN = 'ru'

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


def load_db_from_json():
    try:
        with open(LOCAL_DB_PATH, encoding='utf-8') as f:
            data = deserialize(f.read())
    except FileNotFoundError:
        data = defaultdict(lambda: get_default_user_data())
    return data


def load_db_from_redis():
    redis_db = redis.from_url(REDIS_URL)
    raw_data = redis_db.get('data')
    if raw_data is None:
        data = defaultdict(lambda: get_default_user_data())
    else:
        data = deserialize(raw_data.decode('utf-8'))
    return data


def load_from_db():
    if REDIS_URL is None:
        print('Local DB')
        return load_db_from_json()
    else:
        print('Redis')
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


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 4 days 🐾\nJust send me one of these "
        "commands:"
    )
    show_commands(user_id)
    bot.send_message(user_id, '🐈 To start, send a location pin or enter your city:')
    states[user_id].state = State.WELCOME
    save_state()


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.WELCOME)
def welcome_handler(message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {user_first_name}.\n🐈 To start, send a location pin or enter your city:')
    elif message_text[0] != '/' and check_if_location_exists(message_text):
        bot.send_chat_action(user_id, 'typing')
        location = message_text.title()
        states[user_id].settings.location = location
        bot.send_message(user_id, f'Done. Current city: {location}')
        show_commands(user_id)
        states[user_id].state = State.MAIN
        save_state()
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
        return response.status_code == 200


def show_commands(user_id):
    bot.send_message(user_id, '''⛅ /current - get the current weather for a location
➡️️️ /tomorrow - get a forecast for tomorrow
📆 /forecast - get a 4-day forecast
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
            message = f"Current weather in {location_data.city}, {location_data.country}: " \
                      f"{report.temp}{DEGREE_SIGNS[units]}, {report.desc}"
            bot.send_message(user_id, message)
            return
    bot.send_message(user_id, 'Server error. Please try again.')


def get_tomorrow_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = states[user_id].settings.units
        location_data, reports = get_tomorrow_weather_from_response(response)
        if location_data is not None:
            message = f"{reports[0].datetime.strftime('%B %d')} - {location_data.city}, {location_data.country}:\n"
            for report in reports:
                message += f"{report.datetime.strftime('%H:%M')}: {report.temp}{DEGREE_SIGNS[units]}, {report.desc}\n"
            bot.send_message(user_id, message)
            return
    bot.send_message(user_id, 'Server error. Please try again.')


def get_forecast(user_id):
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = states[user_id].settings.units
        location_data, reports = get_forecast_from_response(response)
        if location_data is not None:
            lines = [f'4-day forecast for {location_data.city}, {location_data.country}:']
            for report in reports:
                lines.append(
                    f"{report.date.strftime('%b %d')}: {report.min}-{report.max}{DEGREE_SIGNS[units]}, {report.desc}")
            bot.send_message(user_id, '\n'.join(lines))
            return
    bot.send_message(user_id, 'Server error. Please try again.')


def request_forecast(location, language, units):
    querystring = {
        'q': location,
        'lang': language,
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
        save_state()
    elif message_text == '/language':
        show_language(user_id)
        states[user_id].state = State.SETTING_LANGUAGE
        save_state()
    elif message_text == '/units':
        show_units(user_id)
        states[user_id].state = State.SETTING_UNITS
        save_state()
    elif message_text == '/back':
        bot.send_message(user_id, f'Current city: {states[user_id].settings.location}')
        show_commands(user_id)
        states[user_id].state = State.MAIN
        save_state()
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

# TODO location pin
@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LOCATION)
def setting_location_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text != '/back':
        if check_if_location_exists(message_text):
            states[user_id].settings.location = message_text.title()
            location = states[user_id].settings.location
            bot.send_message(user_id, f'Updated. Current city: {location}')
            show_settings(user_id)
            states[user_id].state = State.SETTINGS
            save_state()
        else:
            bot.send_message(user_id, 'Location not found.')
            bot.send_message(user_id, 'To start, send a location pin or enter your city:')
    else:
        show_settings(user_id)
        states[user_id].state = State.SETTINGS
        save_state()


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'en', 'ru']:
        if message_text != '/back':
            language = Language.ENGLISH if message_text == 'en' else Language.RUSSIAN
            states[user_id].settings.language = language
            bot.send_message(user_id, f'Updated. Current language: {language.value}.')
        show_settings(user_id)
        states[user_id].state = State.SETTINGS
        save_state()
    else:
        reply_to_bad_command(message)


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_UNITS)
def setting_units_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'imperial', 'metric']:
        if message_text != '/back':
            units = Units.METRIC if message_text == 'metric' else Units.IMPERIAL
            states[user_id].settings.units = units
            bot.send_message(user_id, f'Updated. Current units: {units.value}.')
        show_settings(user_id)
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
