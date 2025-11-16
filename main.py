import re
import time
from mangadown_mlib import MangaDown_MLib
from mangadown_group import MangaDownGroup
from utils import selection

# Поддерживаемые домены
M_LIB = ["mangalib.me", "mangalib.org"]
H_LIB = ["hentailib.me"]
IMG_URLS = ["img33.imgslib.link", "img3h.hentaicdn.org"]
GROUP_L = ["web.usagi.one", "1.seimanga.me", "a.zazaza.me"]

def domain_definition(url, sel):
    """Определяет тип сайта и запускает соответствующий загрузчик."""
    dom = re.search(r'//([^/]+)/', url).group(1)
    if dom in M_LIB:
        MangaDown_MLib(url, dom, IMG_URLS[0], sel, "https://api.cdnlibs.org/api/manga", "1")
    elif dom in H_LIB:
        MangaDown_MLib(url, dom, IMG_URLS[1], sel, "https://hapi.hentaicdn.org/api/manga", "4")
    elif dom in GROUP_L:
        MangaDownGroup(url,  dom, sel)
    else:
        print("Адрес не поддерживается. Проверьте обновления программы.")
        time.sleep(15)
        exit(0)
    time.sleep(20)

if __name__ == "__main__":
    print("Введите адрес манги")
    url = input().strip()
    sel = selection()
    domain_definition(url, sel)