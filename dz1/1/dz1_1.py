# 1. Посмотреть документацию к API GitHub, разобраться как вывести список 
# репозиториев для конкретного пользователя, сохранить JSON-вывод в файле *.json.

from json import dump
from requests import get
from sys import exit
from tabulate import tabulate

USERNAME = "imp104"


class GHRepos:
    # список репозиториев пользователя

    def __init__(self, uname):
        """
        Конструктор класса. Плдучает список репозиториев через GitHub API
        :param uname: имя пользователя
        """
        self._username = uname  # пользователь GitHub
        self._repos = self.get_repos()  # результат GET-запроса
        self._error = not self._repos.ok  # флаг ошибки
        self._json = self._repos.json()  # словарь json со списком репозиториев

    def get_repos(self):
        # GET-запрос к GitHub API
        get_result = get(f"https://api.github.com/users/{self._username}/repos")
        return get_result

    def write_json(self):
        # сохранение json в файл
        json_filename = f"{self._username}_repos.json"
        with open(json_filename, "w") as f:
            dump(self._json, f, indent=4, sort_keys=True)

    @property
    def error(self):
        # флаг ошибки
        return self._error

    def show_repos(self):
        # вывод таблицы
        headers = ['name', 'description', 'html_url']
        values = [[repo.get(field) for field in headers] for repo in self._json]
        tab = tabulate(values, headers=headers, tablefmt='github')
        width = len(tab.splitlines()[0])
        table_name = f'Github repositories for {self._username}'.center(width)
        print(f'\n{table_name}\n\n{tab}')


ghr = GHRepos(USERNAME)

if ghr.error:
    print("Error!")
    exit(-1)

ghr.write_json()
ghr.show_repos()
