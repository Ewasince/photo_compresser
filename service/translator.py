"""Simple runtime translation support."""

import locale

LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
}

_translations: dict[str, dict[str, str]] = {
    "ru": {
        "Image Compression Tool": "Компрессор изображений",
        "Input Settings": "Настройки ввода",
        "No input directory selected": "Папка исходных файлов не выбрана",
        "Select Input Directory": "Выбрать папку источника",
        "No output directory selected": "Папка сохранения не выбрана",
        "Regenerate output directory name": "Сгенерировать имя выходной папки",
        "Select Output Directory": "Выбрать папку вывода",
        "Regenerate unsupported folder name": "Сгенерировать имя папки неподдерживаемых",
        "Save Profiles": "Сохранить профили",
        "Load Profiles": "Загрузить профили",
        "Add Profile": "Добавить профиль",
        "Default": "По умолчанию",
        "Profile {num}": "Профиль {num}",
        "Profiles: {names}": "Профили {names}",
        "Reset Settings": "Сбросить настройки",
        "Progress": "Прогресс",
        "Ready to compress images": "Готов к сжатию изображений",
        "Start Compression": "Начать сжатие",
        "Abort Compression": "Прервать сжатие",
        "Compare Images": "Сравнить изображения",
        "Log": "Журнал",
        "Language:": "Язык:",
        "Warning": "Предупреждение",
        "Please select an input directory first.": "Сначала выберите папку исходных файлов.",
        "Please select an output directory first.": "Сначала выберите папку вывода.",
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
        "Selected input directory: {path}": "Выбрана папка источника: {path}",
        "Compression settings reset to defaults": "Настройки сжатия сброшены по умолчанию",
        "Selected output directory: {path}": "Выбрана папка вывода: {path}",
        "Regenerated output directory: {path}": "Сгенерирована выходная папка: {path}",
        "Saved {count} profiles to {file}": "Сохранено {count} профилей в {file}",
        "Loaded {count} profiles from {file}": "Загружено {count} профилей из {file}",
        "Starting compression process...": "Запуск процесса сжатия...",
        "Stopping compression...": "Остановка сжатия...",
        "Waiting for compression to stop; start button disabled": "Ожидание остановки сжатия; кнопка отключена",
        "Error: {error}": "Ошибка: {error}",
        "Opened comparison window": "Открыто окно сравнения",
        "Error opening comparison: {error}": "Ошибка открытия окна сравнения: {error}",
        "Successfully compressed: {name} with profile {profile}": "Успешно сжат: {name} с профилем {profile}",
        "Failed to compress: {name}": "Не удалось сжать: {name}",
        "Compression aborted by user": "Сжатие прервано пользователем",
        "Copied file: {name}": "Скопирован файл: {name}",
        "Skipped unsupported file: {name}": "Пропущен неподдерживаемый файл: {name}",
        "Generating image pairs...": "Создание пар изображений...",
        "Saving compression settings...": "Сохранение настроек сжатия...",
        "Compression complete: {compressed}/{total} files processed": (
            "Сжатие завершено: {compressed}/{total} файлов обработано"
        ),
        "Processed {current}/{total} files": "Обработано {current}/{total} файлов",
        "Processed {current}/{total} files (≈ {remaining} left)": (
            "Обработано {current}/{total} файлов (≈ {remaining} осталось)"
        ),
        "Loading Previews": "Загрузка превью",
        "Generating previews: {current}/{total}": "Создание превью: {current}/{total}",
        "Image Comparison Viewer": "Просмотр сравнения изображений",
        "Load Config": "Загрузить конфиг",
        "Load Image Pair": "Загрузить пару изображений",
        "Load Directories": "Загрузить папки",
        "Reset View": "Сбросить вид",
        "Compare Stats": "Сравнить статистику",
        "No images loaded": "Изображения не загружены",
        "Select First Image": "Выберите первое изображение",
        "Select Second Image": "Выберите второе изображение",
        "Select Config": "Выберите конфиг",
        "Select First Directory": "Выберите первую папку",
        "Select Second Directory": "Выберите вторую папку",
        "Showing: {name} ({index}/{total})": "Показ: {name} ({index}/{total})",
        "Loaded {count} image pairs": "Загружено {count} пар изображений",
        "Compression Statistics": "Статистика сжатия",
        "Metric": "Метрика",
        "Directory 1": "Папка 1",
        "Directory 2": "Папка 2",
        "Difference": "Разница",
        "Different": "Различаются",
        "N/A": "Н/Д",
        "Output Format": "Формат вывода",
        "Quality": "Качество",
        "Progressive": "Прогрессивный",
        "Subsampling": "Субдискретизация",
        "Optimize": "Оптимизация",
        "Smooth": "Сглаживание",
        "Keep RGB": "Сохранить RGB",
        "Lossless": "Без потерь",
        "Method": "Метод",
        "Alpha Quality": "Качество альфа",
        "Exact": "Точный",
        "Speed": "Скорость",
        "Codec": "Кодек",
        "Range": "Диапазон",
        "Qmin": "Qmin",
        "Qmax": "Qmax",
        "Autotiling": "Авторазбиение",
        "Tile Rows": "Ряды тайлов",
        "Tile Cols": "Колонки тайлов",
        "Input Size": "Входной размер",
        "Output Size": "Выходной размер",
        "Profile: {name}": "Профиль: {name}",
        "Original photo": "Оригинальное фото",
        "Basic settings:": "Базовые настройки:",
        "Advanced settings:": "Расширенные настройки:",
        "Conditions:": "Условия:",
        "Space Saved": "Экономия места",
        "Compression Ratio": "Коэффициент сжатия",
        "Total Files": "Всего файлов",
        "Files Compressed": "Файлов сжато",
        "Failed Files": "Ошибок",
        "Conversion Time": "Время преобразования",
        "Name": "Имя",
        "Compression Settings": "Настройки сжатия",
        "Compression Metrics": "Метрики сжатия",
        "Max largest side": "Макс. большая сторона",
        "Max smallest side": "Макс. меньшая сторона",
        "Format": "Формат",
        "Preserve folder structure": "Сохранить структуру папок",
        "Copy unsupported files": "Копировать неподдерживаемые файлы",
        "Copy unsupported files to separate folder": "Копировать неподдерживаемые файлы в отдельную папку",
        "Select Unsupported Folder": "Выбрать папку неподдерживаемых",
        "Regenerated unsupported folder: {path}": "Сгенерирована папка неподдерживаемых: {path}",
        "Unsupported files folder": "Папка неподдерживаемых файлов",
        "Selected unsupported folder: {path}": "Выбрана папка неподдерживаемых: {path}",
        "No unsupported directory selected": "Папка неподдерживаемых не выбрана",
        "not_proceed": "не_обработано",
        "Advanced Settings": "Расширенные настройки",
        "Exact alpha": "Точная альфа",
        "Smallest side": "Меньшая сторона",
        "Largest side": "Большая сторона",
        "Pixels": "Пиксели",
        "Aspect ratio": "Соотношение сторон",
        "Orientation": "Ориентация",
        "Any": "Любая",
        "Landscape": "Альбомная",
        "Portrait": "Портретная",
        "Square": "Квадратная",
        "Input formats": "Входные форматы",
        "Transparency": "Прозрачность",
        "Requires": "Требуется",
        "No": "Нет",
        "File size": "Размер файла",
        "Examples: 500KB, 2MB, 1.5GB": "Примеры: 500KB, 2MB, 1.5GB",
        "Required EXIF (k=v,...)": "Требуемый EXIF (k=v,...)",
        "Conditions": "Условия",
        "Conditions (default profile - always used)": "Условия (профиль по умолчанию — используется всегда)",
    }
}


def _detect_system_language() -> str:
    """Return a language code based on system locale."""
    lang, _ = locale.getdefaultlocale()
    if lang:
        code = lang.split("_")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


_current_language = _detect_system_language()


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
