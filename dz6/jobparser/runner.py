from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

from jobparser.spiders.hhru import HhruSpider
from jobparser.spiders.superjob import SuperjobSpider

SEARCH_LINE = 'golang'

if __name__ == '__main__':
    configure_logging()  # инициализация лога
    settings = get_project_settings()  # загрузка настроек из settings.py
    runner = CrawlerRunner(settings)  # объект раннера
    runner.crawl(HhruSpider, search_line=SEARCH_LINE)  # подключаем паука для hh.ru
    runner.crawl(SuperjobSpider, search_line=SEARCH_LINE)  # подключаем паука для superjob.ru
    d = runner.join()  # организация выполнения нескольких пауков
    d.addBoth(lambda _: reactor.stop())  # callback и errback функция
    reactor.run()  # запуск пауков и ожидание завершения их процессов

