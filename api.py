import os
import sys
from collections import Counter
from datetime import datetime, timedelta, tzinfo

import requests

from consts import OWM_API_KEY, API_URL
from state import LocationData, CurrentWeatherReport, TomorrowWeatherReport, ForecastWeatherReport


class SimpleTimezone(tzinfo):
    def __init__(self, offset):
        self.offset = offset

    def utcoffset(self, dt):
        return timedelta(seconds=self.offset)

    def dst(self, dt):
        return timedelta(0)


def check_if_location_exists(location):
    try:
        querystring = {'q': location, 'appid': OWM_API_KEY}
        response = requests.get(API_URL, params=querystring)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
    else:
        return response.status_code == 200


def request_forecast(location, language, units):
    querystring = {
        'q': location,
        'lang': language.short_name(),
        'units': units.value,
        'appid': OWM_API_KEY,
    }
    try:
        response = requests.get(API_URL, params=querystring)
    except Exception as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None
    if response.status_code == 200:
        return response.json()
    return None


# TODO change OWM API endpoint
def get_current_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        temp = int(round(response['list'][0]['main']['temp']))
        desc = response['list'][0]['weather'][0]['description']
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), CurrentWeatherReport(temp=temp, desc=desc)


def response_day_to_local_time(day, tzoffset):
    return datetime.fromtimestamp(int(day['dt']), tz=SimpleTimezone(tzoffset))


def get_tomorrow_weather_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        today = response_day_to_local_time(response['list'][0], tzoffset)
        tomorrow = (today + timedelta(days=+1))
        reports = []
        for interval in response['list']:
            dt = response_day_to_local_time(interval, tzoffset)
            if dt.day == today.day:
                continue
            elif dt.day == tomorrow.day:
                temp = int(round(interval['main']['temp']))
                desc = interval['weather'][0]['description']
                reports.append(TomorrowWeatherReport(datetime=dt, temp=temp, desc=desc))
            else:
                break
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), reports


def get_forecast_from_response(response):
    try:
        city = response['city']['name']
        country = response['city']['country']
        tzoffset = int(response['city']['timezone'])
        today = response_day_to_local_time(response['list'][0], tzoffset)
        reports = []
        days = []
        for i, interval in enumerate(response['list']):
            dt = response_day_to_local_time(interval, tzoffset)
            if dt.day == today.day:
                continue
            else:
                shift = 8
                for d in range(4):
                    days.append(response['list'][i + shift * d: i + shift * (d + 1)])
                break

        for day in days:
            dt = response_day_to_local_time(day[0], tzoffset)
            day_temps = []
            for interval in day:
                temp = int(round(interval['main']['temp']))
                desc = interval['weather'][0]['description']
                day_temps.append((temp, desc))

            min_temp = min(day_temps, key=lambda t_d: t_d[0])[0]
            max_temp = max(day_temps, key=lambda t_d: t_d[0])[0]
            day_desc = Counter(tup[1] for tup in day_temps).most_common(1)[0][0]
            reports.append(ForecastWeatherReport(date=dt, min=min_temp, max=max_temp, desc=day_desc))
    except ValueError as e:
        sys.stderr.write(f"Exception: {e}" + os.linesep)
        return None, None
    return LocationData(city=city, country=country), reports
