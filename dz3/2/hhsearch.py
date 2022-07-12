# 2. Написать функцию, которая производит поиск и выводит на экран вакансии с заработной платой больше введённой
# суммы (необходимо анализировать оба поля зарплаты). То есть цифра вводится одна, а запрос проверяет оба поля

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sys import argv
from pymongo import MongoClient
from pprint import pprint
import bson.json_util as json_util
from pycbrf import ExchangeRates

MIN_SALARY = 200000

DB_NAME = 'hh_vacancies'
DB_ADDRESS = '127.0.0.1'
DB_PORT = 27017

job = "Data scientist senior"  # строка поиска по умолчанию
max_pages = 20  # максимальное количество страниц выдачи


class MongoHH:
    # реализация взаимодействия с MongoDB
    def __init__(self, address, port, db_name, collection):
        # address, port - ip и порт сервера
        # db_name - база данных
        # collection - имя коллекции
        self._client = MongoClient(address, port)
        self._db = self._client[db_name]
        self._collection = self._db[collection]
        self._key = 'Link'  # поле с уникальным ключом

    def insert_or_update(self, key_value, new_document):
        # сохраняет или перезаписывает документ new_document в базу
        # key_value - значение ключа поиска
        self._collection.update_one(
            {self._key: key_value},
            {'$set': new_document},
            upsert=True
        )

    def show_collection(self):
        # вывод коллекции
        for item in self._collection.find({}):
            pprint(item)

    def export_to_json_file(self, filename):
        # сохранение коллекии в JSON-формате
        # filename - имя файла
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_util.dumps(self._collection.find({}), indent=4, ensure_ascii=False))

    @property
    def collection(self):
        # getter для объекта коллекции
        return self._collection


