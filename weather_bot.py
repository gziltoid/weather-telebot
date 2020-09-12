import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests
from pprint import pprint
import sys

load_dotenv(find_dotenv())

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
OWM_API_KEY = os.getenv('OWM_API_KEY')

# Constants
API_URL = 'https://api.openweathermap.org/data/2.5/forecast'

UNITS_METRIC = 'metric'
UNITS_IMPERIAL = 'imperial'
UNITS = (UNITS_METRIC, UNITS_IMPERIAL)
DEGREE_SIGNS = {UNITS_METRIC: '℃', UNITS_IMPERIAL: '℉'}

LANGUAGE_ENGLISH = 'en'
LANGUAGE_RUSSIAN = 'ru'
LANGUAGES = [LANGUAGE_ENGLISH, LANGUAGE_RUSSIAN]

LOCATION_DEFAULT = 'Moscow'

MAIN_STATE = 'main'
WEATHER_DATE_STATE = 'weather_date_handler'

# Globals
units = UNITS_METRIC
language = LANGUAGE_ENGLISH
location = LOCATION_DEFAULT
are_notifications_enabled = False

bot = telebot.TeleBot(TOKEN)

states = {}

querystring = {
    'q': location,
    'units': units,
    'appid': OWM_API_KEY,
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        '''Hey, I'm the Weather Cat.
I can show you a weather forecast up to 5 days.
Just send me one of these commands:
/current - get the current weather for a location or city
/tomorrow - get a forecast for tomorrow
/forecast - get a 5-day forecast
/settings - change your preferences

To start, send a location pin or enter your area or city:
''')

# @bot.message_handler(func=lambda message: states.get(message.from_user.id, MAIN_STATE) == MAIN_STATE)
# def main_handler(message):
#     if str.lower(message.text).strip() in ['привет', 'hello', 'hi', 'hey']:
#         bot.reply_to(message, f'Hi, {message.from_user.first_name}')
#     else:
#         bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')
#     # TODO


@bot.message_handler(commands=['current'])
def get_current_weather(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = requests.get(API_URL, params=querystring).json()
        city = response['city']['name']
        temp = int(round(response['list'][0]['main']['temp']))
        desc = response['list'][0]['weather'][0]['description']
        pprint(response)
        print(f"Current weather in {city}: {temp}, {desc}")
        bot.send_message(message.chat.id, f"Current weather in {city}: {temp}{DEGREE_SIGNS[units]}, {desc}")
    except BaseException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        bot.send_message(message.chat.id, 'oops')
    states[message.from_user.id] = MAIN_STATE

@bot.message_handler(commands=['tomorrow'])
def get_tomorrow_weather(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, 'Tomorrow\'s weather:')
    states[message.from_user.id] = MAIN_STATE
    # TODO

@bot.message_handler(commands=['forecast'])
def get_forecast(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, '5-day forecast:')
    states[message.from_user.id] = MAIN_STATE
    # TODO


@bot.message_handler(commands=['settings'])
def show_settings(message):
    bot.send_message(
        message.chat.id,
        '''Settings:
/location - set or change your location
/lang - select a language
/units - change your unit preferences
/notifications - enable or disable notifications
''')


@bot.message_handler(commands=['location'])
def change_location(message):
    bot.send_message(
        message.chat.id,
        f'Current location: {location}.\nSend location pin or enter your area or city:')
    # TODO


@bot.message_handler(commands=['lang'])
def change_language(message):
    bot.send_message(message.chat.id, f'Current language: {language}.\nSelect a language:')
    # TODO


@bot.message_handler(commands=['units'])
def change_units(message):
    bot.send_message(
        message.chat.id,
        f'Current units: {units}.\nIf you want to change it, please type metric or imperial:')
    # TODO


@bot.message_handler(commands=['notifications'])
def set_notifications(message):
    bot.send_message(
        message.chat.id,
        f'Enabled: {"Yes" if are_notifications_enabled else "No"}.\nDo you want to get daily notifications? Type Yes or No.')
    # TODO


@bot.message_handler(func=lambda message: True)
def weather(message):
    global units
    # greetings = ['привет', 'hello', 'hi', 'hey']
    # if any([g in message.text.strip().lower() for g in greetings]):
    if message.text.strip().lower() in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}.')
    elif message.text.lower() == 'metric':
        units = 'metric'
        bot.send_message(message.chat.id, f'Done. Updated units to {units}.')
    elif message.text.lower() == 'imperial':
        units = 'imperial'
        bot.send_message(message.chat.id, f'Done. Updated units to {units}.')
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')
    # TODO


if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)

    bot.polling()
