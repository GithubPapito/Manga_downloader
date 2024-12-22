import re
import urllib.request
from bs4 import BeautifulSoup
import requests
import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import img2pdf

class MangaDown:
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        self.links = []
        self.manga_name = ''

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        self.conwert_to_pdf()

    def check_status(self, status_code):
        if status_code != 200:
            print(f'TERMINATED! Server return code {status_code}!')
            sys.exit(0)

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

    def create_path(self):
        my_cwd = os.getcwd()
        regex = re.compile('[\\\/\:\*\?\""\<\>\|]')
        self.manga_name = regex.sub(' ', self.manga_name)
        path = os.path.join(my_cwd, self.manga_name)

        if not os.path.exists(path):
            os.mkdir(path)

        for n in self.links:
            a = n.split('/')
            vol = a[2]
            ch = a[3]
            new_dir = str(vol)
            path = os.path.join(my_cwd + '\\' + self.manga_name, new_dir)

            if not os.path.exists(path):
                os.mkdir(path)

            new_dir = str(ch)
            path = os.path.join(my_cwd + '\\' + self.manga_name + '\\' + str(vol), new_dir)
            if not os.path.exists(path):
                os.mkdir(path)

    def download(self):
        my_cwd = os.getcwd()
        url = self.url[:self.url.rfind('/')]
        driver = webdriver.Edge()

        for i in self.links:
            a = i.split('/')
            vol = a[2]
            ch = a[3]
            path = os.path.join(my_cwd + '\\' + self.manga_name + '\\' + vol + '\\' + ch)
            driver.get(url + i)
            btn = driver.find_elements(By.CLASS_NAME, 'btn-lg')
            time.sleep(1.3)

            try:
                btn[0].click()
            except:
                pass

            no = driver.find_element(By.CLASS_NAME, 'pages-count')

            for y in range(int(no.text)):
                errCount = 0

                while True:
                    if errCount > 100:
                        print('Error while downloading file ' + i)
                        break
                    try:
                        img = driver.find_element(By.CLASS_NAME, 'manga-img')
                    except:
                        errCount += 1
                        print('Ошибка "1" ' + str(errCount))
                        time.sleep(0.2)
                        continue
                    break

                src = img.get_attribute('src')
                fileType = src.split(".")[-1]

                errCount = 0

                while True:
                    if errCount > 100:
                        print('Error while downloading file ' + i)
                        break
                    try:
                        urllib.request.urlretrieve(src, os.path.join(path, str(y) + "." + fileType[0:3]))
                    except:
                        errCount += 1
                        print('Ошибка "2" ' + str(errCount))
                        time.sleep(0.2)
                        continue
                    break

                errCount = 0

                while True:
                    if errCount > 100:
                        print('Error while downloading file ' + i)
                        break
                    try:
                        btn = driver.find_element(By.CLASS_NAME, 'nextButton')
                        btn.click()
                    except:
                        errCount += 1
                        print('Ошибка "3" ' + str(errCount))
                        time.sleep(0.2)
                        continue
                    break

                time.sleep(0.7)

    def conwert_to_pdf(self):
        my_cwd = os.getcwd()
        path = os.path.join(my_cwd + '\\' + self.manga_name)
        dir = os.listdir(path)

        for n in dir:
            path = os.path.join(my_cwd + '\\' + self.manga_name + '\\' + n)
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
            with open(my_cwd + '\\' + self.manga_name + '\\' + n + ".pdf", "wb") as file:
                file.write(pdf_data)


if __name__ == "__main__":
    print("Адрес манги")
    url = input()
    MangaDown(url)



