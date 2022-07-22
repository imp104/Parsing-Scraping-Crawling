# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
# from pymongo import MongoClient
from modules.db_routines import Mongo


class JobparserPipeline:
    def __init__(self):
        self.mongo_base = Mongo()  # создаём объект базы

    def process_item(self, item, spider):
        item['salary'] = self.get_min_max_currency(item['salary'], spider.name)  # обработка поля с зарплатой
        self.mongo_base.insert_or_update(spider.name, item)  # записываем объект в базу
        return item

    @staticmethod
    def get_min_max_currency(salary_str, spider_name):
        # разбирает строку с зарплатой. возвращает словарь с минимальной, максимальной зарплатой и валютой.
        # обрабатывает данные с учётом специфики сайта.
        # salary_str - строка с зарплатой
        # spider_name - имя паука
        res = {
            'min': None,
            'max': None,
            'cur': None
        }
        if salary_str:
            if spider_name == 'hhru':
                salary_str = salary_str.replace(u"\u202f", "").\
                    replace(u" на руки", "").\
                    replace(u'\xa0', "").\
                    replace('не указана', '').\
                    replace(' до вычета налогов', '')
                last_space_position = salary_str.rfind(' ')
                res['cur'] = salary_str[last_space_position + 1:]
                salary_str = salary_str[:last_space_position].replace(' ', '')
                if salary_str.find('–') > 0:
                    string_split = salary_str[:last_space_position].split('–')
                    res['min'], res['max'] = string_split
                elif salary_str.startswith('от'):
                    if salary_str.find('до') > 0:
                        res['min'] = salary_str[2:salary_str.find('до')]
                        res['max'] = salary_str[salary_str.find('до') + 2:]
                    else:
                        res['min'] = salary_str[2:]
                elif salary_str.startswith('до'):
                    res['max'] = salary_str[2:]
                res['min'] = int(res['min']) if res['min'] else None
                res['max'] = int(res['max']) if res['max'] else None
            elif spider_name == 'superjob':
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
