from pprint import pprint
from re import findall
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from time import sleep
import bson.json_util as json_util
from pymongo import MongoClient

URL = 'https://mvideo.ru'

DB_NAME = 'mvideo_products'
DB_ADDRESS = '127.0.0.1'
DB_PORT = 27017
COLLECTION_NAME = 'trending'
DEFAULT_JSON_FILE_NAME = "mvideo_trending.json"


class Mongo:
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

    def export_to_json_file(self, filename=DEFAULT_JSON_FILE_NAME):
        # сохранение коллекии в JSON-формате
        # filename - имя файла
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_util.dumps(self._collection.find({}), indent=4, ensure_ascii=False))


class MVideo:
    # работа с сайтом mvideo.ru через selenium
    def __init__(self):
        self._products = []
        options = Options()
        options.add_argument('start-maximized')
        options.add_argument("--disable-notifications")
        chromedriver_service = Service('./chromedriver.exe')
        self._driver = webdriver.Chrome(service=chromedriver_service, options=options)

    def _get_product_elements(self, verbose=False):
        # Возвращает список товаров (списки с элементами selenium).

        # Листает сайт клавишей Page Down, пока не появится кнопка "В тренде".
        # Жмёт кнопку, ищет все элементы в разделе "В тренде".
        # Разбивает полученный список на списки длиной 9 элементов.

        self._driver.get(URL)
        self._driver.implicitly_wait(10)

        body = self._driver.find_element(By.CSS_SELECTOR, 'body')

        button = None
        while not button:  # листаем, пока не обнаружен элемент с кнопкой
            if verbose:
                print('Scanning page for button...')
            try:
                button = self._driver.find_element(By.XPATH, '//span[contains(text(),"В тренде")]')
            except Exception as ex:
                try:
                    body.send_keys(Keys.PAGE_DOWN)
                    sleep(2)
                except Exception as ex:
                    body = self._driver.find_element(By.CSS_SELECTOR, 'body')
                    body.send_keys(Keys.PAGE_DOWN)
                    sleep(5)

        if verbose:
            print('Button detected.')
        sleep(2)

        button.click()
        sleep(2)

        if verbose:
            print('Button pressed.')

        divs = self._driver.find_elements(By.XPATH, '//*[@_nghost-serverapp-c276]//'
                                                    'div[contains(@class,"mvid-carousel-outer mv-hide-scrollbar")]/'
                                                    'div[contains(@class,"mvid-carousel-inner")]/'
                                                    'mvid-product-cards-group/'
                                                    'div[@_ngcontent-serverapp-c260]')

        chunk_size = 9

        if verbose:
            print('Products in trending list:', int(len(divs) / chunk_size))

        elements = [divs[i * chunk_size:(i + 1) * chunk_size] for i in range(0, int(len(divs) / chunk_size))]

        return elements

    def scan_products(self, verbose=False):

        item_list = self._get_product_elements(verbose=verbose)

        for item in item_list:
            additional_terms = item[0].text
            discount_percent = item[1].text
            product_name = item[3].text
            rev_block = item[4].text.splitlines()
            rating = rev_block[0] if len(rev_block) > 0 else ""
            rev_cnt = rev_block[1] if len(rev_block) > 1 else ""

            price_block = item[5].text.splitlines()
            cur_price = price_block[0] if len(price_block) > 0 else ""
            cur_price = "".join(findall("\d", cur_price))
            cur_price = int(cur_price) if cur_price else -1
            old_price = price_block[1] if len(price_block) > 1 else ""
            old_price = "".join(findall("\d", old_price))
            old_price = int(old_price) if old_price else -1
            bonus = item[7].text

            href = item[3].find_element(By.XPATH, './/a').get_attribute('href')

            item_dict = {
                "Additional terms": additional_terms,
                "Discount percent": discount_percent,
                "Product name": product_name,
                "Rating": rating,
                "Reviews count": rev_cnt,
                "Current price": cur_price,
                "Old price": old_price,
                "Bonus": bonus,
                "Link": href
            }

            self._products.append(item_dict)
            print(f'Product added: {product_name}')

    def save_to_db(self, db):
        # запись в базу данных
        for product in self._products:
            db.insert_or_update(product)

    def __del__(self):
        # деструктор - завершает работу драйвера
        self._driver.close()


if __name__ == '__main__':
    db = Mongo(DB_ADDRESS, DB_PORT, DB_NAME, COLLECTION_NAME)

    mv = MVideo()
    mv.scan_products(verbose=True)
    mv.save_to_db(db)

    print("\n============\n"
          "= PRODUCTS =\n"
          "============\n")
    db.show_collection()
    db.export_to_json_file()
