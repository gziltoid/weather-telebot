import random

from telebot import types as tt

from api import *
from consts import *
import handlers


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


def set_bot_commands(commands=()):
    handlers.bot.set_my_commands(commands)


def show_main_keyboard(user_id):
    set_bot_commands(BOT_MAIN_COMMANDS)
    handlers.bot.send_message(user_id, 'Choose one:', reply_markup=get_main_keyboard())


def show_current_settings(user_id):
    location = handlers.states[user_id].settings.location
    language = handlers.states[user_id].settings.language
    units = handlers.states[user_id].settings.units
    handlers.bot.send_message(
        user_id,
        f'Current: 📍 {location} | {LANGUAGE_SIGNS[language]} {language.value.title()} '
        f'| {UNITS_SIGNS[units]} {units.value}'
    )


def show_settings_keyboard(user_id):
    set_bot_commands()
    handlers.bot.send_message(
        user_id,
        f'Choose your preferences: ',
        reply_markup=get_settings_keyboard()
    )


def show_current_city(user_id):
    handlers.bot.send_message(user_id, f'📍 Current city: {handlers.states[user_id].settings.location}')


# FIXME split
def show_location_and_keyboard(user_id):
    handlers.bot.send_message(
        user_id,
        f'📍 Current location: {handlers.states[user_id].settings.location}.\n\n🐈 Enter your city:',
        reply_markup=get_select_location_keyboard()
    )


def show_language_and_keyboard(user_id):
    language = handlers.states[user_id].settings.language
    handlers.bot.send_message(
        user_id,
        f'Current: {LANGUAGE_SIGNS[language]} {language.value.title()}.\n\nChoose a forecast language:',
        reply_markup=get_select_language_keyboard()
    )


def show_units_and_keyboard(user_id):
    units = handlers.states[user_id].settings.units
    handlers.bot.send_message(
        user_id,
        f'Current: {UNITS_SIGNS[units]} {units.value}.\n\nChoose units:',
        reply_markup=get_select_units_keyboard()
    )


def reply_to_bad_command(message):
    handlers.bot.reply_to(message, random.choice(BAD_COMMAND_ANSWERS))


# TODO OWM API module, detailed report
def get_current_weather(user_id):
    handlers.bot.send_chat_action(user_id, 'typing')
    settings = handlers.states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        location_data, report = get_current_weather_from_response(response)
        if location_data is not None:
            units = handlers.states[user_id].settings.units
            message = f"<i>Current weather in {location_data.city}, {location_data.country}: " \
                      f"{report.temp}{DEGREE_SIGNS[units]}, {report.desc}</i>"
            handlers.bot.send_message(user_id, message, parse_mode='HTML')
            return
    handlers.bot.send_message(user_id, '⁉️ Server error. Please try again.')


def get_tomorrow_weather(user_id):
    handlers.bot.send_chat_action(user_id, 'typing')
    settings = handlers.states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = handlers.states[user_id].settings.units
        location_data, reports = get_tomorrow_weather_from_response(response)
        if location_data is not None:
            lines = [f"<u>{reports[0].datetime.strftime('%B %d')} - {location_data.city}, {location_data.country}:</u>"]
            for report in reports:
                lines.append(
                    f"<i><b>{report.datetime.strftime('%H:%M')}</b>: "
                    f"{report.temp}{DEGREE_SIGNS[units]}, {report.desc}</i>")
            handlers.bot.send_message(user_id, '\n'.join(lines), parse_mode='HTML')
            return
    handlers.bot.send_message(user_id, '⁉️ Server error. Please try again.')


def get_forecast(user_id):
    handlers.bot.send_chat_action(user_id, 'typing')
    settings = handlers.states[user_id].settings
    response = request_forecast(settings.location, settings.language.value, settings.units.value)
    if response is not None:
        units = handlers.states[user_id].settings.units
        location_data, reports = get_forecast_from_response(response)
        if location_data is not None:
            lines = [f'<u>4-day forecast for {location_data.city}, {location_data.country}:</u>']
            for report in reports:
                lines.append(
                    f"<i><b>{report.date.strftime('%b %d')}</b>: {report.min}-{report.max}{DEGREE_SIGNS[units]}, "
                    f"{report.desc}</i>")
            handlers.bot.send_message(user_id, '\n'.join(lines), parse_mode='HTML')
            return
    handlers.bot.send_message(user_id, '⁉️ Server error. Please try again.')
