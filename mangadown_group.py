import os
import time
from tqdm import tqdm
import httplib2
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from utils import qest, create_save, authorization, convert_to_pdf, check_status, sanitize_filename

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
        self.links = qest(self.my_cwd, self.links)
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.url)
        driver = authorization(driver, self.my_cwd)

        for rev, link in enumerate(self.links):
            vol, ch = link.split('/')[2:4]
            path = os.path.join(self.my_cwd, self.manga_name, vol, ch)
            full_url = self.url.rsplit('/', 1)[0] + link

            try:
                driver.get(full_url)
                pages_element = WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CLASS_NAME, 'pages-count')))
                pages = int(pages_element.text)

                for y in tqdm(range(1, pages + 1), desc=link):
                    img = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, 'manga-img')))
                    src = img.get_attribute('src')
                    fileType = src.split(".")[-1][:3]
                    if fileType not in ("jpg", "png", "svg"):
                        fileType = src.split(".")[-1][:4]

                    h = httplib2.Http('.cache')
                    response, content = h.request(src)
                    if response.status != 200:
                        print(f"Ошибка скачивания {src}: {response.status}")
                        continue

                    with open(os.path.join(path, f"{y}.{fileType}"), 'wb') as f:
                        f.write(content)
                    self._click_next_button(driver)

                create_save(rev + 1, self.links)
            except Exception as e:
                print(f"Ошибка при скачивании главы {link}: {e}")
                continue


        driver.close()
        print('Скачивание завершено')


    def _click_next_button(self, driver):
        """Пытается нажать кнопку 'Далее' с обработкой ошибок."""
        errCount = 0
        while errCount <= 50:
            try:
                next_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'nextButton')))
                next_btn.click()
                return
            except:
                errCount += 1
                if errCount % 10 == 0:
                    driver.refresh()
                    time.sleep(0.5)
                else:
                    time.sleep(0.2)
        driver.close()
        print('Ошибка: не удалось нажать кнопку "Далее".')
        exit(0)