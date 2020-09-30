import random

import telebot
from telebot import types as tt

from api import *
from consts import *
from db import load_from_db, save_state
from state import State

# Globals
bot = telebot.TeleBot(TOKEN)
states = load_from_db()

def remove_reply_keyboard():
    return tt.ReplyKeyboardRemove(selective=False)


def get_main_keyboard():
    main_buttons = [item.value for item in MAIN_KEYBOARD]
    markup = tt.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*main_buttons)
    return markup


def get_settings_keyboard():
    settings_buttons = [item.value for item in SETTINGS_KEYBOARD]
    markup = tt.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add(settings_buttons[0])
    markup.row(*settings_buttons[1:3])
    markup.add(settings_buttons[3])
    return markup


def get_select_location_keyboard():
    markup = tt.InlineKeyboardMarkup()
    markup.add(
        tt.InlineKeyboardButton(
            text=SETTING_LOCATION_KEYBOARD.value,
            callback_data=SETTING_LOCATION_KEYBOARD.value
        )
    )
    return markup


def get_select_language_keyboard():
    markup = tt.InlineKeyboardMarkup(row_width=2)
    buttons = [
        tt.InlineKeyboardButton(text=btn.value, callback_data=btn.value) for btn in SETTING_LANGUAGE_KEYBOARD
    ]
    markup.add(*buttons)
    return markup


def get_select_units_keyboard():
    markup = tt.InlineKeyboardMarkup(row_width=2)
    buttons = [
        tt.InlineKeyboardButton(text=btn.value, callback_data=btn.value) for btn in SETTING_UNITS_KEYBOARD
    ]
    markup.add(*buttons)
    return markup


@bot.callback_query_handler(func=lambda call: states[call.from_user.id].state == State.SETTING_LOCATION)
def setting_location_callback_handler(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    states[user_id].state = State.SETTINGS
    save_state()
    bot.delete_message(user_id, message_id)
    show_settings_keyboard(user_id)


@bot.callback_query_handler(func=lambda call: states[call.from_user.id].state == State.SETTING_LANGUAGE)
def setting_language_callback_handler(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    if call.data != KeyboardButton.BACK.value:
        language = Language.ENGLISH if call.data == KeyboardButton.ENGLISH.value else Language.RUSSIAN
        states[user_id].settings.language = language
        bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=f'✔️ Updated. Current language: {LANGUAGE_SIGNS[language]} {language.value.title()}.',
            reply_markup=None
        )
        bot.answer_callback_query(call.id, show_alert=False, text='Updated.')
        show_current_settings(user_id)
    else:
        bot.delete_message(user_id, message_id)
    states[user_id].state = State.SETTINGS
    save_state()
    show_settings_keyboard(user_id)


@bot.callback_query_handler(func=lambda call: states[call.from_user.id].state == State.SETTING_UNITS)
def setting_units_callback_handler(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    if call.data != KeyboardButton.BACK.value:
        units = Units.METRIC if call.data == KeyboardButton.METRIC.value else Units.IMPERIAL
        states[user_id].settings.units = units
        bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=f'✔️ Updated. Current units: {UNITS_SIGNS[units]} {units.value}.',
            reply_markup=None
        )
        bot.answer_callback_query(call.id, show_alert=False, text='Updated.')
        show_current_settings(user_id)
    else:
        bot.delete_message(user_id, message_id)
    states[user_id].state = State.SETTINGS
    save_state()
    show_settings_keyboard(user_id)

def set_bot_commands(commands=()):
    bot.set_my_commands(commands)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    set_bot_commands()
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        "Hey, I'm the Weather Cat 🐱\nI can show you a weather forecast up to 4 days 🐾",
        reply_markup=remove_reply_keyboard()
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
        states[user_id].state = State.MAIN
        save_state()
        show_main_keyboard(user_id)
    else:
        bot.send_message(
            user_id,
            '⚠️ Location not found.\n\n🐈 To start, enter your city:'
        )


def show_main_keyboard(user_id):
    set_bot_commands(BOT_MAIN_COMMANDS)
    bot.send_message(user_id, 'Choose one:', reply_markup=get_main_keyboard())


def reply_to_bad_command(message):
    bot.reply_to(message, random.choice(BAD_COMMAND_ANSWERS))


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.MAIN)
def main_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text in (Command.CURRENT.value, KeyboardButton.CURRENT.value):
        get_current_weather(user_id)
    elif message_text in (Command.TOMORROW.value, KeyboardButton.TOMORROW.value):
        get_tomorrow_weather(user_id)
    elif message_text in (Command.FORECAST.value, KeyboardButton.FORECAST.value):
        get_forecast(user_id)
    elif message_text in (Command.SETTINGS.value, KeyboardButton.SETTINGS.value):
        show_current_settings(user_id)
        show_settings_keyboard(user_id)
        states[user_id].state = State.SETTINGS
        save_state()
    else:
        reply_to_bad_command(message)


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
                lines.append(
                    f"<i><b>{report.datetime.strftime('%H:%M')}</b>: {report.temp}{DEGREE_SIGNS[units]}, {report.desc}</i>")
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
                    f"<i><b>{report.date.strftime('%b %d')}</b>: {report.min}-{report.max}{DEGREE_SIGNS[units]}, "
                    f"{report.desc}</i>")
            bot.send_message(user_id, '\n'.join(lines), parse_mode='HTML')
            return
    bot.send_message(user_id, '⁉️ Server error. Please try again.')


