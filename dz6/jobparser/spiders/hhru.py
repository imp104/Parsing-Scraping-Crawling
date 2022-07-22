from pprint import pprint

import scrapy
from scrapy.http import HtmlResponse
from jobparser.items import JobparserItem


class HhruSpider(scrapy.Spider):
    # класс паука для hh.ru

    def __init__(self, **kwargs):
        self.name = 'hhru'  # имя паука
        self.site = 'hh.ru'
        self.allowed_domains = ['hh.ru']  # список доменов
        self.search_line = kwargs.get('search_line')

        # список стартовых ссылок
        self.start_urls = [
            f'https://hh.ru/search/vacancy?text={self.search_line}&from=suggest_post&salary=&clusters=true&area=1&ored_clusters=true&enable_snippets=true',
            f'https://hh.ru/search/vacancy?text={self.search_line}&from=suggest_post&salary=&clusters=true&area=2&ored_clusters=true&enable_snippets=true']

        self.search_line = kwargs.get('search_line')
        super().__init__()

    def parse(self, response: HtmlResponse):
        # метод осуществляет парсинг страницы (response).
        # ищет ссылки и осуществляет переход на следующую страницу.
        next_page = response.xpath("//a[@data-qa='pager-next']/@href").get()  # ищем ссылку на следующую страницу
        if next_page:  # если страница найдена
            yield response.follow(next_page, callback=self.parse)  # возвращаем объект response
        links = response.xpath("//a[@data-qa='vacancy-serp__vacancy-title']/@href").getall()
        pprint(links)
        for link in links:
            yield response.follow(link, callback=self.vacancy_parse)

    def vacancy_parse(self, response: HtmlResponse):
        # парсер вакансий, полученных по ссылкам из parse.
        name = response.xpath("//h1/text()").get()  # заголовок вакансии
        salary = response.xpath("//div[@data-qa='vacancy-salary']//text()").getall()  # зарплата
        salary = ''.join(salary)
        url = response.url  # ссылку берём из объекта response
        employer = ''.join(response.xpath("//span[@class='vacancy-company-name']//text()").getall())
        place = ''.join(response.xpath("(//span[@data-qa='vacancy-view-raw-address'])[1]//text()").getall())
        if not place:
            place = ''.join(response.xpath("//p[@data-qa='vacancy-view-location']//text()").getall())
        item = JobparserItem(vacancy=name, salary=salary, link=url, site=self.site, employer=employer,
                             place=place)  # создаём item
        yield item  # возвращаем полученный объект
