from pprint import pprint

import scrapy
from scrapy.http import HtmlResponse
from jobparser.items import JobparserItem


class SuperjobSpider(scrapy.Spider):
    # класс паука для superjob.ru

    def __init__(self, **kwargs):
        self.name = 'superjob'  # имя паука
        self.site = 'superjob.ru'
        self.allowed_domains = ['superjob.ru']  # список доменов
        self.search_line = kwargs.get('search_line')

        # список стартовых ссылок
        self.start_urls = [
            f'https://www.superjob.ru/vacancy/search/?keywords={self.search_line}&geo%5Bt%5D%5B0%5D=4',
            f'https://spb.superjob.ru/vacancy/search/?keywords={self.search_line}']

        super().__init__()

    def parse(self, response: HtmlResponse):
        # метод осуществляет парсинг страницы (response).
        # ищет ссылки и осуществляет переход на следующую страницу.
        next_page = response.xpath(
            "//a[contains(@class, 'f-test-button-dalshe')]").get()  # ищем ссылку на следующую страницу
        if next_page:  # если страница найдена
            yield response.follow(next_page, callback=self.parse)  # возвращаем объект response
        links = response.xpath(
            "//div[contains(@class, 'f-test-vacancy-item')]//a[contains(@class, 'HyxLN')]/@href").getall()
        pprint(links)
        for link in links:
            yield response.follow(link, callback=self.vacancy_parse)

    def vacancy_parse(self, response: HtmlResponse):
        # парсер вакансий, полученных по ссылкам из parse.
        name = response.xpath("//h1/text()").get()  # заголовок вакансии
        salary = response.xpath(
            "//div[contains(@class, 'f-test-vacancy-base-info')]//span[contains(@class, '_2eYAG')]//text()").getall()  # зарплата
        salary = ''.join(salary)
        url = response.url  # ссылку берём из объекта response
        employer = response.xpath(
            "//div[contains(@class, 'f-test-vacancy-base-info')]"
            "//a[contains(@class, '_1IHWd')]"
            "//span[contains(@class, '_10_Fa')]//text()").get()  # работодатель
        place = ''.join(response.xpath("//span[@class='_3NZry']//text()").getall())
        item = JobparserItem(vacancy=name, salary=salary, link=url, site=self.site, employer=employer, place=place)  # создаём item
        yield item  # возвращаем полученный объект
