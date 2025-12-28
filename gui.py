import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import re
import os
import contextlib
from mangadown_mlib import MangaDown_MLib
from mangadown_group import MangaDownGroup

# Поддерживаемые домены
M_LIB = ["mangalib.me", "mangalib.org"]
H_LIB = ["hentailib.me"]
IMG_URLS = ["img33.imgslib.link", "img3h.hentaicdn.org"]
GROUP_L = ["web.usagi.one", "1.seimanga.me", "a.zazaza.me"]


class MangaDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Загрузчик манги")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Переменные
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="pdf")
        self.token_var = tk.StringVar()
        self.cookies_path_var = tk.StringVar()
        self.is_downloading = False
        self.download_thread = None
        self.cancel_flag = threading.Event()
        
        self.create_widgets()
        
        if os.path.exists('cookies.json'):
            self.cookies_path_var.set('cookies.json')
    
    def create_widgets(self):
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка весов для растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Загрузчик манги", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL
        ttk.Label(main_frame, text="URL манги:").grid(row=1, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # Формат вывода
        ttk.Label(main_frame, text="Формат вывода:").grid(row=2, column=0, sticky=tk.W, pady=5)
        format_frame = ttk.Frame(main_frame)
        format_frame.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Radiobutton(format_frame, text="PDF", variable=self.format_var, 
                       value="pdf").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="CBZ", variable=self.format_var, 
                       value="cbz").pack(side=tk.LEFT, padx=5)
        
        # Токен для MangaLib (опционально)
        ttk.Label(main_frame, text="Токен (MangaLib):").grid(row=3, column=0, sticky=tk.W, pady=5)
        token_frame = ttk.Frame(main_frame)
        token_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        token_frame.columnconfigure(0, weight=1)
        
        token_entry = ttk.Entry(token_frame, textvariable=self.token_var, width=40)
        token_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Label(token_frame, text="(оставьте пустым, если не требуется)", 
                 font=("Arial", 8), foreground="gray").grid(row=1, column=0, sticky=tk.W)
        
        # Cookies для других сайтов
        ttk.Label(main_frame, text="Cookies файл:").grid(row=4, column=0, sticky=tk.W, pady=5)
        cookies_frame = ttk.Frame(main_frame)
        cookies_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        cookies_frame.columnconfigure(0, weight=1)
        
        cookies_entry = ttk.Entry(cookies_frame, textvariable=self.cookies_path_var, width=40)
        cookies_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        cookies_browse_btn = ttk.Button(cookies_frame, text="Обзор...", 
                                       command=self.browse_cookies_file)
        cookies_browse_btn.grid(row=0, column=1)
        
        ttk.Label(cookies_frame, text="(требуется для Usagi, SeiManga, ReadManga)", 
                 font=("Arial", 8), foreground="gray").grid(row=1, column=0, sticky=tk.W)
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.download_btn = ttk.Button(button_frame, text="Начать скачивание", 
                                      command=self.start_download, width=20)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Отмена", 
                                    command=self.cancel_download, 
                                    state=tk.DISABLED, width=20)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Прогресс-бар
        self.progress_var = tk.StringVar(value="Готов к работе")
        ttk.Label(main_frame, text="Статус:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.status_label = ttk.Label(main_frame, textvariable=self.progress_var)
        self.status_label.grid(row=6, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Лог-окно
        ttk.Label(main_frame, text="Лог:").grid(row=8, column=0, sticky=(tk.W, tk.N), pady=(10, 5))
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=8, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), 
                      pady=(10, 5), padx=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(8, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=70, 
                                                  wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Информация о поддерживаемых сайтах
        info_frame = ttk.LabelFrame(main_frame, text="Поддерживаемые сайты", padding="5")
        info_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        info_text = ("MangaLib, HentaiLib - требуется токен (опционально)\n"
                    "Usagi, SeiManga, ReadManga - требуется файл cookies.json")
        ttk.Label(info_frame, text=info_text, font=("Arial", 9), 
                 foreground="gray").pack()
    
    def browse_cookies_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл cookies",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.cookies_path_var.set(filename)
            self.log_message(f"Выбран файл cookies: {filename}")
    
    def log_message(self, message):
        """Добавляет сообщение в лог."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Обновляет статус."""
        self.progress_var.set(message)
        self.log_message(message)
        self.root.update_idletasks()
    
    def validate_input(self):
        """Проверяет корректность введенных данных."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Ошибка", "Введите URL манги!")
            return False
        
        # Проверка формата URL
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Ошибка", "URL должен начинаться с http:// или https://")
            return False
        
        # Проверка домена
        try:
            dom = re.search(r'//([^/]+)/', url).group(1)
            if dom not in M_LIB + H_LIB + GROUP_L:
                messagebox.showerror("Ошибка", 
                    f"Домен {dom} не поддерживается.\n"
                    f"Поддерживаемые: {', '.join(M_LIB + H_LIB + GROUP_L)}")
                return False
        except AttributeError:
            messagebox.showerror("Ошибка", "Некорректный URL!")
            return False
        
        # Проверка cookies для других сайтов
        dom = re.search(r'//([^/]+)/', url).group(1)
        if dom in GROUP_L:
            cookies_path = self.cookies_path_var.get().strip()
            if not cookies_path or not os.path.exists(cookies_path):
                result = messagebox.askyesno(
                    "Предупреждение",
                    "Файл cookies не найден. Для скачивания с этого сайта требуется файл cookies.json.\n"
                    "Продолжить без cookies? (скачивание может не работать)"
                )
                if not result:
                    return False
        
        return True
    
    def start_download(self):
        """Запускает процесс скачивания в отдельном потоке."""
        if not self.validate_input():
            return
        
        if self.is_downloading:
            messagebox.showwarning("Предупреждение", "Скачивание уже выполняется!")
            return
        
        self.is_downloading = True
        self.cancel_flag.clear()  # Сбрасываем флаг отмены
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar.start(10)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Запуск в отдельном потоке
        self.download_thread = threading.Thread(target=self.download_manga, daemon=True)
        self.download_thread.start()
    
    def cancel_download(self):
        """Отменяет скачивание."""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите отменить скачивание?"):
            self.is_downloading = False
            self.cancel_flag.set()  # Устанавливаем флаг отмены
            self.finish_download()
            self.update_status("Скачивание отменено пользователем")
    
    def finish_download(self):
        """Завершает процесс скачивания."""
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_bar.stop()
    
    def download_manga(self):
        """Основная функция скачивания."""
        try:
            url = self.url_var.get().strip()
            sel = self.format_var.get()
            
            if not url:
                raise ValueError("URL не может быть пустым")
            
            dom_match = re.search(r'//([^/]+)/', url)
            if not dom_match:
                raise ValueError(f"Не удалось определить домен из URL: {url}")
            dom = dom_match.group(1)
            
            if dom in GROUP_L:
                cookies_path = self.cookies_path_var.get().strip()
                if cookies_path and os.path.exists(cookies_path) and cookies_path != 'cookies.json':
                    import shutil
                    shutil.copy(cookies_path, 'cookies.json')
                    self.update_status(f"Скопирован файл cookies: {cookies_path}")
            
            class PrintRedirector:
                def __init__(self, callback):
                    self.callback = callback
                
                def write(self, text):
                    if text.strip():
                        self.callback(text.strip())
                
                def flush(self):
                    pass
            
            print_redirector = PrintRedirector(self.update_status)
            
            with contextlib.redirect_stdout(print_redirector), \
                 contextlib.redirect_stderr(print_redirector):
                if dom in M_LIB:
                    self.update_status("Запуск загрузчика MangaLib...")
                    token = self.token_var.get().strip()
                    downloader = MangaDown_MLib_GUI(
                        url, dom, IMG_URLS[0], sel, 
                        "https://api.cdnlibs.org/api/manga", "1",
                        token, self.cancel_flag
                    )
                elif dom in H_LIB:
                    self.update_status("Запуск загрузчика HentaiLib...")
                    token = self.token_var.get().strip()
                    downloader = MangaDown_MLib_GUI(
                        url, dom, IMG_URLS[1], sel,
                        "https://hapi.hentaicdn.org/api/manga", "4",
                        token, self.cancel_flag
                    )
                elif dom in GROUP_L:
                    self.update_status("Запуск загрузчика Group...")
                    downloader = MangaDownGroup_GUI(url, dom, sel, self.cancel_flag)
                else:
                    self.update_status("Адрес не поддерживается. Проверьте обновления программы.")
                    self.finish_download()
                    return
            
            self.update_status("Скачивание завершено успешно!")
            self.finish_download()
            self.root.after(0, lambda: messagebox.showinfo("Успех", "Скачивание завершено успешно!"))
            
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            self.update_status(error_msg)
            self.finish_download()
            error_str = str(e)
            self.root.after(0, lambda err=error_str: messagebox.showerror("Ошибка", 
                f"Произошла ошибка при скачивании:\n{err}"))


class MangaDown_MLib_GUI(MangaDown_MLib):
    """Обертка для MangaDown_MLib - переопределяет только get_tok() и download() для поддержки отмены."""
    def __init__(self, url, dom, img_url, sel, base_url, Site_Id, token, cancel_flag):
        self._gui_token = token  # Сохраняем токен для использования в get_tok
        self.cancel_flag = cancel_flag  # Флаг отмены
        self.url = url
        self.token = None
        self.manga_name = None
        self.slug_url = None
        self.my_cwd = os.getcwd()
        self.volumes = {}
        self.base_url = base_url
        self.img_url = img_url

        self.get_tok()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": f"{dom}",
            "Referer": f"{dom}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Site-Id": Site_Id,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        }

        self.get_slug()
        self.get_manga_data()
        self.get_chapters()
        self.create_path()
        self.download()
        if not self.cancel_flag.is_set():
            from utils import convert_to_pdf
            convert_to_pdf(self.my_cwd, self.manga_name, sel)
    
    def get_tok(self):
        """Переопределенный метод, использует токен из GUI вместо input()"""
        self.token = self._gui_token if self._gui_token else ""
    
    def download(self):
        """Переопределенный метод download с поддержкой отмены."""
        import httplib2
        import random
        import time
        from tqdm import tqdm
        
        h = httplib2.Http('.cache')
        for vol in self.volumes:
            if self.cancel_flag.is_set():
                return
            for ch in self.volumes[vol]:
                if self.cancel_flag.is_set():
                    return
                page_urls = self.get_pages(vol, ch)
                if not page_urls:
                    print(f"Страницы не найдены для тома {vol}, главы {ch}!")
                    continue

                path = os.path.join(self.my_cwd, self.manga_name, f'vol{vol}', ch)
                for i, src in enumerate(tqdm(page_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                    if self.cancel_flag.is_set():
                        return
                    fileType = src.split(".")[-1][:3]
                    if fileType not in ("jpg", "png", "svg"):
                        fileType = src.split(".")[-1][:4]
                    try:
                        response, content = h.request(src, headers=self.headers)
                        while response.status in (429, 522):
                            if self.cancel_flag.is_set():
                                return
                            print(f"Ошибка скачивания {src}: {response.status}")
                            time.sleep(0.25)
                            print("Повторное скачивание")
                            response, content = h.request(src, headers=self.headers)
                        if response.status != 200:
                            print(f"Ошибка скачивания {src}: {response.status}")
                            continue
                        with open(os.path.join(path, f"{i}.{fileType}"), 'wb') as f:
                            f.write(content)
                        time.sleep(random.uniform(0.2, 0.35))
                    except Exception as e:
                        print(f"Ошибка при скачивании страницы: {e}")


class MangaDownGroup_GUI(MangaDownGroup):
    """Обертка для MangaDownGroup - переопределяет только download() для поддержки отмены."""
    def __init__(self, url, dom, sel, cancel_flag):
        self.cancel_flag = cancel_flag  # Флаг отмены
        self.url = url
        self.domain = dom
        self.headers = {
            "accept": "*/*",
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "host": dom,
            "referer": f"https://{dom}/",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            )
        }

        self.headers_img = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        }

        self.links = []
        self.manga_name = None
        self.cwd = os.getcwd()

        self.get_manga_data()
        self.get_chapter_links()
        self.create_path()
        self.download()
        if not self.cancel_flag.is_set():
            from utils import convert_to_pdf
            convert_to_pdf(self.cwd, self.manga_name, sel)
    
    def download(self):
        """Переопределенный метод download с поддержкой отмены."""
        import httplib2
        import random
        import time
        from tqdm import tqdm
        from utils import authorization
        import requests
        from bs4 import BeautifulSoup
        import re
        
        http = httplib2.Http('.cache')

        session = requests.Session()
        authorization(session=session, my_cwd=self.cwd)

        for _, link in enumerate(self.links):
            if self.cancel_flag.is_set():
                return
            vol, ch = link.split('/')[2:4]
            chapter_path = os.path.join(self.cwd, self.manga_name, vol, ch)
            full_url = self.url.rsplit('/', 1)[0] + link

            response = session.get(full_url, timeout=10, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')

            script_tag = soup.find("script", string=lambda x: x and "rm_h.readerInit" in x)
            if not script_tag:
                print("Ошибка: не найден блок данных со страницами главы")
                time.sleep(15)
                exit(0)

            matches = re.findall(
                r"\['(https?://[^']+/)','',\"([^\"]+\.[a-zA-Z0-9]{3,4})",
                script_tag.string
            )
            cleaned_urls = [domain + path for domain, path in matches]

            for i, src in enumerate(tqdm(cleaned_urls, desc=f'Скачивание том {vol} глава {ch}'), start=1):
                if self.cancel_flag.is_set():
                    return
                ext = src.split(".")[-1][:3]
                if ext not in ("jpg", "png", "svg"):
                    ext = src.split(".")[-1][:4]

                try:
                    resp, content = http.request(src, headers=self.headers_img)
                    while resp.status in (429, 522):
                        if self.cancel_flag.is_set():
                            return
                        print(f"Ошибка скачивания {src}: {resp.status} — повтор")
                        time.sleep(0.25)
                        resp, content = http.request(src, headers=self.headers_img)

                    if resp.status != 200:
                        print(f"Ошибка скачивания {src}: {resp.status}")
                        continue

                    with open(os.path.join(chapter_path, f"{i}.{ext}"), 'wb') as f:
                        f.write(content)

                    time.sleep(random.uniform(0.35, 0.5))

                except Exception as e:
                    print(f"Ошибка при скачивании страницы: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MangaDownloaderGUI(root)
    root.mainloop()

