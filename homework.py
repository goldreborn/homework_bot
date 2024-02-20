from pprint import pprint
from os import getenv
from dotenv import load_dotenv
from error_handler import TokenError, ResponseError
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)
from telegram import Bot, ReplyKeyboardMarkup, Update
import logging
import requests as req
from requests.exceptions import RequestException
from datetime import datetime
from http.client import HTTPResponse


load_dotenv()

PRACTICUM_TOKEN = getenv('practicum_token')
TELEGRAM_TOKEN = getenv('telegram_token')
TELEGRAM_CHAT_ID = getenv('telegram_chat_id')

PRACTICUM_BORN_DATE = 1549962000
RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PARAMS = {'from_date': PRACTICUM_BORN_DATE}

BUTTON_TEXT = 'Жмяк'
STARTED_QUEUE_TEXT = 'Начал следить за статусом твоей работы'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

queue_running = False


def check_tokens() -> None:

    if any(
        [
            x is None for x in (
                PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
            )
        ]
    ):
        raise TokenError(
            ('Ошибка, токен не существует'),
            ('или не получилось взять его из файла .env')
        )


def send_message(bot: Bot, message: str) -> None:

    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(timestamp: int) -> dict | None:

    try:
        response = req.get(
            url=ENDPOINT, headers=HEADERS, params={
                'from_date': timestamp
            }
        )
    except RequestException:

        logging.error(f'Ошибка {response.status_code}')
        raise ResponseError(
            ('Ошибка, не удалось подключится к api'),
            (f'Код ошибки {response.status_code}'),
            (f'Время {datetime.now()}')
        )
    else:
        logging.info(
            ('Получил json данные из response'),
            (f'Время {datetime.now()}')
        )
        return response.json()
    finally:
        logging.info(
            ('Успешно'),
            ('Произошёл запрос к api'),
            (f'Время {datetime.now()}')
        )


def check_response(response: HTTPResponse) -> None:

    if response is not None:
        pass


def parse_status(homework: dict) -> str | None:

    if any([x == homework['status'] for x in HOMEWORK_VERDICTS.keys()]):

        logging.info(
            ('Статус работы изменён'),
            (f'Время {datetime.now()}')
        )
        return 'Изменился статус проверки работы "{name}". {verdict}'.format(
            name=homework['lesson_name'],
            verdict=HOMEWORK_VERDICTS[homework['status']]
        )
    else:
        return None


def handle_text(update: Update, context: CallbackContext) -> None:

    global queue_running

    if update.message.text == BUTTON_TEXT and not queue_running:
        context.bot.send_message(
            chat_id=update.effective_chat,
            text=STARTED_QUEUE_TEXT
        )
        queue_running = True
    elif update.message.text == BUTTON_TEXT and queue_running:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Проверка домашнего задания уже активирована'
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Неизвестная команда'
        )


def start(update: Update, context: CallbackContext) -> None:

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Привет, я твой бот который будет проверять состояние домашки',
        reply_markup=ReplyKeyboardMarkup(
            [[
                BUTTON_TEXT
            ]]
        )
    )


def main():

    response = req.get(url=ENDPOINT, headers=HEADERS, params=PARAMS)

    pprint(response.json())

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    updater = Updater(token=TELEGRAM_TOKEN)
    updater.start_polling(poll_interval=float(RETRY_PERIOD))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text))



if __name__ == '__main__':
    main()