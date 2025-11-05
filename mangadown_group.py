import os
import random
import time
from tqdm import tqdm
import httplib2
from bs4 import BeautifulSoup
import requests
from utils import qest, authorization, convert_to_pdf, check_status, sanitize_filename
import re

class MangaDown_group:
    def __init__(self, url, dom, sel):
        self.url = url
        self.headers = {
            "accept": "*/*",
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "host": f"{dom}",
            "referer": f"https://{dom}/",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        self.headers1 = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        self.links = []
        self.manga_name = None
        self.my_cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        convert_to_pdf(self.my_cwd, self.manga_name, sel)

    def get_manga_data(self):
        """Получает данные о манге."""
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
            self.links = [lnk['href'] for div in page.find_all('div', class_="chapters")
                          for lnk in div.find_all('a', class_="chapter-link")]
            self.links.reverse()
        except Exception as e:
            print(f"Ошибка при получении списка глав: {e}")
            exit(0)

    def create_path(self):
        """Создает директории для сохранения манги."""
        self.manga_name = sanitize_filename(self.manga_name)
        path = os.path.join(self.my_cwd, self.manga_name)
        os.makedirs(path, exist_ok=True)
        for n in self.links:
            vol, ch = n.split('/')[2:4]
            os.makedirs(os.path.join(path, vol, ch), exist_ok=True)

    def download(self):
        """Скачивает главы манги."""
        h = httplib2.Http('.cache')
        self.links = qest(self.my_cwd, self.links)
        session = requests.Session()
        authorization(session=session, my_cwd=self.my_cwd)

        for rev, link in enumerate(self.links):
            vol, ch = link.split('/')[2:4]
            path = os.path.join(self.my_cwd, self.manga_name, vol, ch)
            full_url = self.url.rsplit('/', 1)[0] + link

            response =  session.get(full_url, timeout=10, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            script_tag = soup.find("script", string=lambda x: x and "rm_h.readerInit" in x)

            try:
                script_text = script_tag.string
            except Exception as e:
                print(f"Ошибка при получении страницы: {e}")
                print("Попробуйте с куки")
                time.sleep(15)
                exit(0)

            pattern = r"\['(https?://[^']+/)','',\"([^\"]+\.[a-zA-Z0-9]{3,4})[^\"']*\""
            matches = re.findall(pattern, script_text)

            cleaned_urls = [domain + path for domain, path in matches]

            for i, src in enumerate(tqdm(cleaned_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                fileType = src.split(".")[-1][:3]
                if fileType not in ("jpg", "png", "svg"):
                    fileType = src.split(".")[-1][:4]
                try:
                    response, content = h.request(src, headers=self.headers1)
                    while response.status in (429, 522):
                        print(f"Ошибка скачивания {src}: {response.status}")
                        time.sleep(0.1)
                        print("Повторное скачивание")
                        response, content = h.request(src, headers=self.headers1)
                    if response.status != 200:
                        print(f"Ошибка скачивания {src}: {response.status}")
                        continue
                    with open(os.path.join(path, f"{i}.{fileType}"), 'wb') as f:
                        f.write(content)
                    time.sleep(random.uniform(0.1, 0.25))
                except Exception as e:
                    print(f"Ошибка при скачивании страницы: {e}")