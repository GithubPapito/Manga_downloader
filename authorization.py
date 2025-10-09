import time
from selenium import webdriver
import json
from selenium.webdriver.chrome.options import Options

def authorization(url):
    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    time.sleep(30)

    cookies = driver.get_cookies()
    with open('cookies.json', 'w') as file:
        json.dump(cookies, file)

    driver.close()

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input()
    authorization(url)