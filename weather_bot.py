import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests
from pprint import pprint
import sys
from enum import Enum

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


# FIXME
DEGREE_SIGNS = {Units.METRIC: '℃', Units.IMPERIAL: '℉'}

# Constants
API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
LOCATION_DEFAULT = 'Moscow'
LANGUAGE_DEFAULT = Language.ENGLISH

# Globals
units = Units.METRIC
language = LANGUAGE_DEFAULT  # FIXME
location = LOCATION_DEFAULT
# are_notifications_enabled = False

bot = telebot.TeleBot(TOKEN)

states = {}

querystring = {
    'q': location,
    'lang': language.value,
    'units': units.value,
    'appid': OWM_API_KEY,
}


# @bot.message_handler(commands=['start', 'help'])
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # print(units, units.value, Units.METRIC, Units.METRIC.value)
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        '''Hey, I'm the Weather Cat.
I can show you a weather forecast up to 5 days.
Just send me one of these commands:
/current - get the current weather for a location
/tomorrow - get a forecast for tomorrow
/forecast - get a 5-day forecast
/settings - change your preferences

To start, send a location pin or enter your city:
''')
    states[user_id] = State.WELCOME
    # TODO
    # states[user_id] = {
    #     'state': State.WELCOME,
    #     'settings': 'A',
    # }


# @bot.message_handler(func=lambda message: states[message.from_user.id]['state'] == State.WELCOME)
@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.WELCOME)
def welcome_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}.\nTo start, send a location pin or enter your city:')
    elif message_text[0] != '/':
        # TODO check city, location pin
        global location
        bot.send_chat_action(message.from_user.id, 'typing')
        print(message.text)
        if check_if_location_exists(message.text):
            location = message.text.strip()
            bot.send_message(message.from_user.id, f'Done. Current city: {location}')
            show_commands(message)
            states[message.from_user.id] = State.MAIN
            # TODO switch_to_state(print_message, state)
        else:
            bot.send_message(message.from_user.id, 'Location not found.')
            bot.send_message(message.from_user.id, 'To start, send a location pin or enter your city:')
    else:
        bot.send_message(message.from_user.id, 'To start, send a location pin or enter your city:')

def check_if_location_exists(loc):
    try:
        qs = {'q': loc, 'appid': OWM_API_KEY}
        response = requests.get(API_URL, params=qs)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
    else:
        return response.status_code == 200

def show_commands(message):
    bot.send_message(message.from_user.id, '''/current - get the current weather for a location
/tomorrow - get a forecast for tomorrow
/forecast - get a 5-day forecast
/settings - change your preferences''')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.MAIN)
def main_handler(message):
    message_text = message.text.strip().lower()
    # if message_text in ['привет', 'hello', 'hi', 'hey']:
    #     bot.reply_to(message, f'Hi, {message.from_user.first_name}')
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
        states[message.from_user.id] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


def get_current_weather(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    try:
        # FIXME
        global querystring
        querystring = {
            'q': location,
            'lang': language.value,
            'units': units.value,
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
            bot.send_message(message.from_user.id,
                             f"Current weather in {city}, {country}: {temp}{DEGREE_SIGNS[units]}, {desc}")
        else:
            bot.send_message(message.from_user.id, response.json()['message'])
            show_location(message)
            # FIXME state
            states[message.from_user.id] = State.WELCOME


def get_tomorrow_weather(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    bot.send_message(message.from_user.id, f"Tomorrow\'s weather in {location}: XX")
    # TODO


def get_forecast(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    bot.send_message(message.from_user.id, f'5-day forecast for {location}: YY')
    # TODO


def show_settings(message):
    bot.send_message(
        message.from_user.id,
        f'''Settings:
/location - change your location. (Current location: {location})
/language - select a forecast language. (Current forecast language: {language.value})
/units - change your unit preferences. (Current units: {units.value})
/back - back to Weather''')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTINGS)
def settings_handler(message):
    message_text = message.text.strip().lower()
    if message_text == '/location':
        show_location(message)
        states[message.from_user.id] = State.SETTING_LOCATION
    elif message_text == '/language':
        show_language(message)
        states[message.from_user.id] = State.SETTING_LANGUAGE
    elif message_text == '/units':
        show_units(message)
        states[message.from_user.id] = State.SETTING_UNITS
    elif message_text == '/back':
        show_commands(message)
        states[message.from_user.id] = State.MAIN
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


def show_location(message):
    bot.send_message(
        message.from_user.id,
        f'Current location: {location}.\n/back - back to Settings\nSend a location pin or enter your city:')


def show_language(message):
    bot.send_message(message.from_user.id, f'Current forecast language: {language.value}.\n/back - back to Settings\nSelect a '
                                           f'forecast language: en | ru')


def show_units(message):
    bot.send_message(
        message.from_user.id,
        f'Current units: {units.value}.\n/back - back to Settings\nChoose metric or imperial:')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_LOCATION)
def setting_location_handler(message):
    message_text = message.text.strip()
    if message_text != '/back':
        # TODO check city, location pin
        if check_if_location_exists(message_text):
            global location
            location = message_text
            bot.send_message(message.from_user.id, f'Updated. Current city: {location}')
            show_settings(message)
            states[message.from_user.id] = State.SETTINGS
        else:
            bot.send_message(message.from_user.id, 'Location not found.')
            bot.send_message(message.from_user.id, 'To start, send a location pin or enter your city:')
    else:
        show_settings(message)
        states[message.from_user.id] = State.SETTINGS

@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'en', 'ru']:
        global language
        if message_text == 'en':
            # TODO extract method
            language = Language.ENGLISH
            bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        elif message_text == 'ru':
            language = Language.RUSSIAN
            bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        show_settings(message)
        states[message.from_user.id] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_UNITS)
def setting_units_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['/back', 'imperial', 'metric']:
        global units
        if message_text == 'metric':
            # TODO extract method
            units = Units.METRIC
            bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
        elif message_text == 'imperial':
            units = Units.IMPERIAL
            bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
        show_settings(message)
        states[message.from_user.id] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')

# @bot.message_handler(commands=['notifications'])
# def set_notifications(message):
#     bot.send_message(
#         message.from_user.id,
#         f'Enabled: {"Yes" if are_notifications_enabled else "No"}.\n" \
#         "Do you want to get daily notifications? Type Yes or No.')


# @bot.message_handler(func=lambda message: True)
# def other(message):
#     bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)

    bot.polling()
