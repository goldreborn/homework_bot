from typing import Any
from os import getenv
import time
from http import HTTPStatus
import requests

from pprint import pprint
from dotenv import load_dotenv
from telegram import Bot
import logging
from json import JSONDecodeError

from error_handler import TokenError, ResponseError


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
    """Проверяем наличие токенов."""
    logging.info('Проверка наличия токенов...')

    if any([x is None for x in tokens]):

        logging.critical('Отсутствуют обязательные переменные окружения')

        raise TokenError(
            'Ошибка. Отсутствуют или неверно указаны токены'
        )


def send_message(bot: Bot, message: str) -> None:
    """Отправляем сообщение из бота."""
    logging.info('Пробуем отправить сообщение...')

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as err:
        logging.error(
            f'Боту не удалось отправить сообщение-ошибка{err}'
        )
    else:
        logging.debug(
            f'{bot.__class__.__name__} отправил сообщение {message}'
        )
    finally:
        logging.info('Совершена попытка отправить сообщение')


def get_api_answer(timestamp: int) -> Any:
    """Пробуем получить ответ от апи."""
    logging.info('Пробуем отправить запрос к api...')

    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={
                'from_date': timestamp
            })
        if response.status_code != HTTPStatus.OK:
            raise ResponseError
    except JSONDecodeError as error:
        logging.error(
            f'Ошибка {error}'
        )
    except requests.RequestException as error:
        logging.error(
            f'Ошибка {error}'
        )
        raise ResponseError
    else:
        return response.json()


def check_response(response: Any) -> dict:
    """Проверяем что данные совпадают ожидаемым типам."""
    logging.info('Проверка соответствия объектов классу...')

    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(
            'Не найдены данные по ключю homeworks'
        )

    if not isinstance(homeworks, list):
        raise TypeError(
            'Ошибка. Все домашки должны передаваться в списке'
        )
    elif any(not isinstance(x, dict) for x in homeworks):
        raise TypeError(
            'Ошибка. Каждая домашка должна передаваться в словаре'
        )
    else:
        return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус работы."""
    name = homework.get('homework_name')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS.keys():
        raise KeyError
    elif 'homework_name' not in homework:
        raise KeyError
    return 'Изменился статус проверки работы "{n}". {v}'.format(
        n=name,
        v=HOMEWORK_VERDICTS[status]
    )


def main() -> None:
    """Главный метод, вызывается стразу при запуске всего кода."""
    check_tokens((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = 1549962000

    while True:

        try:
            response = get_api_answer(timestamp)
            pprint(response)
        except Exception as error:
            print(f'Произошла ошибка: {error}')
        else:
            homeworks = check_response(response)

            if homeworks is not None:
                send_message(bot=bot, message=parse_status(homeworks[0]))
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
