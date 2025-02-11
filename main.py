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
import random
import json

def domain_definition(url):
    m = re.search('//(.+?)/', url)
    if m:
        dom = m.group(1)
    print(dom)

def qest(my_cwd, links):
    file = os.listdir(my_cwd)
    for i in file:
        if i == 'save.json':
            save = load_save()
            if len(save) != 0:
                print("Продолжить скачивание с " + save[0] + " ? (y/n)")
                otv = input()
                if otv == "y":
                    return save
    return links

def load_save():
    with open('save.json', 'r') as file:
        save = json.load(file)
    return save

def create_save(rev, links):
    save = links.copy()
    for i in range(rev):
        save.pop(0)
    with open('save.json', 'w') as file:
        json.dump(save, file)

def authorization(driver, my_cwd):
    file = os.listdir(my_cwd)
    for i in file:
        if i == 'cookies.json':
            with open(i, 'r') as file:
                cookies = json.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            return driver

def conwert_to_pdf(my_cwd, manga_name):
    print('Создание PDF')

    path = os.path.join(my_cwd + '\\' + manga_name)
    dir = os.listdir(path)

    for n in tqdm((dir), desc='Прогресс создания PDF: '):
        path = os.path.join(my_cwd + '\\' + manga_name + '\\' + n)
        vol = os.listdir(path)
        image_files = []
        ch = []

        for y in vol:
            try:
                ch.append(int(y))
            except:
                ch.append(float(y))
        ch.sort()

        for v in ch:
            img = os.listdir(path + '\\' + str(v))
            img = sorted(img, key=lambda p: img[:p.find('.')])
            for i in img:
                image_files.append(path + '\\' + str(v) + '\\' + i)

        pdf_data = img2pdf.convert(image_files)
        with open(my_cwd + '\\' + manga_name + '\\' + n + ".pdf", "wb") as file:
            file.write(pdf_data)

    print('Создание PDF завершено')

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
        conwert_to_pdf(self.my_cwd, self.manga_name)

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
        self.links = qest(self.my_cwd, self.links)

        url = self.url[:self.url.rfind('/')]

        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)
        first = True
        rev = 0

        for i in self.links:
            rev += 1
            a = i.split('/')
            vol = a[2]
            ch = a[3]
            path = os.path.join(self.my_cwd + '\\' + self.manga_name + '\\' + vol + '\\' + ch)

            if first:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'btn-lg'))
                    )
                    element.click()
                    first = False
                except:
                    first = False

                try:
                    driver.get(url)
                    driver = authorization(driver, self.my_cwd)
                except:
                    pass

            driver.get(url + i)

            no = WebDriverWait(driver, 15).until(
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
                        if errCount % 10 == 0 and errCount != 0:
                            driver.refresh()
                            time.sleep(0.2)
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

                time.sleep(random.uniform(0.1, 0.3))

            create_save(rev, self.links)

        driver.close()
        print('Скачивание завершено')

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input()
    MangaDown(url)