import json
import os
from time import sleep

import requests
from bs4 import BeautifulSoup

QWINTRY_HOST = 'logistics.qwintry.com'
FILENAME = 'info.json'

SLEEP_TIME = os.getenv('SLEEP_TIME', 60)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TRACKING_NUMBERS = os.getenv('TRACKING_NUMBERS')


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def send_message(message, chat_id):
    url = 'https://api.telegram.org/bot{}/sendMessage'.format(TELEGRAM_TOKEN)
    response = requests.post(url, data={
        'chat_id': chat_id,
        'text': message,
    })
    return response


def format_message(tracking_number, info):
    message = f'Изменения по треку {tracking_number}:\n'
    for item in info:
        message += '[{}] {} ({})\n'.format(item['date'], item['full_descr'], item['short_descr'])
    return message


def format_url(tracking_number):
    return f'https://{QWINTRY_HOST}/ru/track?tracking={tracking_number}'


def get_info(tracking_number):
    url = format_url(tracking_number)
    response = requests.get(url)
    content = response.content
    soup = BeautifulSoup(content, 'html.parser')
    cleaned_contents = []
    for chunk in chunks(soup.tbody.find_all('td'), 3):
        cleaned_contents.append({
            'date': chunk[0].text.strip(),
            'short_descr': chunk[1].text.strip(),
            'full_descr': chunk[2].text.strip(),
        })
        sleep(0.5)
    return cleaned_contents


def save_to_file(full_info, filename):
    with open(filename, 'w') as file:
        file.write(json.dumps(full_info, indent=4))


def load_from_file(filename):
    with open(filename, 'r') as file:
        return json.loads(file.read())


if __name__ == '__main__':
    while True:
        full_info = {}
        tracking_numbers = [n.strip() for n in TRACKING_NUMBERS.split(',')]
        for tracking_number in tracking_numbers:
            info = get_info(tracking_number)
            full_info[tracking_number] = info

        try:
            full_info_file = load_from_file(FILENAME)
        except FileNotFoundError:
            save_to_file(full_info, FILENAME)
            print('File created!')
            continue

        if full_info_file != full_info:
            save_to_file(full_info, FILENAME)
            print('File updated!')
            for tracking_number, info in full_info.items():
                if full_info_file.get(tracking_number) != info:
                    message = format_message(tracking_number, info)
                    send_message(message, TELEGRAM_CHAT_ID)
                    print('Message sent!')
        else:
            print('No changes!')

        print('Sleeping...')
        sleep(SLEEP_TIME)
