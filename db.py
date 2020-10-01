from collections import defaultdict

import redis

from consts import LOCAL_DB_PATH, REDIS_URL
from state import get_default_user_data, serialize, deserialize


def load_from_local_db():
    try:
        with open(LOCAL_DB_PATH, encoding='utf-8') as f:
            data = defaultdict(lambda: get_default_user_data(), deserialize(f.read()))
    except FileNotFoundError:
        data = defaultdict(lambda: get_default_user_data())
    return data


def load_db_from_redis():
    redis_db = redis.from_url(REDIS_URL)
    raw_data = redis_db.get('data')
    if raw_data is None:
        data = defaultdict(lambda: get_default_user_data())
    else:
        data = defaultdict(lambda: get_default_user_data(), deserialize(raw_data.decode('utf-8')))
    return data


def load_from_db():
    if REDIS_URL is None:
        print('Using Local DB.')
        return load_from_local_db()
    else:
        print('Using Redis.')
        return load_db_from_redis()


def save_state(states):
    if REDIS_URL is not None:
        redis_db = redis.from_url(REDIS_URL)
        redis_db.set('data', serialize(states))
    else:
        with open(LOCAL_DB_PATH, mode='w', encoding='utf-8') as f:
            f.write(serialize(states))
