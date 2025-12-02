import os
import json
import time
import img2pdf
from tqdm import tqdm
import re
import zipfile

def selection():
    y = input("Создать PDF или CBZ (по умолчанию PDF)")
    if y in ["CBZ", "cbz", "2", "c"]:
        return "cbz"
    else:
        return "pdf"

def authorization(session, my_cwd):
    """Авторизует пользователя с использованием cookies."""
    if 'cookies.json' in os.listdir(my_cwd):
        with open('cookies.json', 'r') as file:
            for c in json.load(file):
                session.cookies.set(c["name"], c["value"], domain=c.get("domain"))
            return session
    return None

def convert_to_pdf(my_cwd, manga_name, format):
    """Конвертирует изображения в PDF."""
    print(f'Создание {format}')
    path = os.path.join(my_cwd, manga_name)
    for n in tqdm(os.listdir(path), desc=f'Прогресс создания {format}'):
        vol_path = os.path.join(path, n)
        image_files = []
        for v in sorted(os.listdir(vol_path), key=lambda x: float(x)):
            img_path = os.path.join(vol_path, v)
            files = os.listdir(img_path)
            image_files.extend([os.path.join(img_path, img) for img in sorted(files, key=lambda p: float(re.search(r'(\d+)', p).group()))])
        if format == "cbz":
            out_name = os.path.join(path, f"{n}.cbz")
            total = len(image_files)  # сколько всего страниц
            digits = len(str(total))  # сколько цифр нужно для нумерации
            with zipfile.ZipFile(out_name, 'w', zipfile.ZIP_DEFLATED) as cbz:
                for index, image_path in enumerate(image_files, 1):
                    ext = os.path.splitext(image_path)[1]  # .png / .jpg и т.д.
                    num = str(index).zfill(digits)  # 0001, 0002 ...
                    arcname = f"том {n} изображение {num}{ext}"
                    cbz.write(image_path, arcname)
        else:
            pdf_data = img2pdf.convert(image_files)
            with open(os.path.join(path, f"{n}.pdf"), "wb") as file:
                file.write(pdf_data)
    print(f'Создание {format} завершено')

def check_status(status_code):
    """Проверяет статус ответа сервера."""
    if status_code != 200:
        print(f'TERMINATED! Server return code {status_code}!')
        time.sleep(20)
        exit(0)

def sanitize_filename(name):
    """Очищает имя от недопустимых символов."""
    return re.sub(r'[\\/:*?"<>|~]', '_', name)