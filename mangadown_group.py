import os
import random
import time
import re
from http.client import IncompleteRead
from tqdm import tqdm
import httplib2
import requests
from bs4 import BeautifulSoup
from utils import authorization, convert_output_file, check_status, sanitize_filename
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from exceptions import ChapterFetchError, DownloadError, MangaNotFoundError

class MangaDownGroup:
    def __init__(self, url, dom, sel, auto_start=True):
        self.url = url
        self.domain = dom
        self.sel = sel
        self.headers = {
            "accept": "*/*",
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "host": dom,
            "referer": f"{url}&mtr=true",
            "sec-ch-ua": "\"Google Chrome\";v=\"146\", \"Not:A-Brand\";v=\"24\", \"Chromium\";v=\"146\"",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            )
        }

        self.headers_img = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Google Chrome\";v=\"146\", \"Not:A-Brand\";v=\"24\", \"Chromium\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            )
        }

        self.links = []
        self.manga_name = None
        self.cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()

        if auto_start:
            self.start()

    def start(self):
        self.create_path()
        self.driver = self.init_driver()
        self.download()
        convert_output_file(self.cwd, self.manga_name, self.sel)

    def get_manga_data(self):
        """Получает данные о манге (название)."""
        try:
            response = requests.get(self.url, headers=self.headers)
            check_status(response.status_code)
            page = BeautifulSoup(response.content, 'html.parser')
            self.manga_name = page.find_all('div', class_="py-1")[0].text

        except Exception as e:
            raise MangaNotFoundError(f"Ошибка при получении данных манги: {e}") from e

    def init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        driver.command_executor.set_timeout(300)

        return driver

    def get_chapter_links(self):
        """Получает ссылки на главы."""
        try:
            response = requests.get(self.url, headers=self.headers)
            check_status(response.status_code)
            page = BeautifulSoup(response.content, 'html.parser')

            self.links = [
                link['href']
                for div in page.find_all('div', class_="chapters")
                for link in div.find_all('a', class_="chapter-link")
            ]
            self.links.reverse()

        except Exception as e:
            raise ChapterFetchError(f"Ошибка при получении списка глав: {e}") from e

    def create_path(self):
        """Создает директории для сохранения манги."""
        self.manga_name = sanitize_filename(self.manga_name)
        base_path = os.path.join(self.cwd, self.manga_name)
        os.makedirs(base_path, exist_ok=True)

        for link in self.links:
            vol, ch = link.split('/')[2:4]
            os.makedirs(os.path.join(base_path, vol, ch), exist_ok=True)

    def selen(self, url):
        self.driver.get(f"{url}?mtr=true")
        return self.driver.page_source

    def download(self):
        """Скачивает главы манги."""
        http = httplib2.Http('.cache')

        session = requests.Session()
        authorization(session=session, my_cwd=self.cwd)

        for _, link in enumerate(self.links):
            vol, ch = link.split('/')[2:4]
            chapter_path = os.path.join(self.cwd, self.manga_name, vol, ch)
            full_url = self.url.rsplit('/', 1)[0] + link

            max_attempts = 4
            script_tag = None

            for attempt in range(1, max_attempts + 1):
                try:
                    soup = BeautifulSoup(self.selen(full_url), 'html.parser')

                    # with open("page.txt", "w", encoding="utf-8") as f:
                    #     f.write(str(soup))
                    # exit(0)

                    script_tag = soup.find(
                        "script",
                        string=lambda x: x and "rm_h.readerInit" in x
                    )

                    if script_tag:
                        break

                    print(f"Не удалось получить страницы главы "
                          f"(попытка {attempt}/{max_attempts})")

                    time.sleep(2.5)

                except Exception as e:
                    raise DownloadError (f"Ошибка при получении главы: {e}") from e

            # если после всех попыток script_tag так и не найден
            if not script_tag:
                print(f"Пропуск том {vol} глава {ch}")
                continue

            matches = re.findall(
                r"\['(https?://[^']+/)','',\"([^\"]+)\"",
                script_tag.string
            )

            cleaned_urls = [domain + path for domain, path in matches]

            for i, src in enumerate(tqdm(cleaned_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                ext = src.split(".")[-1][:3]

                if ext not in ("jpg", "png", "svg", "gif"):
                    ext = src.split(".")[-1][:4]

                attempt = 0
                max_attempts = 10  # количество попыток повторного скачивания

                while attempt < max_attempts:
                    try:
                        resp, content = http.request(src, headers=self.headers_img)

                        while resp.status in (429, 522):
                            print(f"Ошибка скачивания {src}: {resp.status} — повтор")
                            time.sleep(1)
                            resp, content = http.request(src, headers=self.headers_img)

                        if resp.status in (300, 502):
                            src = src.split("?", 1)[0]
                            resp, content = http.request(src, headers=self.headers_img)

                        if resp.status != 200:
                            print(f"Ошибка скачивания {src}: {resp.status}")
                            break

                        with open(os.path.join(chapter_path, f"{i}.{ext}"), 'wb') as f:
                            f.write(content)

                        time.sleep(random.uniform(0.25, 0.35))
                        break

                    except IncompleteRead:
                        attempt += 1
                        print(f"IncompleteRead при скачивании {src}. Попытка {attempt}/{max_attempts}.")
                        if attempt >= max_attempts:
                            print(f"Не удалось скачать {src} после {max_attempts} попыток.")
                        else:
                            time.sleep(0.3)

                    except Exception as e:
                        print(f"Ошибка при скачивании страницы: {e}")
                        break

        self.driver.quit()