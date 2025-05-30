import re
import requests
import os
import time
import random
from tqdm import tqdm
import httplib2
from utils import convert_to_pdf, sanitize_filename


class MangaDown_MLib:
    def __init__(self, url, dom, img_url):
        self.url = url
        self.token = None
        self.manga_name = None
        self.slug_url = None
        self.my_cwd = os.getcwd()
        self.volumes = {}
        self.base_url = "https://api.cdnlibs.org/api/manga"
        self.img_url = img_url

        self.get_tok()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": f"{dom}",
            "Referer": f"{dom}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        }

        self.get_slug()
        self.get_manga_data()
        self.get_chapters()
        self.create_path()
        self.download()
        convert_to_pdf(self.my_cwd, self.manga_name)

    def get_tok(self):
        """Запрашивает токен авторизации."""
        print("Введите токен (если манга доступна для общего просмотра, можно оставить пустым (просто Enter))")
        self.token = input()

    def get_pages(self, vol, ch):
        """Получает список страниц главы."""
        endpoint = f"{self.base_url}/{self.slug_url}/chapter"
        params = {"number": ch, "volume": vol}

        try:
            response = requests.get(endpoint, params=params, timeout=10, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                pages = data.get("data", {}).get("pages", [])
                return [
                    f"https://{self.img_url}{page['url']}"
                    if page["url"].startswith("//manga/")
                    else page["url"]
                    for page in pages
                ]
            print(f"Ошибка при получении страниц: {response.status_code}")
            time.sleep(3)
            return None
        except Exception as e:
            print(f"Ошибка при получении страниц: {e}")
            return None

    def download(self):
        """Скачивает все главы манги."""
        h = httplib2.Http('.cache')
        for vol in self.volumes:
            for ch in self.volumes[vol]:
                page_urls = self.get_pages(vol, ch)
                if not page_urls:
                    print(f"Страницы не найдены для тома {vol}, главы {ch}!")
                    continue

                path = os.path.join(self.my_cwd, self.manga_name, f'vol{vol}', ch)
                for i, src in enumerate(tqdm(page_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                    fileType = src.split(".")[-1][:3]
                    try:
                        response, content = h.request(src, headers=self.headers)
                        if response.status != 200:
                            print(f"Ошибка скачивания {src}: {response.status}")
                            continue
                        with open(os.path.join(path, f"{i}.{fileType}"), 'wb') as f:
                            f.write(content)
                        time.sleep(random.uniform(0.15, 0.5))
                    except Exception as e:
                        print(f"Ошибка при скачивании страницы: {e}")

    def create_path(self):
        """Создает структуру папок для сохранения."""
        self.manga_name = sanitize_filename(self.manga_name)
        path = os.path.join(self.my_cwd, self.manga_name)
        os.makedirs(path, exist_ok=True)
        for vol in self.volumes:
            for ch in self.volumes[vol]:
                os.makedirs(os.path.join(path, f'vol{vol}', ch), exist_ok=True)

    def get_chapters(self):
        """Получает список всех глав манги."""
        url = f"{self.base_url}/{self.slug_url}/chapters"
        try:
            response = requests.get(url, timeout=10, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                m_data = data.get("data", [])
                for chapter in m_data:
                    volume_number = chapter.get("volume", "0")
                    if volume_number not in self.volumes:
                        self.volumes[volume_number] = []
                    self.volumes[volume_number].append(chapter.get("number", "0"))
                return
            print(f"Ошибка при получении глав: {response.status_code}")
        except Exception as e:
            print(f"Ошибка при получении списка глав: {e}")
        time.sleep(10)
        exit(0)

    def get_slug(self):
        """Извлекает slug манги из URL."""
        try:
            self.slug_url = re.search(r'manga/(.+?)(?:\?|$)', self.url).group(1)
        except (AttributeError, IndexError):
            self.slug_url = self.url.rstrip('/').split('/')[-1]
        if not self.slug_url:
            raise ValueError(f"Не удалось извлечь slug из URL: {self.url}")

    def get_manga_data(self):
        """Получает основную информацию о манге."""
        try:
            response = requests.get(f"{self.base_url}/{self.slug_url}", timeout=10, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                self.manga_name = data.get("data", {}).get("name", "Unknown Manga")
                return
            print(f"Ошибка при получении информации о манге: {response.status_code}")
        except Exception as e:
            print(f"Ошибка при получении данных манги: {e}")
        time.sleep(10)
        exit(0)