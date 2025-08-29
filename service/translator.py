from __future__ import annotations

"""Simple runtime translation support."""


LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
}

_translations: dict[str, dict[str, str]] = {
    "ru": {
        "Image Compression Tool": "Инструмент сжатия изображений",
        "Input Settings": "Настройки ввода",
        "No input directory selected": "Папка исходных файлов не выбрана",
        "Select Input Directory": "Выбрать папку источника",
        "No output directory selected": "Папка сохранения не выбрана",
        "Regenerate output directory name": "Сгенерировать имя выходной папки",
        "Select Output Directory": "Выбрать папку вывода",
        "Save Profiles": "Сохранить профили",
        "Load Profiles": "Загрузить профили",
        "Add Profile": "Добавить профиль",
        "Default": "По умолчанию",
        "Profile {num}": "Профиль {num}",
        "Reset Settings": "Сбросить настройки",
        "Progress": "Прогресс",
        "Ready to compress images": "Готов к сжатию изображений",
        "Start Compression": "Начать сжатие",
        "Compare Images": "Сравнить изображения",
        "Log": "Журнал",
        "Language:": "Язык:",
        "Warning": "Предупреждение",
        "Please select an input directory first.": "Сначала выберите папку исходных файлов.",
        "Output directory already exists. Please regenerate or choose another path.": (
            "Выходная папка уже существует. Сгенерируйте новое имя или выберите другой путь."
        ),
        "No profiles found in file.": "В файле не найдено профилей.",
        "Compression completed! {compressed}/{total} files compressed. {failed} failed.": (
            "Сжатие завершено! {compressed}/{total} файлов сжато. Ошибок: {failed}."
        ),
        "Starting compression...": "Начало сжатия...",
        "Compression error: {error}": "Ошибка сжатия: {error}",
        "Compression Complete": "Сжатие завершено",
        "Compression completed successfully!": "Сжатие успешно завершено!",
        "Compression failed": "Сжатие не удалось",
        "Compression Error": "Ошибка сжатия",
        "An error occurred during compression:\n\n{error}": "Произошла ошибка во время сжатия:\n\n{error}",
        "Error": "Ошибка",
        "Failed to open comparison window:\n\n{error}": "Не удалось открыть окно сравнения:\n\n{error}",
    }
}

_current_language = "en"


def set_language(code: str) -> None:
    """Set the active language code."""
    global _current_language  # noqa: PLW0603
    if code in LANGUAGES:
        _current_language = code


def get_language() -> str:
    """Return the current language code."""
    return _current_language


def tr(text: str) -> str:
    """Translate ``text`` into the currently selected language."""
    return _translations.get(_current_language, {}).get(text, text)
