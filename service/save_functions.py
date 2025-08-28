from pathlib import Path
from typing import Any

import pillow_avif  # noqa: F401
from PIL import Image


# ВСПОМОГАТЕЛЬНОЕ: аккуратно убирать альфу для JPEG
def _flatten_for_jpeg(im: Image.Image, background: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    JPEG не поддерживает альфа-канал. Эта функция безопасно «сплющит» RGBA к RGB.
    """
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        bg = Image.new("RGB", im.size, background)
        return Image.alpha_composite(bg.convert("RGBA"), im.convert("RGBA")).convert("RGB")
    return im.convert("RGB") if im.mode not in ("RGB", "L") else im


# JPEG
def save_jpeg(
    im: Image.Image,
    dst: Path,
    *,
    quality: int = 75,  # [БАЗОВЫЙ] 0–100 (дефолт Pillow: 75). Ниже → сильнее сжатие
    subsampling: int | str = -1,
    # [ПРО] -1 (авто/как решит кодек), 2="4:2:0", 1="4:2:2", 0="4:4:4", либо строкой "4:2:0" и т.п.
    progressive: bool = False,  # [БАЗОВЫЙ] False/True. Прогрессивная запись, иногда минус кб
    optimize: bool = False,  # [ПРО] False/True. Оптимизация Хаффмана → чуть меньше файл
    qtables: dict | None = None,  # [ПРО] Кастомные квант-таблицы (обычно не трогаем)
    smooth: int = 0,  # [ПРО] 0–100. Лёгкое сглаживание (меньше шум → лучше сжимается)
    keep_rgb: bool = False,  # [ПРО] Сохранить в RGB (без YCbCr). Может ↑размер, но убирает переход
) -> None:
    """
    Сохраняет как JPEG, прокидывая только параметры, влияющие на качество/сжатие.
    Дефолты соответствуют поведению Pillow, если параметры не указать.
    """
    im = _flatten_for_jpeg(im)

    # Метаданные (влияют только на итоговый размер, не на кодирование пикселей):
    # По идее можно без изменений передать exif, icc и xmp оригинального изображения.
    exif = im.info.get("exif")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    icc_profile = im.info.get("icc_profile")
    xmp = im.info.get("xmp")

    # Собираем kwargs только из «влияющих» параметров
    kwargs: dict[str, Any] = {
        "quality": quality,  # 0–100 (дефолт 75)
        "subsampling": subsampling,  # -1, 0/1/2 или "4:4:4" и т.п.
        "progressive": progressive,  # False по умолчанию
        "optimize": optimize,  # False по умолчанию
        "qtables": qtables,  # None по умолчанию
        "smooth": smooth,  # 0 по умолчанию
        "keep_rgb": keep_rgb,  # False по умолчанию
    }

    # Сохраняем метаданные источника без изменений
    if exif:
        kwargs["exif"] = exif
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    if xmp:
        kwargs["xmp"] = xmp

    im.save(dst, format="JPEG", **{k: v for k, v in kwargs.items() if v is not None})


# WebP
def save_webp(
    im: Image.Image,
    dst: str | Path,
    *,
    lossless: bool = False,  # [БАЗОВЫЙ] False/True. Влияет радикально на метод сжатия
    quality: int = 80,  # [БАЗОВЫЙ] 0–100. Для lossless — «усилие» (0–100), дефолт 80
    method: int = 4,  # [ПРО] 0–6. Медленнее → лучше сжатие при том же качестве (дефолт 4)
    alpha_quality: int = 100,  # [ПРО] 0–100. Качество альфы в lossy; дефолт 100
    exact: bool = False,  # [ПРО] False/True. Сохранять RGB под прозрачностью (↑размер, ↑качество)
) -> None:
    """
    Сохраняет как WebP. Прокидывает только влияющие на качество/сжатие параметры.
    Дефолты соответствуют Pillow (lossy q=80/method=4; метаданные не пишутся).
    """

    # Метаданные: по умолчанию Pillow/WebP их НЕ сохраняет → передадим исходные
    exif = im.info.get("exif")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    if exif and exif.startswith(b"Exif\x00\x00"):
        exif = exif[6:]
    icc_profile = im.info.get("icc_profile")
    xmp = im.info.get("xmp")

    kwargs: dict[str, Any] = {
        "lossless": lossless,  # False
        "quality": quality,  # 0–100 (80)
        "method": method,  # 0–6 (4)
        "alpha_quality": alpha_quality,  # 0–100 (100)
        "exact": exact,  # False
    }

    # Сохраняем метаданные источника без изменений
    if exif:
        kwargs["exif"] = exif
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    if xmp:
        kwargs["xmp"] = xmp

    dst_path = Path(dst)

    im.save(dst_path, format="WEBP", **kwargs)


# ────────────────────────────────────────────────────────────────────────────────
# AVIF (через pillow-avif-plugin; в официальном Pillow — аналогично по ключам)
def save_avif(
    im: Image.Image,
    dst: str | Path,
    *,
    quality: int = 75,  # [БАЗОВЫЙ] 0–100 (дефолт 75). Ниже → сильнее сжатие
    subsampling: str = "4:2:0",  # [БАЗОВЫЙ] "4:2:0" (дефолт) | "4:2:2" | "4:4:4" | "4:0:0"
    speed: int = 6,  # [ПРО] 0–10. 0 — медленнее/лучше RD, 10 — быстрее/хуже (дефолт 6)
    codec: str = "auto",  # [ПРО] "auto"(деф.)|"aom"|"rav1e"|"svt" (если доступны)
    range_: str = "full",  # [ПРО] "full"(деф.)|"limited" (тональный диапазон)
    qmin: int = -1,  # [ПРО] -1 (деф.) или 0–63. Мин. квантайзер (жёсткая нижняя граница)
    qmax: int = -1,  # [ПРО] -1 (деф.) или 0–63. Макс. квантайзер (верхняя граница)
    autotiling: bool = True,  # [ПРО] True (деф.) | False. Автотайлинг для декод-скорости
    tile_rows_log2: int = 0,  # [ПРО] 0..6 (лог2). Явные тайлы по строкам (если autotiling=False)
    tile_cols_log2: int = 0,  # [ПРО] 0..6 (лог2). Явные тайлы по столбцам (если autotiling=False)
) -> None:
    """
    Сохраняет как AVIF. Прокидывает только влияющие параметры (качество, сабсэмплинг,
    скорость/кодек, кванты, тайлинг). Дефолты соответствуют текущему поведению плагина.
    """

    # Метаданные: возьмём из исходного изображения (поведение плагина по умолчанию)
    exif = im.info.get("exif")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    icc_profile = im.info.get("icc_profile")
    xmp = im.info.get("xmp")

    kwargs: dict[str, Any] = {
        "quality": quality,  # 0–100 (75)
        "subsampling": subsampling,  # "4:2:0" (деф.), "4:2:2", "4:4:4", "4:0:0"
        "speed": speed,  # 0–10 (6)
        "codec": codec,  # "auto"
        "range": range_,  # "full"
        "qmin": qmin,  # -1
        "qmax": qmax,  # -1
    }

    # Тайлинг: по умолчанию autotiling=True (соответствует поведению плагина)
    if autotiling:
        kwargs["autotiling"] = True
    else:
        kwargs["tile_rows"] = tile_rows_log2
        kwargs["tile_cols"] = tile_cols_log2

    # Сохраняем метаданные источника без изменений
    if exif:
        kwargs["exif"] = exif
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    if xmp:
        kwargs["xmp"] = xmp

    dst_path = Path(dst)

    im.save(dst_path, format="AVIF", **kwargs)
