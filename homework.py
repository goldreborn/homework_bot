import requests
import time
from typing import Any
from os import getenv
from http import HTTPStatus
from sys import stdout

import logging
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from error_handler import ResponseError


load_dotenv()

PRACTICUM_TOKEN = getenv('practicum_token')
TELEGRAM_TOKEN = getenv('telegram_token')
TELEGRAM_CHAT_ID = getenv('telegram_chat_id')

TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID',)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверяем наличие токенов."""
    logging.info('Проверка наличия токенов...')

    for token in TOKENS:

        if not globals()[token]:

            logging.critical(
                f'Критическая ошибка. Отсутствуют токены {token}'
            )
            return False

    return True


def send_message(bot: Bot, message: str) -> None:
    """Отправляем сообщение из бота."""
    logging.info('Пробуем отправить сообщение...')

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except TelegramError as err:
        logging.error(
            f'Боту не удалось отправить сообщение-ошибка{err}'
        )
    else:
        logging.debug(
            f'{bot.__class__.__name__} отправил сообщение {message}'
        )


def get_api_answer(timestamp: int) -> Any:
    """Пробуем получить ответ от апи."""
    logging.info('Пробуем отправить запрос к api...')

    try:
        payload = {'from_date': timestamp}
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:

        raise ConnectionError(
            (
                f'Ошибка {error} при попытке отправить запрос на сервер api'
                f'| url={ENDPOINT} | headers=HEADERS | params={payload}'
            )
        )
    if response.status_code != HTTPStatus.OK:
        raise ResponseError(
            f'Ошибка. Код ответа {response.status_code}'
            f'Причина {response.reason}'
        )

    return response.json()


def check_response(response: Any) -> list:
    """Проверяем что данные совпадают ожидаемым типам."""
    logging.info('Проверка соответствия объектов классу...')

    if not isinstance(response, dict):
        raise TypeError(
            f'Ошибка. Полученный объект response не типа {type(dict)}'
        )

    if 'current_date' not in response:
        raise KeyError(
            'Ошибка. Отсутствует дата по ключю current_date'
        )

    if 'homeworks' not in response:
        raise KeyError(
            'Ошибка. Не найден ключ homeworks'
        )

    homeworks = response['homeworks']

    if not isinstance(homeworks, list):
        raise TypeError(
            f'Ошибка. Домашки должны быть в списке, а не {type(homeworks)}'
        )
    logging.info('Закончил проверку на совпадение типа данных')

    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Извлекает из информации о домашней работе статус работы."""
    logging.info('Начал проверку статуса работы...')

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not status:
        raise KeyError(
            'Отсутствует статус по ключю status в запрашиваемой работе'
        )

    if status not in HOMEWORK_VERDICTS.keys():
        raise KeyError(
            f'Отсутствует статус {status} по ключю status в словаре вердиктов'
        )

    if 'homework_name' not in homework:
        raise KeyError(
            'Отсутствует имя по ключю homework_name в запрашиваемой работе'
        )

    logging.info('Окончил проверку статуса работы')

    return 'Изменился статус проверки работы "{name}". {verdict}'.format(
        name=homework_name,
        verdict=HOMEWORK_VERDICTS[status]
    )


def main() -> None:
    """Главный метод, вызывается стразу при запуске всего кода."""
    if not check_tokens():

        logging.critical('Отсутствуют обязательные переменные окружения')

        exit()

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    last_error = None

    while True:

        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                send_message(bot=bot, message=parse_status(homeworks[0]))
                last_error = None
            else:
                logging.debug(
                    'Отсутствуют новые статусы работ'
                )
            timestamp = response.get('current_date')
        except Exception as error:
            if last_error != error:
                last_error = error
            logging.error(
                f'Ошибка {error}', exc_info=True
            )
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s - %(levelname)s - %(message)s'
            '%(name)s - %(funcName)s - %(lineno)s'
        ),
        handlers=[
            logging.StreamHandler(stdout),
            logging.FileHandler(f'{__file__}.log', encoding='utf-8')
        ]
    )

    main()
