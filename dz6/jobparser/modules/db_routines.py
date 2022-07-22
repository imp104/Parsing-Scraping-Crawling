from pymongo import MongoClient
from pprint import pprint
import bson.json_util as json_util

DB_NAME = 'vacancies'
DB_ADDRESS = '127.0.0.1'
DB_PORT = 27017


class Mongo:
    # реализация взаимодействия с MongoDB
    def __init__(self, address=DB_ADDRESS, port=DB_PORT, db_name=DB_NAME):
        # address, port - ip и порт сервера
        # db_name - база данных
        # collection - имя коллекции
        self._client = MongoClient(address, port)
        self._db = self._client[db_name]
        self._key = 'link'  # поле с уникальным ключом

    def insert_or_update(self, collection, new_document):
        # сохраняет или перезаписывает документ new_document в базу
        # key_value - значение ключа поиска
        self._db[collection].update_one(
            {self._key: new_document[self._key]},
            {'$set': new_document},
            upsert=True
        )

    def show_collection(self, collection):
        # вывод коллекции
        for item in self._db[collection].find({}):
            pprint(item)

    def export_to_json_file(self, collection, filename):
        # сохранение коллекии в JSON-формате
        # filename - имя файла
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_util.dumps(self._db[collection].find({}), indent=4, ensure_ascii=False))
