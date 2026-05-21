import re
from mangadown_mlib import MangaDown_MLib
from mangadown_group import MangaDownGroup
from exceptions import MangaDownloaderError

# Поддерживаемые домены
M_LIB = ["mangalib.me", "mangalib.org"]
H_LIB = ["hentailib.me"]
IMG_URLS = ["img3.mixlib.me", "img3h.hentaicdn.org"]
GROUP_L = ["web.usagi.one", "1.seimanga.me", "a.zazaza.me"]

# -------------------------------------------------
# UI
# -------------------------------------------------

def clear():
    print("\n" * 3)

def title():
    print("=" * 60)
    print("        Manga Downloader")
    print("=" * 60)

def ask_url():
    print("\nВведите ссылку на мангу:")
    return input("> ").strip()

def ask_format():
    print("\nВыберите формат:")
    print("1. PDF")
    print("2. CBZ")

    while True:
        sel = input("> ").strip()

        if sel == "1":
            return "pdf"

        if sel == "2":
            return "cbz"

        print("Неверный выбор")

def ask_token():
    print("\nВведите токен")
    print("(если не нужен — просто Enter)")

    return input("> ").strip()

def ask_continue():
    print("\nСкачать ещё одну мангу? [y/n]")

    return input("> ").lower().strip() == "y"

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
# Отображение глав
# -------------------------------------------------

def print_chapters(chapters):

    print("\nНайденные главы:\n")

    for index, (vol, ch) in enumerate(chapters, start=1):
        print(f"[{index}] Том {vol} Глава {ch}")

# -------------------------------------------------
# Выбор глав
# -------------------------------------------------

def select_chapters(chapters):

    print("\nВведите номера глав")
    print("Пример:")
    print("1,2,3")
    print("1-10")
    print("all")

    raw = input("> ").strip().lower()

    if raw == "all":
        return chapters

    result = []

    parts = raw.split(",")

    for part in parts:

        part = part.strip()

        if "-" in part:

            start, end = part.split("-")

            start = int(start)
            end = int(end)

            for i in range(start, end + 1):

                if 1 <= i <= len(chapters):
                    result.append(chapters[i - 1])

        else:

            try:
                idx = int(part)

                if 1 <= idx <= len(chapters):
                    result.append(chapters[idx - 1])

            except Exception:
                pass

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

    print_chapters(chapters)

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

    print_chapters(chapters)

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

    if not dom:
        print("Неверная ссылка")
        return

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

    else:

        print("\nСайт не поддерживается")

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
