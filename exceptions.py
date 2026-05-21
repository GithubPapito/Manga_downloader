class MangaDownloaderError(Exception):
    """Базовая ошибка приложения."""


class MangaNotFoundError(MangaDownloaderError):
    """Манга не найдена."""


class ChapterFetchError(MangaDownloaderError):
    """Не удалось получить главы."""


class DownloadError(MangaDownloaderError):
    """Ошибка скачивания."""