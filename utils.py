import os
import json
import time
import img2pdf
from tqdm import tqdm
import re
import zipfile
from PIL import Image
import tempfile

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

def fix_image(image_path):
    try:
        img2pdf.convert(image_path)
    except Exception as e:
        print("Проблемный файл:", image_path)
        print(e)
        print("Чиним ...")
        img = Image.open(image_path).convert("RGB")

        tmp_dir = tempfile.gettempdir()
        fixed_path = os.path.join(
            tmp_dir,
            "fixed_" + os.path.basename(image_path).rsplit(".", 1)[0] + ".jpg"
        )

        img.save(fixed_path, "JPEG")
        return fixed_path

    return image_path

def convert_webp_to_jpg(image_path):
    img = Image.open(image_path).convert("RGB")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    img.save(temp_file.name, "JPEG")

    return temp_file.name

def convert_to_pdf(my_cwd, manga_name, format):
    print(f'Создание {format}')
    path = os.path.join(my_cwd, manga_name)

    for n in tqdm(os.listdir(path), desc=f'Прогресс создания {format}'):
        vol_path = os.path.join(path, n)

        image_files = []

        for v in sorted(os.listdir(vol_path), key=lambda x: float(x)):
            img_path = os.path.join(vol_path, v)
            files = os.listdir(img_path)

            image_files.extend([
                os.path.join(img_path, img)
                for img in sorted(
                    files,
                    key=lambda p: float(re.search(r'(\d+)', p).group())
                )
            ])

        # ---- CBZ ----
        if format == "cbz":
            out_name = os.path.join(path, f"{n}.cbz")
            total = len(image_files)
            digits = len(str(total))

            with zipfile.ZipFile(out_name, 'w', zipfile.ZIP_DEFLATED) as cbz:
                for index, image_path in enumerate(image_files, 1):
                    ext = os.path.splitext(image_path)[1].lower()
                    num = str(index).zfill(digits)

                    if ext == ".webp":
                        print("Найден webp, конвертация в jpg")
                        converted_path = convert_webp_to_jpg(image_path)
                        arcname = f"том {n} изображение {num}.jpg"
                        cbz.write(converted_path, arcname)
                    else:
                        arcname = f"том {n} изображение {num}{ext}"
                        cbz.write(image_path, arcname)

        # ---- PDF ----
        else:
            fixed_images = []

            for img_path in image_files:
                fixed = fix_image(img_path)
                fixed_images.append(fixed)

            pdf_data = img2pdf.convert(fixed_images)

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