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

# Constants
API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
LOCATION_DEFAULT = 'Moscow'


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


DEGREE_SIGNS = {Units.METRIC: '℃', Units.IMPERIAL: '℉'}

# Globals
units = Units.METRIC
language = Language.ENGLISH
location = LOCATION_DEFAULT
# are_notifications_enabled = False

bot = telebot.TeleBot(TOKEN)

states = {}

querystring = {
    'q': location,
    'units': units,
    'appid': OWM_API_KEY,
}


# @bot.message_handler(commands=['start', 'help'])
@bot.message_handler(commands=['start'])
def send_welcome(message):
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


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.WELCOME)
def welcome_handler(message):
    message_text = message.text.strip().lower()
    if message_text in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}.\nTo start, send a location pin or enter your city:')
        # states[message.from_user.id] = State.WELCOME
    else:
        # TODO check city
        bot.send_message(message.from_user.id, f'Current city: {location}')
        show_commands(message)
        states[message.from_user.id] = State.MAIN
        # TODO switch_to_state(print_message, state)


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
    elif message_text == '/tomorrow':
        get_tomorrow_weather(message)
    elif message_text == '/forecast':
        get_forecast(message)
    elif message_text == '/settings':
        show_settings(message)
        states[message.from_user.id] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


def get_current_weather(message):
    bot.send_chat_action(message.from_user.id, 'typing')
    try:
        response = requests.get(API_URL, params=querystring).json()
        city = response['city']['name']
        temp = int(round(response['list'][0]['main']['temp']))
        desc = response['list'][0]['weather'][0]['description']
        pprint(response)
        print(f"Current weather in {city}: {temp}, {desc}")
        bot.send_message(message.from_user.id,
                         f"Current weather in {location}: {temp}{DEGREE_SIGNS[units]}, {desc}")
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        bot.send_message(message.from_user.id, 'oops')


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
        '''Settings:
/location - change your location
/language - select a language
/units - change your unit preferences
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
        f'Current location: {location}.\nSend a location pin or enter your city:')


def show_language(message):
    bot.send_message(message.from_user.id, f'Current language: {language.value}.\nSelect a language: en | ru')


def show_units(message):
    bot.send_message(
        message.from_user.id,
        f'Current units: {units.value}.\nChoose metric or imperial:')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_LOCATION)
def setting_location_handler(message):
    # TODO check city
    bot.send_message(message.from_user.id, f'Updated. Current city: {message.text}')
    states[message.from_user.id] = State.SETTINGS


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_LANGUAGE)
def setting_language_handler(message):
    global language
    message_text = message.text.strip().lower()
    if message_text == 'en':
        language = Language.ENGLISH
        bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        states[message.from_user.id] = State.SETTINGS
    elif message_text == 'ru':
        language = Language.RUSSIAN
        bot.send_message(message.from_user.id, f'Updated. Current language: {language.value}.')
        states[message.from_user.id] = State.SETTINGS
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


@bot.message_handler(func=lambda message: states.get(message.from_user.id, State.MAIN) == State.SETTING_UNITS)
def setting_units_handler(message):
    global units
    message_text = message.text.strip().lower()
    if message_text == 'metric':
        units = Units.METRIC
        bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
        states[message.from_user.id] = State.SETTINGS
    elif message_text == 'imperial':
        units = Units.IMPERIAL
        bot.send_message(message.from_user.id, f'Updated. Current units: {units.value}.')
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
# def weather(message):
#     global units
#     # greetings = ['привет', 'hello', 'hi', 'hey']
#     # if any([g in message.text.strip().lower() for g in greetings]):
#     if message.text.strip().lower() in ['привет', 'hello', 'hi', 'hey']:
#         bot.reply_to(message, f'Hi, {message.from_user.first_name}.')
#     elif message.text.lower() == 'metric':
#         units = 'metric'
#         bot.send_message(message.from_user.id, f'Done. Updated units to {units}.')
#     elif message.text.lower() == 'imperial':
#         units = 'imperial'
#         bot.send_message(message.from_user.id, f'Done. Updated units to {units}.')
#     else:
#         bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')

if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)

    bot.polling()
