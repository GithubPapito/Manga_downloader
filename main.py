import re
from bs4 import BeautifulSoup
import requests
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import img2pdf
from tqdm import tqdm
import httplib2
import json

def domain_definition(url):
    m_lib = ["mangalib.me"]
    groupl = ["web.usagi.one", "1.seimanga.me", "2.mintmanga.one", "selfmanga.live", "rumix.me", "web.usagi.one"]
    dom = re.search('//(.+?)/', url).group(1)
    if dom in m_lib:
        MangaDown_MLib(url)
    elif dom in groupl:
        MangaDown_group(url)
    else:
        print("Адрес не поддерживается, попробуйте скачать новую версию или напишите в обсуждения на https://github.com/GithubPapito/Manga_downloader")
        time.sleep(15)
        exit(0)

def qest(my_cwd, links):
    """Проверяет наличие сохраненного прогресса и предлагает продолжить с него."""
    if 'save.json' in os.listdir(my_cwd):
        save = load_save()
        if save:
            print(f"Продолжить скачивание с {save[0]}? (y/n)")
            if input().lower() == "y":
                return save
    return links

def load_save():
    """Загружает сохраненный прогресс из файла."""
    with open('save.json', 'r') as file:
        return json.load(file)

def create_save(rev, links):
    """Создает или обновляет файл сохранения."""
    save = links[rev:]
    with open('save.json', 'w') as file:
        json.dump(save, file)

def authorization(driver, my_cwd):
    """Авторизует пользователя с использованием cookies."""
    if 'cookies.json' in os.listdir(my_cwd):
        with open('cookies.json', 'r') as file:
            cookies = json.load(file)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
        driver.refresh()
    return driver

def convert_to_pdf(my_cwd, manga_name):
    """Конвертирует изображения в PDF."""
    print('Создание PDF')
    path = os.path.join(my_cwd, manga_name)
    for n in tqdm(os.listdir(path), desc='Прогресс создания PDF'):
        vol_path = os.path.join(path, n)
        image_files = []
        for v in sorted(os.listdir(vol_path), key=lambda x: float(x)):
            img_path = os.path.join(vol_path, v)
            files = os.listdir(img_path)
            image_files.extend([os.path.join(img_path, img) for img in sorted(files, key=lambda p: files[:p.find('.')])])
        pdf_data = img2pdf.convert(image_files)
        with open(os.path.join(path, f"{n}.pdf"), "wb") as file:
            file.write(pdf_data)
    print('Создание PDF завершено')

