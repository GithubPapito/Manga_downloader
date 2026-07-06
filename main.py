import re
import os
import questionary
from mangadown_mlib import MangaDown_MLib
from mangadown_group import MangaDownGroup
from exceptions import MangaDownloaderError
from questionary import Style

custom_style = Style([
    ('qmark', 'fg:#ff9d00 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#ff9d00 bold'),
    ('highlighted', 'fg:#ff9d00 bold'),
])

# Поддерживаемые домены
M_LIB = ["mangalib.me", "mangalib.org"]
H_LIB = ["hentailib.me"]
IMG_URLS = ["img3.cdnlibs.org", "img3h.hentaicdn.org"]
GROUP_L = ["web.usagi.one", "1.seimanga.me", "a.zazaza.me"]

# -------------------------------------------------
# UI
# -------------------------------------------------

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def title():
    print("=" * 60)
    print("        Manga Downloader")
    print("=" * 60)

def ask_url():
    return questionary.text(
        "Введите ссылку:",
        style=custom_style,
        validate=lambda text:
        True if get_domain(text) in (M_LIB + H_LIB + GROUP_L)
        else "Данный сайт не поддерживается"
    ).ask()

def ask_format():
    result = questionary.select(
        "Выберите формат:",
        style=custom_style,
        choices=[
            "PDF",
            "CBZ"
        ]
    ).ask()
    return result.lower()

def ask_token():
    print("\nВведите токен")
    print("(если не нужен — просто Enter)")

    return input("> ").strip()

def ask_continue():
    return questionary.confirm(
        "Скачать ещё одну мангу?",
        style=custom_style
    ).ask()

# -------------------------------------------------
# Получение домена
# -------------------------------------------------

def get_domain(url):
    match = re.search(r'//([^/]+)/', url)

    if not match:
        return None

    return match.group(1)

# -------------------------------------------------
# Получение списка глав
# -------------------------------------------------

def get_chapters_mlib(loader):

    chapters = []

    for vol in loader.volumes:
        for ch in loader.volumes[vol]:
            chapters.append((vol, ch))

    return chapters

def get_chapters_group(loader):

    chapters = []

    for link in loader.links:

        try:
            vol, ch = link.split('/')[2:4]
            chapters.append((vol, ch))

        except Exception:
            pass

    return chapters

# -------------------------------------------------
# Выбор глав
# -------------------------------------------------

def select_chapters(chapters):
    choices = []

    for vol, ch in chapters:
        choices.append(
            f"Том {vol} Глава {ch}"
        )

    selected = questionary.checkbox(
        "Выберите главы:",
        style=custom_style,
        choices=choices
    ).ask()

    result = []

    for item in selected:
        parts = item.replace("Том ", "").replace(" Глава ", ":")
        vol, ch = parts.split(":")

        result.append((vol, ch))

    return result

# -------------------------------------------------
# Фильтрация MangaLib
# -------------------------------------------------

def filter_mlib(loader, selected):

    filtered = {}

    for vol, ch in selected:

        if vol not in filtered:
            filtered[vol] = []

        filtered[vol].append(ch)

    loader.volumes = filtered

# -------------------------------------------------
# Фильтрация Group
# -------------------------------------------------

def filter_group(loader, selected):

    selected_set = {
        f"{vol}:{ch}"
        for vol, ch in selected
    }

    loader.links = [
        link for link in loader.links
        if f"{link.split('/')[2]}:{link.split('/')[3]}"
        in selected_set
    ]

# -------------------------------------------------
# Запуск MangaLib
# -------------------------------------------------

def run_mlib(url, dom, img_url, api_url, site_id, fmt):

    # создаём объект
    loader = MangaDown_MLib(
        url,
        dom,
        img_url,
        fmt,
        api_url,
        site_id,
        auto_start=False
    )

    chapters = get_chapters_mlib(loader)

    selected = select_chapters(chapters)

    filter_mlib(loader, selected)

    print("\nЗапуск скачивания...")

    loader.start()

# -------------------------------------------------
# Запуск Group
# -------------------------------------------------

def run_group(url, dom, fmt):
    loader = MangaDownGroup(
        url,
        dom,
        fmt,
        auto_start=False
    )

    chapters = get_chapters_group(loader)

    selected = select_chapters(chapters)

    filter_group(loader, selected)

    print("\nЗапуск скачивания...")

    loader.start()

# -------------------------------------------------
# Основная логика
# -------------------------------------------------

def run():

    clear()
    title()

    url = ask_url()

    dom = get_domain(url)

    fmt = ask_format()

    if dom in M_LIB:

        run_mlib(
            url,
            dom,
            IMG_URLS[0],
            "https://api.cdnlibs.org/api/manga",
            "1",
            fmt
        )

    elif dom in H_LIB:

        run_mlib(
            url,
            dom,
            IMG_URLS[1],
            "https://hapi.hentaicdn.org/api/manga",
            "4",
            fmt
        )

    elif dom in GROUP_L:

        run_group(url, dom, fmt)

# -------------------------------------------------
# Entry Point
# -------------------------------------------------


if __name__ == "__main__":

    while True:

        try:
            run()

        except KeyboardInterrupt:
            print("\n\nВыход...")
            break

        except MangaDownloaderError as e:
            print(f"\nОшибка: {e}")

        except Exception as e:
            print(f"\nНеожиданная ошибка: {e}")

        if not ask_continue():
            break

    print("\nРабота завершена")
