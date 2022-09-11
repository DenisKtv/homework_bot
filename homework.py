import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HTTPStatusNotOK, MessageNotSend

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def send_message(bot, message):
    """Отправка сообщения."""
    logging.info(f'Бот начал отправку сообщения: {message}.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение: {message} -  отправлено!')
    except MessageNotSend as error:
        message = (f'Отправка сообщения не удалась! По причине {error}')
        logging.error(message)


def get_api_answer(current_timestamp):
    """Получаем ответ от Практикум API."""
    logging.info('Подключение к Практикум API.')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise HTTPStatusNotOK('Соединение недоступно!')
    return response.json()


def check_response(response):
    """Проверка правильности формата ответа от Практикум API."""
    logging.info('Проверяем ответ на правильность формата.')
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных, ожидается dict!')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('Данные приходят не в виде списка в ответ от API')
    elif 'homeworks' not in response:
        logging.error('Ключ отсутствует в response API')
        raise KeyError('Ключ отсутствует в response API')
    return response['homeworks']


def parse_status(homework):
    """Получаем статус домашней работы."""
    logging.info('Извлекаем данные о домашней работе.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Неверный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных среды."""
    logging.info('Проверка токенов.')
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует токен!')
        sys.exit('Отсутствует токен!')

    status_message = ''
    error_message = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                message = parse_status(homework[0])
                if status_message != message:
                    status_message = message
                    send_message(bot, message)
            else:
                logging.debug('Новых статусов нет!')
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в программе: {error}'
            logging.error(message)
            if error_message != message:
                error_message = message
                bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
