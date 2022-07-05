# 2. Изучить список открытых API (https://www.programmableweb.com/category/all/apis). 
# Найти среди них любое, требующее авторизацию (любого типа). Выполнить запросы к нему, 
# пройдя авторизацию. Ответ сервера записать в файл.

import requests
from json import dump, dumps

API_KEY = "________________________________"  # https://www.last.fm/api/account/create
USER_AGENT = "_______"


def json_print(obj):
    # вывод Json-объекта
    print(dumps(obj, sort_keys=True, indent=4))


def json_save(obj, json_filename):
    # сохранение json в файл
    with open(json_filename, "w") as f:
        dump(obj, f, indent=4, sort_keys=True)


class LastFMAPI:
    # класс для работы с LastFM API
    def __init__(self, api_key=API_KEY, user_agent=USER_AGENT, url='https://ws.audioscrobbler.com/2.0/'):
        # конструктор, принимает ключ API, user agent и ссылку для GET-запросов
        self._api_key = api_key
        self._user_agent = user_agent
        self._request_url = url

    def get(self, lastfm_api_request):
        # выполняет запрос к LastFM API
        request_headers = {'user-agent': self._user_agent}
        lastfm_api_request['api_key'] = self._api_key
        lastfm_api_request['format'] = 'json'
        response = requests.get(self._request_url, headers=request_headers, params=lastfm_api_request)
        return response


class LastFMArtistInfo:
    # информация об исполнителе
    def __init__(self, artist, api):
        # принимает имя исполнителя и объект LastFMAPI
        self._artist = artist
        self._api = api

    def get_tags(self):
        # возвращает три тэга исполнителя в виде строки
        response = self._api.get({
            'method': 'artist.getTopTags',
            'artist': self._artist
        })

        if response.status_code != 200:
            return None

        # формируем строку из первых трёх тэгов исполнителя
        tags = [t['name'] for t in response.json()['toptags']['tag'][:3]]
        tags_str = ', '.join(tags)

        return tags_str

    def get_album_info(self, album):
        # возвращает json с информацией об альбоме album
        response = self._api.get({
            'method': 'album.getInfo',
            'artist': self._artist,
            'album': album
        })

        if response.status_code != 200:
            return None

        res = response.json()

        return res


if __name__ == '__main__':
    artist_name = 'Panzerballett'
    album_name = 'Tank Goodness'

    lfm_api = LastFMAPI()  # создаём объект API (с параметрами по умолчанию)
    lfm_artist = LastFMArtistInfo(artist_name, lfm_api)  # объект информации об исполнителе
    album_info = lfm_artist.get_album_info(album_name)  # получаем json с описанием альбома
    artist_tags = lfm_artist.get_tags()  # получаем список тэгов

    print(f"Tags for {artist_name}: {artist_tags}")
    print("Album info json:")
    json_print(album_info)
    json_save(album_info, f'{album_name}_album_info.json')  # сохраняем json в файл
