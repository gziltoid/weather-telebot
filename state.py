from collections import namedtuple
from dataclasses import dataclass
from enum import Enum


class Units(Enum):
    METRIC = 'metric'
    IMPERIAL = 'imperial'

    @classmethod
    def from_str(cls, label):
        if label == cls.METRIC.value:
            return cls.METRIC
        elif label == cls.IMPERIAL.value:
            return cls.IMPERIAL
        else:
            raise NotImplementedError


class Language(Enum):
    ENGLISH = 'english'
    RUSSIAN = 'russian'

    @classmethod
    def from_str(cls, label):
        if label == cls.ENGLISH.value:
            return cls.ENGLISH
        elif label == cls.RUSSIAN.value:
            return cls.RUSSIAN
        else:
            raise NotImplementedError

    def short_name(self):
        return self.value[:2]


class State(Enum):
    MAIN = 0
    WELCOME = 1
    SETTINGS = 2
    SETTING_LOCATION = 3
    SETTING_LANGUAGE = 4
    SETTING_UNITS = 5

    @classmethod
    def from_int(cls, label):
        if label in range(7):
            return cls(label)
        else:
            raise NotImplementedError


@dataclass
class Settings:
    location: str
    language: Language
    units: Units


@dataclass
class UserData:
    state: State
    settings: Settings


def get_default_user_data():
    return UserData(
        state=State.WELCOME,
        settings=Settings(
            location='',
            language=Language.ENGLISH,
            units=Units.METRIC)
    )


LocationData = namedtuple('LocationData', 'city country')
CurrentWeatherReport = namedtuple('CurrentWeatherReport', 'temp desc')
TomorrowWeatherReport = namedtuple('TomorrowWeatherReport', 'datetime temp desc')
ForecastWeatherReport = namedtuple('ForecastWeatherReport', 'date min max desc')


def serialize(states):
    lines = []
    for id_, user_data in states.items():
        state = user_data.state.value
        location = user_data.settings.location
        language = user_data.settings.language.value
        units = user_data.settings.units.value
        lines.append(f'{id_}|{state}|{location}|{language}|{units}')
    return '\n'.join(lines)


def deserialize(s):
    states = {}
    lines = s.splitlines()
    for line in lines:
        id_, state, loc, lang, units = line.split('|')
        states[int(id_)] = UserData(
            state=State.from_int(int(state)),
            settings=Settings(
                location=loc,
                language=Language.from_str(lang),
                units=Units.from_str(units)
            )
        )
    return states


def test_serialization():
    data0 = get_default_user_data()
    data1 = get_default_user_data()
    data0.settings.location = 'Москва'
    data0.state = State.FORECAST
    data0.settings.units = Units.IMPERIAL
    data1.settings.location = 'San Jose'
    data1.state = State.MAIN
    data1.settings.language = Language.RUSSIAN

    states = {123: data0, 456: data1}
    encoded = serialize(states)
    decoded = deserialize(encoded)
    assert (states == decoded)
