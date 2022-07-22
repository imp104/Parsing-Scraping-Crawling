# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobparserItem(scrapy.Item):
    # объект вакансии

    vacancy = scrapy.Field()
    salary = scrapy.Field()
    link = scrapy.Field()
    site = scrapy.Field()
    employer = scrapy.Field()
    place = scrapy.Field()
    _id = scrapy.Field()