class JobFinderHH:
    # поиск вакансий на hh.ru и запись в MongoDB

    def __init__(self, db, search_string, pages=0):
        # конструктор принимает объект базы данных, строку поиска и число страниц
        self._db = db
        self._search_string = search_string
        self._max_pages = pages
        self._session = requests.session()
        self._url = 'https://hh.ru/search/vacancy'
        self._site_name = 'hh.ru'
        self._data = {
            'Vacancy': [],
            'Salary min': [],
            'Salary max': [],
            'Currency': [],
            'Link': [],
            'Site': [],
            'Employer': [],
            'Place': []
        }
        self._df = None
        self._exchange_rates = ExchangeRates()  # актуальные курсы валют от ЦБРФ

    def print_data(self):
        # вывод результатов
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        self._df = self._df.fillna('')
        print(self._df)

    def save_csv(self):
        # сохранение файла csv
        filename = f'{self._site_name} {self._search_string}.csv'
        self._df.to_csv(filename, encoding='cp1251')
        # self._df.to_csv(filename)
        return filename

    def save_json(self):
        # сохранение файла json
        filename = f'{self._site_name} {self._search_string}.json'
        self._db.export_to_json_file(filename)
        return filename

    def _hh_get_request(self, page):
        # загрузка страницы с номером page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/103.0.0.0 Safari/537.36'
        }

        params = {
            'from': 'suggest_post',
            'fromSearchLine': 'true',
            'area': "113",
            'page': page,
            'hhtmFrom': 'vacancy_search_list',
            'customDomain': 1,
            'items_on_page': 20,
            'text': self._search_string,
        }

        response = self._session.get(self._url, headers=headers, params=params)

        if response.history:
            raise Exception(f'[ERROR] request redirected: {response.url}')

        return response

    def _get_min_max_currency(self, salary_str):
        # разбирает строку с зарплатой. возвращает словарь с минимальной, максимальной зарплатой и валютой.
        # также получает актуальные курсы валют и возвращает рублёвый эквивалент
        res = {
            'min': None,
            'max': None,
            'cur': None,
            'rub_min': None,
            'rub_max': None
        }

        if salary_str:
            salary_str = salary_str.replace(u"\u202f", "")
            last_space_position = salary_str.rfind(' ')
            res['cur'] = salary_str[last_space_position + 1:]
            salary_str = salary_str[:last_space_position].replace(' ', '')
            if salary_str.find('–') > 0:
                string_split = salary_str[:last_space_position].split('–')
                res['min'], res['max'] = string_split
            elif salary_str.startswith('от'):
                res['min'] = salary_str[2:]
            elif salary_str.startswith('до'):
                res['max'] = salary_str[2:]
            res['min'] = float(res['min']) if res['min'] else None
            res['max'] = float(res['max']) if res['max'] else None
            if res['cur'] and res['cur'] != 'руб.':
                res['rub_min'] = res['min'] * float(self._exchange_rates[res['cur']].value) if res['min'] else None
                res['rub_max'] = res['max'] * float(self._exchange_rates[res['cur']].value) if res['max'] else None
            else:
                res['rub_min'] = res['min']
                res['rub_max'] = res['max']

        return res

    def load_data(self, verbose=False):
        # загрузка данных с сайта hh.ru в self._data
        # verbose - выводить номер загружаемой страницы
        page_number = 0

        is_next_page = True

        while is_next_page and (not self._max_pages or page_number < self._max_pages):
            if verbose:
                print(f'Page loading: {page_number}')
            response = self._hh_get_request(page_number)

            dom = BeautifulSoup(response.text, 'html.parser')
            vacancies = dom.find_all('div', {'class': 'vacancy-serp-item'})

            for vacancy in vacancies:
                name = vacancy.find('a', {'data-qa': "vacancy-serp__vacancy-title"})
                href = name.get('href')
                name = name.text if name else ""
                salary = vacancy.find('span', {'data-qa': "vacancy-serp__vacancy-compensation"})
                salary = salary.text if salary else None
                schedule = vacancy.find('div', {'data-qa': "vacancy-serp__vacancy-work-schedule"})
                schedule = schedule.text if schedule else None
                employer = vacancy.find('a', {'data-qa': "vacancy-serp__vacancy-employer"})
                employer = employer.text.replace("\xa0", " ") if employer else ""
                address = vacancy.find('div', {'data-qa': "vacancy-serp__vacancy-address"})
                address = address.text.replace("\xa0", " ") if address else None
                description = vacancy.find('div', {'data-qa': "vacancy-serp__vacancy_snippet_responsibility"})
                description = description.text if description else None
                requirements = vacancy.find('div', {'data-qa': "vacancy-serp__vacancy_snippet_requirement"})
                requirements = requirements.text if requirements else None
                salary_mmc = self._get_min_max_currency(salary)

                # подготовка pandas dataframe

                # encode-decode для экспорта csv (у to_csv нет опции ignore)
                self._data['Vacancy'].append(name.encode('cp1251', 'ignore').decode('cp1251'))
                # self._data['Vacancy'].append(name)
                self._data['Salary min'].append(salary_mmc['min'])
                self._data['Salary max'].append(salary_mmc['max'])
                self._data['Currency'].append(salary_mmc['cur'])
                self._data['Link'].append(href)
                self._data['Site'].append(self._site_name)
                self._data['Employer'].append(employer.encode('cp1251', 'ignore').decode('cp1251'))
                # self._data['Employer'].append(employer)
                self._data['Place'].append(address.encode('cp1251', 'ignore').decode('cp1251'))
                # self._data['Place'].append(address)

                # запись в базу данных
                mongo_doc = {
                    'Vacancy': name,
                    'Salary_min': salary_mmc['min'],
                    'Salary_max': salary_mmc['max'],
                    'Salary_min_rub': salary_mmc['rub_min'],
                    'Salary_max_rub': salary_mmc['rub_max'],
                    'Currency': salary_mmc['cur'],
                    'Link': href,
                    'Employer': employer,
                    'Place': address
                }
                self._db.insert_or_update(href, mongo_doc)

            next_page = dom.find('a', {'data-qa': 'pager-next'})
            if not next_page:
                is_next_page = False

            page_number += 1
        self._df = pd.DataFrame(self._data)

    def show_filtered_by_salary(self, salary):
        # показывает вакансии, отфильтрованные по зарплате (salary) в рублях
        for item in self._db.collection.find(
                {'$or': [{
                    'Salary_min_rub': {'$gt': salary}
                }, {
                    'Salary_max_rub': {'$gt': salary}
                }]}):
            pprint(item)


if __name__ == '__main__':
    if len(argv) == 3:
        max_pages = int(argv[2])
    if len(argv) >= 2:
        job = argv[1]
    if len(argv) == 1:
        print("Usage:\n"
              "hhsearch.py SEARCH_STRING MAX_PAGES\n"
              "  SEARCH_STRING: vacancy name\n"
              "  MAX_PAGES: pages limit (default 0: no limit)\n"
              "Processing default values...")

    mongo_hh = MongoHH(DB_ADDRESS, DB_PORT, DB_NAME, job)

    hh = JobFinderHH(mongo_hh, job, max_pages)

    print(f'Searching for vacancies "{job}" at hh.ru (max pages: {max_pages}).')

    hh.load_data(verbose=True)

    print("\n=================\n"
          "= SEARCH RESULT =\n"
          "=================\n")

    hh.print_data()

    # print("\n============\n"
    #       "= DATABASE =\n"
    #       "============\n")
    #
    # mongo_hh.show_collection()

    print("\n============\n"
          "= FILTERED =\n"
          "============\n")

    hh.show_filtered_by_salary(MIN_SALARY)

    fn = hh.save_csv()
    print(f"\nFile saved: {fn}")

    fn = hh.save_json()
    print(f"File saved: {fn}")
