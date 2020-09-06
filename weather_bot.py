import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests
from pprint import pprint

load_dotenv(find_dotenv())

# Environment variables
TOKEN = os.getenv('BOT_TOKEN', 'BOT_TOKEN does not exist.')
OWM_API_KEY = os.getenv('OWM_API_KEY', 'OWM_API_KEY does not exist.')

# Constants
UNITS_METRIC = 'metric'
UNITS_IMPERIAL = 'imperial'
UNITS = (UNITS_METRIC, UNITS_IMPERIAL)
DEGREE_SIGNS = {UNITS_METRIC: '℃', UNITS_IMPERIAL: '℉'}

LANGUAGE_ENGLISH = 'en'
LANGUAGE_RUSSIAN = 'ru'
LANGUAGES = [LANGUAGE_ENGLISH, LANGUAGE_RUSSIAN]

LOCATION_DEFAULT = 'Moscow'

# Globals

units = UNITS_METRIC
language = LANGUAGE_ENGLISH
location = LOCATION_DEFAULT
are_notifications_enabled = False

bot = telebot.TeleBot(TOKEN)

API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
querystring = {
    'q': location,
    'units': units,
    'appid': OWM_API_KEY,
}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        '''Hey, I'm the Weather Cat.
I can show you the weather forecast up to 5 days.
Just send me one of these commands:
/current - get the current weather for a location or city
/forecast - get a 5-day forecast for a location or city
/settings - change your preferences

To start, send a location pin or enter your area or city:
''')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.chat.id,
        '''What can I do?
Just send me one of these commands:
/current - get the current weather for a location or city
/forecast - get a 5-day forecast for a location or city
/settings - change your preferences
''')


@bot.message_handler(commands=['current'])
def get_current_weather(message):
    response = requests.get(API_URL, params=querystring).json()
    city = response['city']['name']
    temp = int(round(response['list'][0]['main']['temp']))
    desc = response['list'][0]['weather'][0]['description']
    # pprint(response)
    print(f"Current weather in {city}: {temp}, {desc}")
    bot.send_message(message.chat.id, f"Current weather in {city}: {temp}{DEGREE_SIGNS[units]}, {desc}")


@bot.message_handler(commands=['forecast'])
def get_forecast(message):
    bot.send_message(message.chat.id, '5-day forecast:')
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
    if str.lower(message.text).strip() in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}, type /start to begin')
    elif str.lower(message.text) == 'metric':
        units = 'metric'
        bot.send_message(message.chat.id, f'Done. Updated units to {units}.')
    elif str.lower(message.text) == 'imperial':
        units = 'imperial'
        bot.send_message(message.chat.id, f'Done. Updated units to {units}.')
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')
    # TODO


bot.polling()
