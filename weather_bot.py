import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests
from pprint import pprint
import sys
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass
import random

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
    'Not recognized command. Please try again.'
)

# Globals
bot = telebot.TeleBot(TOKEN)

states = defaultdict(
    lambda: {
        'state': State.WELCOME,
        'settings': Settings(location='', language=Language.ENGLISH, units=Units.METRIC)
    })


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 5 days 🐾\nJust send me one of these "
        "commands:"
    )
    show_commands(user_id)
    bot.send_message(user_id, '🐈 To start, send a location pin or enter your city:')
    states[user_id]['state'] = State.WELCOME

@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.WELCOME)
def welcome_handler(message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {user_first_name}.\n🐈 To start, send a location pin or enter your city:')
    elif message_text[0] != '/':
        # TODO location pin
        bot.send_chat_action(user_id, 'typing')
        if check_if_location_exists(message_text):
            location = message_text.title()
            bot.send_message(user_id, f'Done. Current city: {location}')
            show_commands(user_id)
            states[user_id]['state'] = State.MAIN
            states[user_id]['settings'].location = location
            # TODO switch_to_state(print_message, state)
        else:
            bot.send_message(user_id, 'Location not found.')
            bot.send_message(user_id, '🐈 To start, send a location pin or enter your city:')
    else:
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
📆 /forecast - get a 5-day forecast
☑️️ /settings - change your preferences''')

def reply_to_bad_command(message):
    bot.reply_to(message, random.choice(BAD_COMMAND_ANSWERS))

@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.MAIN)
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
        states[user_id]['state'] = State.SETTINGS
    else:
        reply_to_bad_command(message)


def get_current_weather(user_id):
    # user_id = message.from_user.id
    bot.send_chat_action(user_id, 'typing')
    settings = states[user_id]['settings']
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
        bot.send_message(user_id, 'Oops. Try again.')
    else:
        if response.status_code == 200:
            response = response.json()
            city = response['city']['name']
            country = response['city']['country']
            temp = int(round(response['list'][0]['main']['temp']))
            desc = response['list'][0]['weather'][0]['description']
            # pprint(response)
            # print(f"Current weather in {city}, {country}: {temp}, {desc}")
            units = states[user_id]['settings'].units
            bot.send_message(user_id,
                             f"Current weather in {city}, {country}: {temp}{DEGREE_SIGNS[units]}, {desc}")
        else:
            error_message = response.json()['message']
            bot.send_message(user_id, error_message)
            # show_location(user_id)
            # states[user_id]['state'] = State.WELCOME


def get_tomorrow_weather(user_id):
    bot.send_chat_action(user_id, 'typing')
    location = states[user_id]['settings'].location
    bot.send_message(user_id, f"Tomorrow\'s weather in {location}: XX")
    # TODO


def get_forecast(user_id):
    bot.send_chat_action(user_id, 'typing')
    location = states[user_id]['settings'].location
    bot.send_message(user_id, f'5-day forecast for {location}: YY')
    # TODO


def show_settings(user_id):
    location = states[user_id]['settings'].location
    language = states[user_id]['settings'].language.value
    units = states[user_id]['settings'].units.value
    bot.send_message(
        user_id,
        f'''Settings:
🌎 /location - change your location (current: {location})
🔤️ /language - select a forecast language (current: {language})
📐 /units - change your unit preferences (current: {units})
↩️ /back - back to Weather''')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTINGS)
def settings_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text == '/location':
        show_location(user_id)
        states[user_id]['state'] = State.SETTING_LOCATION
    elif message_text == '/language':
        show_language(user_id)
        states[user_id]['state'] = State.SETTING_LANGUAGE
    elif message_text == '/units':
        show_units(user_id)
        states[user_id]['state'] = State.SETTING_UNITS
    elif message_text == '/back':
        show_commands(user_id)
        states[user_id]['state'] = State.MAIN
    else:
        reply_to_bad_command(message)


def show_location(user_id):
    location = states[user_id]['settings'].location
    bot.send_message(
        user_id,
        f'Current location: {location}.\n/back - back to Settings\nSend a location pin or enter your city:')


def show_language(user_id):
    language = states[user_id]['settings'].language.value
    bot.send_message(user_id, f'Current forecast language: {language}.\n/back - back to Settings\nSelect a forecast '
                              f'language: 🇺🇸 en | 🇷🇺 ru')


def show_units(user_id):
    units = states[user_id]['settings'].units.value
    bot.send_message(
        user_id,
        f'Current units: {units}.\n/back - back to Settings\nChoose units: 📏 metric | 👑 imperial')


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_LOCATION)
def setting_location_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text != '/back':
        # TODO location pin
        if check_if_location_exists(message_text):
            states[user_id]['settings'].location = message_text.title()
            location = states[user_id]['settings'].location
            bot.send_message(user_id, f'Updated. Current city: {location}')
            show_settings(user_id)
            states[user_id]['state'] = State.SETTINGS
        else:
            bot.send_message(user_id, 'Location not found.')
            bot.send_message(user_id, 'To start, send a location pin or enter your city:')
    else:
        show_settings(user_id)
        states[user_id]['state'] = State.SETTINGS


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'en', 'ru']:
        if message_text == 'en':
            # TODO extract method
            language = Language.ENGLISH
            states[user_id]['settings'].language = language
            bot.send_message(user_id, f'Updated. Current language: {language.value}.')
        elif message_text == 'ru':
            language = Language.RUSSIAN
            states[user_id]['settings'].language = language
            bot.send_message(user_id, f'Updated. Current language: {language.value}.')
        show_settings(user_id)
        states[user_id]['state'] = State.SETTINGS
    else:
        reply_to_bad_command(message)


@bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.SETTING_UNITS)
def setting_units_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'imperial', 'metric']:
        if message_text == 'metric':
            # TODO extract method
            units = Units.METRIC
            states[user_id]['settings'].units = units
            bot.send_message(user_id, f'Updated. Current units: {units.value}.')
        elif message_text == 'imperial':
            units = Units.IMPERIAL
            states[user_id]['settings'].units = units
            bot.send_message(user_id, f'Updated. Current units: {units.value}.')
        show_settings(user_id)
        states[user_id]['state'] = State.SETTINGS
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
