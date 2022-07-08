# Необходимо собрать информацию о вакансиях на вводимую должность (используем input или через аргументы получаем
# должность) с сайтов HH(обязательно) и/или Superjob(по желанию). Приложение должно анализировать несколько страниц
# сайта (также вводим через input или аргументы). Получившийся список должен содержать в себе минимум:
# Наименование вакансии.
# Предлагаемую зарплату (разносим в три поля: минимальная и максимальная и валюта. цифры преобразуем к цифрам).
# Ссылку на саму вакансию.
# Сайт, откуда собрана вакансия. (можно прописать статично hh.ru или superjob.ru)
# По желанию можно добавить ещё параметры вакансии (например, работодателя и расположение). Структура должна быть
# одинаковая для вакансий с обоих сайтов. Общий результат можно вывести с помощью dataFrame через pandas.
# Сохраните в json либо csv.

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sys import argv

job = "Python разработчик"  # строка поиска по умолчанию
max_pages = None  # максимальное количество страниц выдачи


class JobFinderSJ:
    # поиск вакансий на superjob.ru

    def __init__(self, search_string, pages=0):
        # конструктор принимает строку поиска и число страниц
        self._search_string = search_string
        self._max_pages = pages
        self._session = requests.session()
        self._url = 'https://russia.superjob.ru/vacancy/search/'
        self._vacancy_abs_url = 'https://russia.superjob.ru/vakansii'
        self._site_name = 'superjob.ru'
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

    def _sj_get_request(self, page):
        # загрузка страницы с номером page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/103.0.0.0 Safari/537.36'
        }

        params = {
            'keywords': self._search_string,
            'page': page
        }

        response = self._session.get(self._url, headers=headers, params=params)

        return response

    @staticmethod
    def _get_min_max_currency(salary_str):
        # разбирает строку с зарплатой. возвращает словарь с минимальной, максимальной зарплатой и валютой.
        res = {
            'min': None,
            'max': None,
            'cur': None
        }

        if salary_str and salary_str != "По договорённости":
            salary_str = salary_str.replace(u"\u202f", "").replace(u'\xa0', u' ')
            salary_str = salary_str.replace("/месяц", "")
            last_space_position = salary_str.rfind(' ')
            res['cur'] = salary_str[last_space_position + 1:]
            salary_str = salary_str[:last_space_position].replace(' ', '')
            if salary_str.find('—') > 0:
                string_split = salary_str[:last_space_position].split('—')
                res['min'], res['max'] = string_split
            elif salary_str.startswith('от'):
                res['min'] = salary_str[2:]
            elif salary_str.startswith('до'):
                res['max'] = salary_str[2:]
            res['min'] = int(res['min']) if res['min'] else None
            res['max'] = int(res['max']) if res['max'] else None

        return res

    def load_data(self, verbose=False):
        # загрузка данных с сайта superjob.ru в self._data
        # verbose - выводить номер загружаемой страницы
        page_number = 1

        is_next_page = True

        while is_next_page and (not self._max_pages or page_number <= self._max_pages):
            if verbose:
                print(f'Page loading: {page_number}')
            response = self._sj_get_request(page_number)

            dom = BeautifulSoup(response.text, 'html.parser')
            vacancies = dom.find_all('div', {'class': 'f-test-vacancy-item'})

            for vacancy in vacancies:
                name = vacancy.find('a', {'class': "_1IHWd"})
                href = (self._vacancy_abs_url + name.get('href')) if name else ""
                name = name.text if name else ""

                salary = vacancy.find('span', {'class': "_1Fg5m"})
                salary = salary.text if salary else None

                employer = vacancy.find('span', {'class': "_3nMqD"})
                employer = employer.text if employer else ""

                address = vacancy.find('span', {'class': "f-test-text-company-item-location"})
                address = address.text if address else ""

                salary_mmc = self._get_min_max_currency(salary)

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

            next_page = dom.find('a', {'class': 'f-test-button-dalshe'})
            if not next_page:
                is_next_page = False

            page_number += 1
        self._df = pd.DataFrame(self._data)


if __name__ == '__main__':
    if len(argv) == 3:
        max_pages = int(argv[2])
    if len(argv) >= 2:
        job = argv[1]
    if len(argv) == 1:
        print("Usage:\n"
              "sjsearch.py SEARCH_STRING MAX_PAGES\n"
              "  SEARCH_STRING: vacancy name\n"
              "  MAX_PAGES: pages limit (default 0: no limit)\n"
              "Processing default values...")

    sj = JobFinderSJ(job, max_pages)

    print(f'Searching for vacancies "{job}" at superjob.ru (max pages: {max_pages}).')

    sj.load_data(verbose=True)

    print("\n=================\n"
          "= SEARCH RESULT =\n"
          "=================\n")

    sj.print_data()
    fn = sj.save_csv()

    print(f"File saved: {fn}")
