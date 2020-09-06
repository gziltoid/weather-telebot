import os
import telebot
from dotenv import load_dotenv, find_dotenv
import requests

load_dotenv(find_dotenv())
TOKEN = os.getenv('BOT_TOKEN', 'BOT_TOKEN does not exist.')

UNITS = 'metric'
LOCATION = 'Moscow'
LANGUAGE = 'en'
GET_NOTIFICATIONS = False

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        '''Hey! I'm the Weather Cat.
I can show you the weather forecast up for 5 days.
/help - view available commands

To start, send a location pin or enter your area or city:
'''
    )


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.chat.id,
        '''What can I do?
Just send me one of these commands:
/current - get the current weather for a location or city
/weatherfull - get a 5-day forecast for a location or city
/settings - change your preferences
''')


@bot.message_handler(commands=['current'])
def get_current_weather(message):
    bot.send_message(message.chat.id, 'Current weather:')


@bot.message_handler(commands=['weatherfull'])
def get_forecast(message):
    bot.send_message(message.chat.id, '5-day forecast:')


@bot.message_handler(commands=['settings'])
def show_settings(message):
    bot.send_message(
        message.chat.id,
        '''Settings:
/changelocation - set or change your location
/lang - select a language
/units - change your unit preferences
/notifications - enable notifications'''
    )


@bot.message_handler(commands=['changelocation'])
def change_location(message):
    bot.send_message(
        message.chat.id,
        f'Current location: {LOCATION}.\nSend location pin or enter your area or city:')


@bot.message_handler(commands=['lang'])
def change_language(message):
    bot.send_message(message.chat.id, f'Current language: {LANGUAGE}.\nSelect a language:')


@bot.message_handler(commands=['units'])
def change_units(message):
    bot.send_message(
        message.chat.id,
        f'Current units: {UNITS}.\nIf you want to change it, please type metric or imperial:')


@bot.message_handler(commands=['notifications'])
def set_notifications(message):
    bot.send_message(
        message.chat.id,
        f'Enabled: {"Yes" if GET_NOTIFICATIONS else "No"}.\nDo you want to get daily notifications? Type Yes or No.')


@bot.message_handler(func=lambda message: True)
def weather(message):
    global UNITS
    # greetings = ['привет', 'hello', 'hi', 'hey']
    # if any([g in str.lower(message.text) for g in greetings]):
    if str.lower(message.text).strip() in ['привет', 'hello', 'hi', 'hey']:
        bot.reply_to(message, f'Hi, {message.from_user.first_name}')
    elif str.lower(message.text) == 'metric':
        UNITS = 'metric'
        bot.send_message(message.chat.id, f'Done. Updated units to {UNITS}.')
    elif str.lower(message.text) == 'imperial':
        UNITS = 'imperial'
        bot.send_message(message.chat.id, f'Done. Updated units to {UNITS}.')
    else:
        bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


# @bot.message_handler(func=lambda message: True)
# def echo_all(message):
#     bot.reply_to(message, 'Sorry, I didn\'t get what you mean.')


bot.polling()
