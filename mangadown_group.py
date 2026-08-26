import os
import random
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from tqdm import tqdm
import requests
import httplib2
from bs4 import BeautifulSoup
from utils import convert_output_file, check_status, sanitize_filename
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
            "referer": url,
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

        self.links = []                # ссылки на главы
        self.auth_links = {}           # словарь: нормализованный путь -> оригинальная ссылка с параметром d
        self.manga_name = None
        self.cwd = os.getcwd()
        self.driver = None
        self.http = None               # httplib2 клиент
        self.cookie_header = ""        # строка Cookie из Selenium
        self.authenticated = False
        self.PROFILE_DIR_NAME = "chrome_profile"

        self.get_manga_data()
        self.get_chapter_links()

        if auto_start:
            self.start()

    @property
    def profile_path(self):
        return os.path.join(self.cwd, self.PROFILE_DIR_NAME)

    def start(self):
        """Основной метод запуска: инициализация драйвера, проверка авторизации, создание папок, скачивание."""
        try:
            self.driver = self.init_driver(headless=True)
            self.ensure_authenticated(allow_prompt=False)

            self.create_path()
            self.refresh_http_client()
            self.download()
            convert_output_file(self.cwd, self.manga_name, self.sel)
        finally:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

    def get_manga_data(self):
        """Получает название манги из HTML страницы."""
        try:
            response = requests.get(self.url, headers=self.headers)
            check_status(response.status_code)
            page = BeautifulSoup(response.content, 'html.parser')
            self.manga_name = page.find_all('div', class_="py-1")[0].text
        except Exception as e:
            raise MangaNotFoundError(f"Ошибка при получении данных манги: {e}") from e

    def init_driver(self, headless=True):
        """Создаёт Chrome WebDriver с постоянным профилем."""
        os.makedirs(self.profile_path, exist_ok=True)
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.profile_path}")
        chrome_options.add_argument("--profile-directory=Default")
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        driver.command_executor.set_timeout(300)
        return driver

    def get_chapter_links(self):
        """Получает ссылки на все главы (в обратном порядке, от старых к новым)."""
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
        """Создаёт структуру папок: <название>/<том>/<глава>."""
        self.manga_name = sanitize_filename(self.manga_name)
        base_path = os.path.join(self.cwd, self.manga_name)
        os.makedirs(base_path, exist_ok=True)

        for link in self.links:
            parts = link.split("/")
            if len(parts) < 4:
                continue
            vol = parts[2]
            ch = parts[3].split("?", 1)[0]
            os.makedirs(os.path.join(base_path, vol, ch), exist_ok=True)

    def with_mtr(self, url):
        """Добавляет параметр mtr=true для обхода антибота."""
        parts = urlparse(url)
        query = parse_qs(parts.query, keep_blank_values=True)
        query["mtr"] = ["true"]
        return urlunparse(parts._replace(query=urlencode(query, doseq=True)))

    def selen(self, url):
        """Загружает страницу через Selenium с параметром mtr и возвращает HTML."""
        self.driver.get(self.with_mtr(url))
        return self.driver.page_source

    def _normalize_link(self, href):
        """Возвращает ссылку без query-параметров для сопоставления с исходными ссылками."""
        absolute = urljoin(self.url, href)
        parts = urlparse(absolute)
        return parts.path

    def get_authorized_chapter_links(self):
        """Извлекает ссылки на главы, которые имеют параметр d (только для авторизованных)."""
        self.driver.get(self.url)
        page = BeautifulSoup(self.driver.page_source, "html.parser")
        auth_links = {}
        for div in page.find_all("div", class_="chapters"):
            for link in div.find_all("a", class_="chapter-link"):
                href = link.get("href")
                if not href:
                    continue
                absolute = urljoin(self.url, href)
                query = parse_qs(urlparse(absolute).query, keep_blank_values=True)
                if query.get("d", [""])[0]:
                    auth_links[self._normalize_link(href)] = href
        return auth_links

    def ensure_authenticated(self, allow_prompt=True):
        """
        Проверяет наличие авторизации.
        Если авторизация не найдена и allow_prompt=True, открывает браузер для ручного входа.
        Возвращает True, если авторизация подтверждена.
        """
        auth_links = self.get_authorized_chapter_links()
        if auth_links:
            self.auth_links = auth_links
            self.authenticated = True
            self.refresh_http_client()
            print("Авторизация Chrome-профиля успешно обнаружена.")
            return True

        self.auth_links = {}
        self.authenticated = False

        if not allow_prompt:
            return False

        print("\n" + "=" * 70)
        print("ТРЕБУЕТСЯ АВТОРИЗАЦИЯ")
        print("=" * 70)
        print("Выбранная глава доступна только авторизованным пользователям.")
        print("Сейчас откроется Chrome с профилем программы.")
        print("1. Войдите на сайт вручную.")
        print("2. Вернитесь сюда и нажмите Enter.")
        print("=" * 70)

        try:
            self.driver.quit()
        except Exception:
            pass

        self.driver = self.init_driver(headless=False)
        self.driver.get(self.url)
        input("\nПосле успешного входа нажмите Enter здесь... ")

        auth_links = self.get_authorized_chapter_links()
        if not auth_links:
            raise DownloadError("Авторизация не подтверждена")

        self.auth_links = auth_links
        self.authenticated = True
        self.refresh_http_client()
        print("Авторизация успешно подтверждена.")
        return True

    def refresh_http_client(self):
        """Создаёт httplib2 клиент и обновляет cookie_header из текущих cookies Selenium."""
        self.http = httplib2.Http(".cache")

        if self.driver is None:
            self.cookie_header = ""
            return

        cookies = self.driver.get_cookies()
        self.cookie_header = "; ".join(
            f"{cookie['name']}={cookie['value']}"
            for cookie in cookies
        )

    def authenticate_for_current_chapter(self):
        """
        Вызывается, когда требуется авторизация для текущей главы.
        Если уже авторизованы, обновляет cookie_header (на случай протухания).
        Иначе запускает процесс ручной авторизации.
        """
        if self.authenticated:
            self.refresh_http_client()
            return
        self.ensure_authenticated(allow_prompt=True)

    def download(self):
        for link in self.links:
            parts = link.split("/")
            if len(parts) < 4:
                continue

            vol = parts[2]
            ch = parts[3].split("?", 1)[0]
            chapter_path = os.path.join(self.cwd, self.manga_name, vol, ch)

            # Используем ссылку с параметром d, если она есть для авторизованных
            request_link = self.auth_links.get(
                self._normalize_link(link),
                link
            )
            full_url = urljoin(self.url, request_link)

            max_attempts = 4
            script_tag = None

            # Попытки получить страницу с содержимым главы
            for attempt in range(1, max_attempts + 1):
                try:
                    soup = BeautifulSoup(
                        self.selen(full_url),
                        "html.parser"
                    )

                    script_tag = soup.find(
                        "script",
                        string=lambda x: x and "rm_h.readerInit" in x
                    )

                    if not script_tag:
                        print(f"Не удалось получить страницы главы (попытка {attempt}/{max_attempts})")
                        time.sleep(2.5)
                        continue

                    script_text = script_tag.string or ""

                    # Если страницы скрыты (deleted1.png), нужна авторизация
                    if "/static/deleted1.png" in script_text:
                        if not self.authenticated:
                            print(f"Том {vol} глава {ch}: страницы скрыты для неавторизованных пользователей.")
                            self.authenticate_for_current_chapter()

                        if not self.authenticated:
                            raise DownloadError(f"Не удалось авторизоваться для тома {vol}, главы {ch}.")

                        # Обновляем ссылку с учётом авторизации и повторяем попытку
                        request_link = self.auth_links.get(
                            self._normalize_link(link),
                            link
                        )
                        full_url = urljoin(self.url, request_link)
                        continue

                    # Страница успешно получена, обновляем cookies для скачивания
                    self.refresh_http_client()
                    break

                except Exception as e:
                    if attempt >= max_attempts:
                        raise DownloadError(f"Ошибка при получении главы: {e}") from e
                    time.sleep(2.5)

            if not script_tag:
                print(f"Пропуск том {vol} глава {ch}")
                continue

            if "/static/deleted1.png" in (script_tag.string or ""):
                print(f"Не удалось получить изображения том {vol} глава {ch}")
                continue

            # Извлекаем список URL изображений из script-тега
            matches = re.findall(
                r"\['(https?://[^']+/)','',\"([^\"]+)\"",
                script_tag.string or ""
            )
            cleaned_urls = [(domain + path).split("?")[0] for domain, path in matches]

            # Скачиваем каждое изображение
            for i, src in enumerate(
                tqdm(cleaned_urls, desc=f"Скачивание том {vol} глава {ch}"),
                start=1
            ):
                ext = src.split(".")[-1].split("?")[0][:4].lower()
                if ext not in ("jpg", "jpeg", "png", "svg", "gif", "webp"):
                    ext = "jpg"

                headers = dict(self.headers_img)
                if self.cookie_header:
                    headers["Cookie"] = self.cookie_header
                headers["Referer"] = full_url

                attempt = 0
                max_attempts = 10

                while attempt < max_attempts:
                    try:
                        resp, content = self.http.request(
                            src,
                            method="GET",
                            headers=headers
                        )

                        # Если доступ запрещён, пробуем обновить cookies и повторить
                        if resp.status in ("401", "403"):
                            print(f"Доступ к изображению запрещён ({resp.status}), обновляю cookies...")

                            if self.authenticated:
                                self.refresh_http_client()
                                headers["Cookie"] = self.cookie_header
                                attempt += 1
                                time.sleep(1)
                                continue

                            self.authenticate_for_current_chapter()
                            headers["Cookie"] = self.cookie_header
                            attempt += 1
                            time.sleep(1)
                            continue

                        # Временные ошибки сервера – повтор
                        if resp.status in (429, 522, 502):
                            print(f"Ошибка скачивания {src}: {resp.status} — повтор")
                            attempt += 1
                            time.sleep(1)
                            continue

                        if resp.status != 200:
                            print(f"Ошибка скачивания {src}: {resp.status}")
                            break

                        # Сохраняем изображение
                        with open(os.path.join(chapter_path, f"{i}.{ext}"), "wb") as f:
                            f.write(content)

                        time.sleep(random.uniform(0.25, 0.35))
                        break

                    except Exception as e:
                        attempt += 1
                        print(f"Ошибка при скачивании {src}: {e}. Попытка {attempt}/{max_attempts}.")
                        if attempt < max_attempts:
                            time.sleep(0.5)