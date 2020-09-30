import os
import sys

from consts import TOKEN, OWM_API_KEY, REDIS_URL
from handlers import bot

if __name__ == '__main__':
    if TOKEN is None:
        sys.stderr.write('Error: BOT_TOKEN is not set.' + os.linesep)
        sys.exit(1)
    if OWM_API_KEY is None:
        sys.stderr.write('Error: OWM_API_KEY is not set.' + os.linesep)
        sys.exit(1)
    if REDIS_URL is None:
        sys.stderr.write('Warning: REDIS_URL is not set, using local DB.' + os.linesep)
    bot.polling()
