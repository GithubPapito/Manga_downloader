import re
import time
from mangadown_mlib import MangaDown_MLib
from mangadown_group import MangaDown_group
from utils import selection

# Поддерживаемые домены
M_LIB = ["mangalib.me"]
H_LIB = ["hentailib.me"]
IMG_URLS = ["img33.imgslib.link", "img2h.imgslib.link"]
GROUP_L = [
    "web.usagi.one", "1.seimanga.me", "2.mintmanga.one",
    "selfmanga.live", "rumix.me", "zz.readmanga.io",
    "t.readmanga.io"
]

def domain_definition(url, sel):
    """Определяет тип сайта и запускает соответствующий загрузчик."""
    dom = re.search(r'//([^/]+)/', url).group(1)
    if dom in M_LIB:
        MangaDown_MLib(url, dom, IMG_URLS[0], sel)
    elif dom in H_LIB:
        MangaDown_MLib(url, dom, IMG_URLS[1], sel)
    elif dom in GROUP_L:
        MangaDown_group(url, sel)
    else:
        print("Адрес не поддерживается. Проверьте обновления программы.")
        time.sleep(15)
        exit(0)

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input().strip()
    sel = selection()
    domain_definition(url, sel)