class MangaDown_MLib:
    def __init__(self, url):
        self.url = url
        self.manga_name = None
        self.slug_url = None
        self.my_cwd = os.getcwd()
        self.volumes = {}

        self.get_slug()
        self.get_manga_data()
        self.get_chapters()
        self.create_path()
        self.download()
        convert_to_pdf(self.my_cwd, self.manga_name)

    def get_pages(self, vol, ch):
        base_url = "https://api.lib.social/api/manga"
        endpoint = f"{base_url}/{self.slug_url}/chapter"
        params = {
            "number": ch,
            "volume": vol
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pages = data.get("data", {}).get("pages", [])
                return [
                    f"https://img2.imglib.info{page['url']}"
                    if page["url"].startswith("//manga/") else page["url"]
                    for page in pages
                ]
            return []
        except Exception as e:
            print(f"Ошибка при получении страниц: {e}")
            time.sleep(10)
            exit(0)

    def download(self):
        for vol in self.volumes:
            for ch in self.volumes[vol]:
                page_urls = self.get_pages(vol, ch)
                if not page_urls:
                    print(f"Страницы не найдены для тома {vol}, главы {ch}!")
                path = os.path.join(self.my_cwd, self.manga_name, f'vol{vol}', ch)
                for i, src in enumerate(tqdm(page_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                    fileType = src.split(".")[-1][:3]
                    h = httplib2.Http('.cache')
                    response, content = h.request(src)
                    with open(os.path.join(path, f"{i}.{fileType}"), 'wb') as f:
                        f.write(content)

    def create_path(self):
        self.manga_name = re.sub('[\\\/\:\*\?\""\<\>\|]', ' ', self.manga_name)
        path = os.path.join(self.my_cwd, self.manga_name)
        os.makedirs(path, exist_ok=True)
        for vol in self.volumes:
            for ch in self.volumes[vol]:
                os.makedirs(os.path.join(path, f'vol{vol}', ch), exist_ok=True)

    def get_chapters(self):
        url = f"https://api.lib.social/api/manga/{self.slug_url}/chapters"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                m_data = data.get("data", [])
        except Exception as e:
            print(f"Ошибка при получении глав: {e}")
            time.sleep(10)
            exit(0)
        for chapter in m_data:
            volume_number = chapter.get("volume", "0")
            if volume_number not in self.volumes:
                self.volumes[volume_number] = []
            self.volumes[volume_number].append(chapter.get("number", "0"))

    def get_slug(self):
        try:
            self.slug_url = re.search(r'manga/(.+?)(?:\?|$)', self.url).group(1)
        except (AttributeError, IndexError):
            self.slug_url = self.url.rstrip('/').split('/')[-1]
        if not self.slug_url:
            raise ValueError(f"Не удалось извлечь slug из URL: {self.url}")

    def get_manga_data(self):
        try:
            response = requests.get(f"https://api.lib.social/api/manga/{self.slug_url}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.manga_name = data.get("data", {}).get("eng_name", [])
        except Exception as e:
            print(f"Ошибка при получении информации о манге: {e}")
            time.sleep(10)
            exit(0)


class MangaDown_group:
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        self.links = []
        self.manga_name = None
        self.my_cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        convert_to_pdf(self.my_cwd, self.manga_name)

    def check_status(self, status_code):
        """Проверяет статус ответа сервера."""
        if status_code != 200:
            print(f'TERMINATED! Server return code {status_code}!')
            exit(0)

    def get_manga_data(self):
        """Получает данные о манге."""
        response = requests.get(self.url, headers=self.headers)
        self.check_status(response.status_code)
        page = BeautifulSoup(response.content, 'html.parser')
        self.manga_name = page.select_one('span.name').text

    def get_chapter_links(self):
        """Получает ссылки на главы."""
        response = requests.get(self.url, headers=self.headers)
        self.check_status(response.status_code)
        page = BeautifulSoup(response.content, 'html.parser')
        self.links = [lnk['href'] for div in page.find_all('div', class_="chapters") for lnk in div.find_all('a', class_="chapter-link")]
        self.links.reverse()

    def create_path(self):
        """Создает директории для сохранения манги."""
        self.manga_name = re.sub('[\\\/\:\*\?\""\<\>\|]', ' ', self.manga_name)
        path = os.path.join(self.my_cwd, self.manga_name)
        os.makedirs(path, exist_ok=True)
        for n in self.links:
            vol, ch = n.split('/')[2:4]
            os.makedirs(os.path.join(path, vol, ch), exist_ok=True)

    def download(self):
        """Скачивает главы манги."""
        self.links = qest(self.my_cwd, self.links)
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.url)
        driver = authorization(driver, self.my_cwd)
        for rev, link in enumerate(self.links, 1):
            vol, ch = link.split('/')[2:4]
            path = os.path.join(self.my_cwd, self.manga_name, vol, ch)
            url = self.url[:self.url.rfind('/')]
            driver.get(url + link)
            pages = int(WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CLASS_NAME, 'pages-count'))).text)
            for y in tqdm(range(pages), desc=link):
                img = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, 'manga-img')))
                src = img.get_attribute('src')
                fileType = src.split(".")[-1][:3]
                h = httplib2.Http('.cache')
                response, content = h.request(src)
                with open(os.path.join(path, f"{y}.{fileType}"), 'wb') as f:
                    f.write(content)
                self._click_next_button(driver)
            create_save(rev, self.links)
        driver.close()
        print('Скачивание завершено')

    def _click_next_button(self, driver):
        """Пытается нажать кнопку 'Далее' с обработкой ошибок."""
        errCount = 0
        while True:
            if errCount > 50:
                driver.close()
                print('Ошибка: не удалось нажать кнопку "Далее".')
                exit(0)
            if errCount % 10 == 0 and errCount != 0:
                driver.refresh()
                time.sleep(0.2)
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, 'nextButton'))).click()
                break
            except:
                errCount += 1
                time.sleep(0.2)

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input()
    domain_definition(url)