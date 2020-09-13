import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests
from pprint import pprint
import sys
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass

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


@dataclass
class Settings:
    location: str
    language: Language
    units: Units


# Constants
API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
DEGREE_SIGNS = {Units.METRIC: '℃', Units.IMPERIAL: '℉'}

# Globals
bot = telebot.TeleBot(TOKEN)

states = defaultdict(
    lambda: {
        'state': State.WELCOME,
        'settings': Settings(location='', language=Language.ENGLISH, units=Units.METRIC)
    })


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.from_user.id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 5 days 🐾\nJust send me one of these "
        "commands:"
    )
    show_commands(message)
    bot.send_message(message.from_user.id, '🐈 To start, send a location pin or enter your city:')
    states[message.from_user.id]['state'] = State.WELCOME

@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.WELCOME)
def welcome_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}.\n🐈 To start, send a location pin or enter your city:')
    elif message_text[0] != '/':
        # TODO location pin
        bot.send_chat_action(message.from_user.id, 'typing')
        if check_if_location_exists(message.text):
            location = message.text.strip().title()
            bot.send_message(message.from_user.id, f'Done. Current city: {location}')
            show_commands(message)
            states[message.from_user.id]['state'] = State.MAIN
            states[message.from_user.id]['settings'].location = location
            # TODO switch_to_state(print_message, state)
        else:
            bot.send_message(message.from_user.id, 'Location not found.')
            bot.send_message(message.from_user.id, '🐈 To start, send a location pin or enter your city:')
    else:
        bot.send_message(message.from_user.id, '🐈 To start, send a location pin or enter your city:')


def check_if_location_exists(loc):
    try:
        qs = {'q': loc, 'appid': OWM_API_KEY}
        response = requests.get(API_URL, params=qs)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
    else:
        return response.status_code == 200


def show_commands(message):
    bot.send_message(message.from_user.id, '''⛅ /current - get the current weather for a location
➡️️️ /tomorrow - get a forecast for tomorrow
📆 /forecast - get a 5-day forecast
☑️️ /settings - change your preferences''')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.MAIN)
def main_handler(message):
    message_text = message.text.strip().lower()
    if message_text == '/current':
        get_current_weather(message)
        show_commands(message)
    elif message_text == '/tomorrow':
        get_tomorrow_weather(message)
        show_commands(message)
    elif message_text == '/forecast':
        get_forecast(message)
        show_commands(message)
    elif message_text == '/settings':
        show_settings(message)
        states[message.from_user.id]['state'] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


def get_current_weather(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    settings = states[message.from_user.id]['settings']
    try:
        querystring = {
            'q': settings.location,
            'lang': settings.language.value,
            'units': settings.units.value,
            'appid': OWM_API_KEY,
        }
        print(querystring)
        response = requests.get(API_URL, params=querystring)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        bot.send_message(message.from_user.id, 'oops')
    else:
        if response.status_code == 200:
            response = response.json()
            city = response['city']['name']
            country = response['city']['country']
            temp = int(round(response['list'][0]['main']['temp']))
            desc = response['list'][0]['weather'][0]['description']
            # pprint(response)
            # print(f"Current weather in {city}, {country}: {temp}, {desc}")
            units = states[message.from_user.id]['settings'].units
            bot.send_message(message.from_user.id,
                             f"Current weather in {city}, {country}: {temp}{DEGREE_SIGNS[units]}, {desc}")
        else:
            # FIXME replace with check_if_location_exists()
            bot.send_message(message.from_user.id, response.json()['message'])
            show_location(message)
            # FIXME state
            states[message.from_user.id]['state'] = State.WELCOME


def get_tomorrow_weather(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    location = states[message.from_user.id]['settings'].location
    bot.send_message(message.from_user.id, f"Tomorrow\'s weather in {location}: XX")
    # TODO


def get_forecast(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    location = states[message.from_user.id]['settings'].location
    bot.send_message(message.from_user.id, f'5-day forecast for {location}: YY')
    # TODO


def show_settings(message):
    location = states[message.from_user.id]['settings'].location
    language = states[message.from_user.id]['settings'].language.value
    units = states[message.from_user.id]['settings'].units.value
    bot.send_message(
        message.from_user.id,
        f'''Settings:
🌎 /location - change your location (current: {location})
🔤️ /language - select a forecast language (current: {language})
📐 /units - change your unit preferences (current: {units})
↩️ /back - back to Weather''')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTINGS)
def settings_handler(message):
    message_text = message.text.strip().lower()
    if message_text == '/location':
        show_location(message)
        states[message.from_user.id]['state'] = State.SETTING_LOCATION
    elif message_text == '/language':
        show_language(message)
        states[message.from_user.id]['state'] = State.SETTING_LANGUAGE
    elif message_text == '/units':
        show_units(message)
        states[message.from_user.id]['state'] = State.SETTING_UNITS
    elif message_text == '/back':
        show_commands(message)
        states[message.from_user.id]['state'] = State.MAIN
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


def show_location(message):
    location = states[message.from_user.id]['settings'].location
    bot.send_message(
        message.from_user.id,
        f'Current location: {location}.\n/back - back to Settings\nSend a location pin or enter your city:')


def show_language(message):
    language = states[message.from_user.id]['settings'].language.value
    bot.send_message(message.from_user.id, f'Current forecast language: {language}.\n/back - back to '
                                           f'Settings\nSelect a forecast language: 🇺🇸 en | 🇷🇺 ru')


def show_units(message):
    units = states[message.from_user.id]['settings'].units.value
    bot.send_message(
        message.from_user.id,
        f'Current units: {units}.\n/back - back to Settings\nChoose units: 📏 metric | 👑 imperial')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_LOCATION)
def setting_location_handler(message):
    message_text = message.text.strip()
    if message_text != '/back':
        # TODO location pin
        if check_if_location_exists(message_text):
            states[message.from_user.id]['settings'].location = message_text.title()
            location = states[message.from_user.id]['settings'].location
            bot.send_message(message.from_user.id, f'Updated. Current city: {location}')
            show_settings(message)
            states[message.from_user.id]['state'] = State.SETTINGS
        else:
            bot.send_message(message.from_user.id, 'Location not found.')
            bot.send_message(message.from_user.id, 'To start, send a location pin or enter your city:')
    else:
        show_settings(message)
        states[message.from_user.id]['state'] = State.SETTINGS


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'en', 'ru']:
        if message_text == 'en':
            # TODO extract method
            language = Language.ENGLISH
            states[message.from_user.id]['settings'].language = language
            bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        elif message_text == 'ru':
            language = Language.RUSSIAN
            states[message.from_user.id]['settings'].language = language
            bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        show_settings(message)
        states[message.from_user.id]['state'] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_UNITS)
def setting_units_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'imperial', 'metric']:
        if message_text == 'metric':
            # TODO extract method
            units = Units.METRIC
            states[message.from_user.id]['settings'].units = units
            bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
        elif message_text == 'imperial':
            units = Units.IMPERIAL
            states[message.from_user.id]['settings'].units = units
            bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
        show_settings(message)
        states[message.from_user.id]['state'] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)

    bot.polling()
