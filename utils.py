import os
import json
import img2pdf
from tqdm import tqdm
import re
import zipfile

def selection():
    y = input("Создать PDF или CBZ (по умолчанию PDF)")
    if y in ["CBZ", "cbz"]:
        return "cbz"
    else:
        return "pdf"

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

def convert_to_pdf(my_cwd, manga_name, format):
    """Конвертирует изображения в PDF."""
    print(f'Создание {format}')
    path = os.path.join(my_cwd, manga_name)
    for n in tqdm(os.listdir(path), desc='Прогресс создания PDF'):
        vol_path = os.path.join(path, n)
        image_files = []
        for v in sorted(os.listdir(vol_path), key=lambda x: float(x)):
            img_path = os.path.join(vol_path, v)
            files = os.listdir(img_path)
            image_files.extend([os.path.join(img_path, img) for img in sorted(files, key=lambda p: float(re.search(r'(\d+)', p).group()))])
        if format == "cbz":
            with zipfile.ZipFile(f"{path}\\{n}.cbz", 'w', zipfile.ZIP_DEFLATED) as cbz:
                for image_path in image_files:
                    cbz.write(image_path, image_path)
        else:
            pdf_data = img2pdf.convert(image_files)
            with open(os.path.join(path, f"{n}.pdf"), "wb") as file:
                file.write(pdf_data)
    print(f'Создание {format} завершено')

def check_status(status_code):
    """Проверяет статус ответа сервера."""
    if status_code != 200:
        print(f'TERMINATED! Server return code {status_code}!')
        exit(0)

def sanitize_filename(name):
    """Очищает имя от недопустимых символов."""
    return re.sub(r'[\\/:*?"<>|~]', ' ', name)