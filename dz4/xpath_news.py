# Написать приложение, которое собирает основные новости с сайта на выбор news.mail.ru, lenta.ru, yandex-новости.
# Для парсинга использовать XPath. Структура данных должна содержать:
# - название источника;
# - наименование новости;
# - ссылку на новость;
# - дата публикации.
# Сложить собранные новости в БД
from datetime import datetime
from time import strptime, strftime

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sys import argv
from pymongo import MongoClient
from pprint import pprint
import bson.json_util as json_util
from pycbrf import ExchangeRates
from lxml import html

DB_NAME = 'fresh_news'
DB_ADDRESS = '127.0.0.1'
DB_PORT = 27017
COLLECTION_NAME = 'news'


class NewsPiece:
    def __init__(self, site, title, link, source, news_time):
        self._site = site
        self._title = title
        self._link = link
        self._time = news_time
        self._source = source

    def __str__(self):
        return f"\n---\n" \
               f"Заголовок:{self._title}\n" \
               f"Ресурс: {self._site}\n" \
               f"Источник: {self._source}\n" \
               f"Время: {self._time}\n" \
               f"Ссылка: {self._link}"

    def get_dict(self):
        return {
            'Site': self._site,
            'Title': self._title,
            'Link': self._link,
            'Time': self._time,
            'Source': self._source
        }


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

    def insert_or_update(self, new_document):
        # сохраняет или перезаписывает документ new_document в базу
        # key_value - значение ключа поиска
        self._collection.update_one(
            {self._key: new_document[self._key]},
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


class News:
    def __init__(self, db):
        self._db = db
        self._session = requests.session()
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/103.0.0.0 Safari/537.36'
        }
        self._news = []

    def get_lenta_news(self):
        url = 'https://lenta.ru'
        response = self._session.get(url, headers=self._headers)
        dom = html.fromstring(response.text)
        top_news = dom.xpath("//a[contains(@class,'_topnews')]")
        site = 'lenta.ru'

        for top_news_element in top_news:
            title = top_news_element.xpath(".//h3[contains(@class, 'card-big__title')] |"
                                           " .//span[contains(@class, 'card-mini__title')]")[0].text
            source = "Lenta.ru"
            link = url + top_news_element.xpath("./@href")[0]
            news_time = top_news_element.xpath(".//time")[0].text
            self._news.append(NewsPiece(site, title, link, source, news_time))

    def get_yandex_news(self):
        url = 'https://yandex.ru/news'
        response = self._session.get(url, headers=self._headers)
        dom = html.fromstring(response.text)
        top_news = dom.xpath("//div[contains(@class,'news-top-flexible-stories')]/div")
        site = 'Yandex.ru'

        for top_news_element in top_news:
            title = top_news_element.xpath(".//h2[@class='mg-card__title']/a")[0].text
            link = url + top_news_element.xpath(".//h2[@class='mg-card__title']/a/@href")[0]
            source = top_news_element.xpath(".//span[@class='mg-card-source__source']//a")[0].text
            news_time = top_news_element.xpath(".//span[@class='mg-card-source__time']")[0].text
            self._news.append(NewsPiece(site, title, link, source, news_time))

    def get_mailru_news(self):
        url = 'https://news.mail.ru'
        response = self._session.get(url, headers=self._headers)
        dom = html.fromstring(response.text)
        top_news = dom.xpath(
            "//div[contains(@data-logger,'news__MainTopNews')]//a[contains(@class,'js-topnews__item')]/@href|"
            "//div[contains(@data-logger,'news__MainTopNews')]//a[contains(@class,'list__text')]/@href")
        site = 'Mail.ru'
        for link in top_news:
            response = self._session.get(link, headers=self._headers)
            dom = html.fromstring(response.text)
            article = dom.xpath("//div[contains(@class, 'article')]")
            if article:
                article = article[0]
            else:
                continue

            title = article.xpath(".//h1")[0].text
            news_time = article.xpath(".//span[contains(@class, 'js-ago')]/@datetime")[0]
            news_time = strptime(str(news_time), "%Y-%m-%dT%H:%M:%S+03:00")
            news_time = strftime("%H:%M", news_time)
            source = article.xpath(".//span[contains(@class, 'link__text')]")[0].text
            self._news.append(NewsPiece(site, title, link, source, news_time))

    def get_news(self):
        print('Parsing lenta.ru...')
        self.get_lenta_news()
        print('Parsing yandex.ru...')
        self.get_yandex_news()
        print('Parsing mail.ru...')
        self.get_mailru_news()

    def show_news(self):
        for news_piece in self._news:
            print(news_piece)

    def save_to_db(self):
        for news_piece in self._news:
            self._db.insert_or_update(news_piece.get_dict())


db = MongoHH(DB_ADDRESS, DB_PORT, DB_NAME, COLLECTION_NAME)
news = News(db)
news.get_news()
print("\n========\n"
      "= NEWS =\n"
      "========\n")
news.show_news()
print("\n============\n"
      "= DATABASE =\n"
      "==============\n")
news.save_to_db()
db.show_collection()

fn = "news.json"
db.export_to_json_file(fn)
print(f"File saved: {fn}")
