import os
import random
import time
import re
from http.client import IncompleteRead
from tqdm import tqdm
import httplib2
import requests
from bs4 import BeautifulSoup
from utils import authorization, convert_to_pdf, check_status, sanitize_filename

class MangaDownGroup:
    def __init__(self, url, dom, sel):
        self.url = url
        self.domain = dom
        self.headers = {
            "accept": "*/*",
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "host": dom,
            "referer": f"https://{dom}/",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            )
        }

        self.headers_img = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        }

        self.links = []
        self.manga_name = None
        self.cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        convert_to_pdf(self.cwd, self.manga_name, sel)

    def get_manga_data(self):
        """Получает данные о манге (название)."""
        try:
            response = requests.get(self.url, headers=self.headers)
            check_status(response.status_code)
            page = BeautifulSoup(response.content, 'html.parser')
            self.manga_name = page.select_one('span.name').text
        except Exception as e:
            print(f"Ошибка при получении данных манги: {e}")
            exit(0)

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
            print(f"Ошибка при получении списка глав: {e}")
            exit(0)

    def create_path(self):
        """Создает директории для сохранения манги."""
        self.manga_name = sanitize_filename(self.manga_name)
        base_path = os.path.join(self.cwd, self.manga_name)
        os.makedirs(base_path, exist_ok=True)

        for link in self.links:
            vol, ch = link.split('/')[2:4]
            os.makedirs(os.path.join(base_path, vol, ch), exist_ok=True)

    def download(self):
        """Скачивает главы манги."""
        http = httplib2.Http('.cache')

        session = requests.Session()
        authorization(session=session, my_cwd=self.cwd)

        for _, link in enumerate(self.links):
            vol, ch = link.split('/')[2:4]
            chapter_path = os.path.join(self.cwd, self.manga_name, vol, ch)
            full_url = self.url.rsplit('/', 1)[0] + link

            response = session.get(full_url, timeout=10, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            script_tag = soup.find("script", string=lambda x: x and "rm_h.readerInit" in x)
            if not script_tag:
                print(f"Ошибка: не найден блок данных со страницами главы, для сайта {self.domain} необходим файл cookies")
                time.sleep(15)
                exit(0)

            matches = re.findall(
                r"\['(https?://[^']+/)','',\"([^\"]+\.[a-zA-Z0-9]{3,4})",
                script_tag.string
            )
            cleaned_urls = [domain + path for domain, path in matches]

            for i, src in enumerate(tqdm(cleaned_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                ext = src.split(".")[-1][:3]
                if ext not in ("jpg", "png", "svg"):
                    ext = src.split(".")[-1][:4]

                attempt = 0
                max_attempts = 10  # количество попыток повторного скачивания

                while attempt < max_attempts:
                    try:
                        resp, content = http.request(src, headers=self.headers_img)

                        while resp.status in (429, 522):
                            print(f"Ошибка скачивания {src}: {resp.status} — повтор")
                            time.sleep(0.25)
                            resp, content = http.request(src, headers=self.headers_img)

                        if resp.status != 200:
                            print(f"Ошибка скачивания {src}: {resp.status}")
                            break

                        with open(os.path.join(chapter_path, f"{i}.{ext}"), 'wb') as f:
                            f.write(content)

                        time.sleep(random.uniform(0.35, 0.5))
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