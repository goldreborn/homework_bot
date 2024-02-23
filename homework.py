from os import getenv
from urllib3.response import HTTPResponse
import time

from pprint import pprint
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram import TelegramError
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests
import logging

from error_handler import *


load_dotenv()

PRACTICUM_TOKEN = getenv('practicum_token')
TELEGRAM_TOKEN = getenv('telegram_token')
TELEGRAM_CHAT_ID = getenv('telegram_chat_id')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logging.getLogger(__name__).addHandler(
    logging.StreamHandler()
)


def check_tokens(tokens: tuple) -> None:
    """Проверяем наличие токенов"""

    logging.info('Проверка наличия токенов...')

    if any([x is None for x in tokens]):
        raise TokenError(
            'Ошибка. Отсутствуют или неверно указаны токены'
        )


def send_message(bot: Bot, message: str) -> None:
    """Отправляем сообщение из бота"""

    logging.info('Пробуем отправить сообщение...')

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error(
            f'Боту не удалось отправить сообщение-ошибка{error}'
        )
    else:
        logging.info(
            f'{bot.__class__.__name__} отправил сообщение {message}'
        )
    finally:
        logging.info('Совершена попытка отправить сообщение')
    

def get_api_answer(timestamp: int) -> HTTPResponse:
    """Пробуем получить ответ от апи"""
    logging.info('Пробуем отправить запрос к api...')

    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={
                'from_date': timestamp
            })
        return response
    except requests.exceptions.HTTPError as error:
        logging.error(
            f'Ошибка {error}. Код ответа {response.status_code}'
        )


def check_response(response: HTTPResponse) -> dict | None:
    """Проверяем что данные совпадают ожидаемым типам"""
    logging.info('Проверка соответствия объектов классу...')

    homeworks = response.json()

    if not isinstance(homeworks, list):
        raise TypeError(
            'Ошибка. Все домашки должны передаваться в списке'
        )
    elif any(not isinstance(x, dict) for x in homeworks):
        raise TypeError(
            'Ошибка. Каждая домашка должна передаваться в словаре'
        )
    elif 'homeworks' not in homeworks:
        raise KeyError(
            'Не найдены данные по ключю homeworks'
        )
    else:
        return homeworks


def parse_status(homework: dict) -> str | None:
    """
    Проверяем статус работы, если ключ из словаря совпадает
    со статусом, возвращаем значение
    """
    if any([x == homework['status'] for x in HOMEWORK_VERDICTS.keys()]):
        logging.info(
            'Статус работы изменён'
        )
        return 'Изменился статус проверки работы "{name}". {verdict}'.format(
            name=homework['lesson_name'],
            verdict=HOMEWORK_VERDICTS[homework['status']]
        )
    else:
        return None


def start(updat: Update, context: CallbackContext) -> None:
    """Действие после отправки команды старт"""

    try:
        send_message(
            bot=context.bot,
            message='Привет, я бот который проверяет статус твоей работы'
        )
    except TelegramError as error:
        logging.error(
            f'Ошибка {error}. Бот не смог отправить сообщение'
        )
    else:
        logging.info('Сообщение успешно отправлено')
    finally:
        logging.info('Совершена попытка отправить сообщение')


def main() -> None:
    """Главный метод, вызывается стразу при запуске всего кода"""
    check_tokens((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = time.time()

    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.start_polling()
    updater.idle()

    while True:

        try:
            response = get_api_answer(timestamp)
            pprint(response.json())
        except Exception as error:
            print(f'Произошла ошибка: {error}')
        else:
            homeworks = check_response(response)

            if len(homeworks) != 0:
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=parse_status(homeworks[0])
                )

        time.sleep(RETRY_PERIOD)

    
if __name__ == '__main__':
    main()
