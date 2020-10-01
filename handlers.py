import telebot

from db import load_from_db, save_state
from handler_utils import *
from state import State

bot = telebot.TeleBot(TOKEN)
states = load_from_db()


def start_polling():
    bot.polling(none_stop=True)


@bot.callback_query_handler(func=lambda call: states[call.from_user.id].state == State.SETTING_LOCATION)
def setting_location_callback_handler(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    bot.delete_message(user_id, message_id)
    switch_to_state(user_id, State.SETTINGS)


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
    switch_to_state(user_id, State.SETTINGS)


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
    switch_to_state(user_id, State.SETTINGS)


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
    switch_to_state(user_id, State.WELCOME)


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
        switch_to_state(user_id, State.MAIN)
    else:
        bot.send_message(
            user_id,
            '⚠️ Location not found.\n\n🐈 To start, enter your city:'
        )


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
        switch_to_state(user_id, State.SETTINGS)
    else:
        reply_to_bad_command(message)


@bot.message_handler(func=lambda message: states[message.from_user.id].state == State.SETTINGS)
def settings_handler(message):
    user_id = message.from_user.id
    message_text = message.text.strip()
    if message_text == KeyboardButton.LOCATION.value:
        show_current_location(user_id)
        switch_to_state(user_id, State.SETTING_LOCATION)
    elif message_text == KeyboardButton.LANGUAGE.value:
        show_current_language(user_id)
        switch_to_state(user_id, State.SETTING_LANGUAGE)
    elif message_text == KeyboardButton.UNITS.value:
        show_current_units(user_id)
        switch_to_state(user_id, State.SETTING_UNITS)
    elif message_text == KeyboardButton.BACK.value:
        show_current_location(user_id)
        switch_to_state(user_id, State.MAIN)
    else:
        reply_to_bad_command(message)


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
            disable_notification=True,
            reply_markup=get_select_location_keyboard()
        )
        return
    switch_to_state(user_id, State.SETTINGS)


@bot.message_handler(func=lambda msg: states[msg.from_user.id].state in (State.SETTING_LANGUAGE, State.SETTING_UNITS))
def setting_language_or_units_handler(message):
    reply_to_bad_command(message)