def show_current_settings(user_id):
    location = states[user_id].settings.location
    language = states[user_id].settings.language
    units = states[user_id].settings.units
    bot.send_message(
        user_id,
        f'Current: 📍 {location} | {LANGUAGE_SIGNS[language]} {language.value.title()} '
        f'| {UNITS_SIGNS[units]} {units.value}'
    )


def show_settings_keyboard(user_id):
    set_bot_commands()
    bot.send_message(
        user_id,
        f'Choose your preferences: ',
        reply_markup=get_settings_keyboard()
    )


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTINGS)
def settings_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text == KeyboardButton.LOCATION.value:
        show_location_and_keyboard(user_id)
        states[user_id].state = State.SETTING_LOCATION
        save_state()
    elif message_text == KeyboardButton.LANGUAGE.value:
        show_language_and_keyboard(user_id)
        states[user_id].state = State.SETTING_LANGUAGE
        save_state()
    elif message_text == KeyboardButton.UNITS.value:
        show_units_and_keyboard(user_id)
        states[user_id].state = State.SETTING_UNITS
        save_state()
    elif message_text == KeyboardButton.BACK.value:
        show_current_city(user_id)
        show_main_keyboard(user_id)
        states[user_id].state = State.MAIN
        save_state()
    else:
        reply_to_bad_command(message)


def show_current_city(user_id):
    bot.send_message(user_id, f'📍 Current city: {states[user_id].settings.location}')

# FIXME split
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
        f'Current: {LANGUAGE_SIGNS[language]} {language.value.title()}.\n\nChoose a forecast language:',
        reply_markup=get_select_language_keyboard()
    )


def show_units_and_keyboard(user_id):
    units = states[user_id].settings.units
    bot.send_message(
        user_id,
        f'Current: {UNITS_SIGNS[units]} {units.value}.\n\nChoose units:',
        reply_markup=get_select_units_keyboard()
    )


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTING_LOCATION)
def setting_location_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if check_if_location_exists(message_text):
        states[user_id].settings.location = message_text.title()
        location = states[user_id].settings.location
        bot.send_message(user_id, f'✔️ Updated. Current city: {location}')
        show_current_settings(user_id)
    else:
        bot.delete_message(user_id, message.message_id - 1)
        bot.send_message(
            user_id,
            '⚠️ Location not found.\n\n🐈 Enter your city:',
            reply_markup=get_select_location_keyboard()
        )
        return
    states[user_id].state = State.SETTINGS
    save_state()
    show_settings_keyboard(user_id)


@bot.message_handler(func=lambda message: states[message.from_user.id].state in (State.SETTING_LANGUAGE, State.SETTING_UNITS))
def setting_language_or_units_handler(message):
    reply_to_bad_command(message)
