import re
from bs4 import BeautifulSoup
import requests
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import img2pdf
from tqdm import tqdm
import httplib2
import random
import logging

class MangaDown:
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        self.links = []
        self.manga_name = ''
        self.my_cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        self.conwert_to_pdf()

    def check_status(self, status_code):
        if status_code != 200:
            print(f'TERMINATED! Server return code {status_code}!')
            exit(0)

    def get_manga_data(self):
        response = requests.get(self.url, headers=self.headers)

        self.check_status(response.status_code)

        page = BeautifulSoup(response.content, 'html.parser')
        self.manga_name = page.select_one('span.name').text

    def get_chapter_links(self):
        response = requests.get(self.url, headers=self.headers)

        self.check_status(response.status_code)

        page = BeautifulSoup(response.content, 'html.parser')

        for div in page.find_all('div', class_="chapters"):
            for lnk in div.find_all('a', class_="chapter-link"):
                self.links.append(lnk['href'])

        self.links.reverse()

    def create_path(self):
        regex = re.compile('[\\\/\:\*\?\""\<\>\|]')
        self.manga_name = regex.sub(' ', self.manga_name)
        path = os.path.join(self.my_cwd, self.manga_name)

        if not os.path.exists(path):
            os.mkdir(path)

        for n in self.links:
            a = n.split('/')
            vol = a[2]
            ch = a[3]
            new_dir = str(vol)
            path = os.path.join(self.my_cwd + '\\' + self.manga_name, new_dir)

            if not os.path.exists(path):
                os.mkdir(path)

            new_dir = str(ch)
            path = os.path.join(self.my_cwd + '\\' + self.manga_name + '\\' + str(vol), new_dir)
            if not os.path.exists(path):
                os.mkdir(path)

    def download(self):
        url = self.url[:self.url.rfind('/')]
        logging.getLogger('selenium').setLevel(logging.WARNING)
        driver = webdriver.Edge()
        first = True

        for i in self.links:
            a = i.split('/')
            vol = a[2]
            ch = a[3]
            path = os.path.join(self.my_cwd + '\\' + self.manga_name + '\\' + vol + '\\' + ch)
            driver.get(url + i)

            if first:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'btn-lg'))
                    )
                    element.click()
                    first = False
                except:
                    first = False

            time.sleep(0.5)

            no = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'pages-count'))
            )

            for y in tqdm (range(int(no.text)), desc=i):

                img = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, 'manga-img'))
                )

                src = img.get_attribute('src')
                fileType = src.split(".")[-1]

                h = httplib2.Http('.cache')
                response, content = h.request(src)
                with open(os.path.join(path, str(y) + "." + fileType[0:3]), 'wb') as f:
                    f.write(content)

                errCount = 0

                while True:
                        if errCount > 100:
                            driver.close()
                            print('not good')
                            exit(0)
                        try:
                            element = WebDriverWait(driver, 5).until(
                                EC.visibility_of_element_located((By.CLASS_NAME, 'nextButton'))
                            )
                            element.click()
                        except:
                            errCount += 1
                            time.sleep(0.2)
                            continue
                        break

                time.sleep(random.uniform(0.2, 0.4))

        driver.close()
        print('Скачивание завершен')

    def conwert_to_pdf(self):
        print('Создание PDF')

        path = os.path.join(self.my_cwd + '\\' + self.manga_name)
        dir = os.listdir(path)

        for n in dir:
            path = os.path.join(self.my_cwd + '\\' + self.manga_name + '\\' + n)
            vol = os.listdir(path)
            image_files = []
            ch = []

            for y in vol:
                ch.append(int(y))
            ch.sort()

            for v in ch:
                img = os.listdir(path + '\\' + str(v))
                img = sorted(img, key=lambda p: img[:p.find('.')])
                for i in img:
                    image_files.append(path + '\\' + str(v) + '\\' + i)

            pdf_data = img2pdf.convert(image_files)
            with open(self.my_cwd + '\\' + self.manga_name + '\\' + n + ".pdf", "wb") as file:
                file.write(pdf_data)

        print('Создание PDF завершено')

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input()
    MangaDown(url)