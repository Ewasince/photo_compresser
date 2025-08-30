import json
from pathlib import Path

from PIL import Image

from service.image_compression import ImageCompressor, create_image_pairs, save_compression_settings
from service.translator import set_language, tr


def test_raw_profile_saved_untranslated(tmp_path: Path) -> None:
    set_language("ru")
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    Image.new("RGB", (10, 10), color="red").save(input_dir / "img.jpg")

    compressor = ImageCompressor()
    compressor.process_directory(input_dir, output_dir, [])

    raw_pairs = create_image_pairs(output_dir, input_dir)
    profile_map = compressor.last_profile_map
    condition_map = compressor.last_condition_map
    image_pairs = [(orig, comp, profile_map.get(comp, "Raw"), condition_map.get(comp, {})) for orig, comp in raw_pairs]
    save_compression_settings(output_dir, {}, image_pairs, {}, profiles=[])

    settings_file = output_dir / "compression_settings.json"
    with settings_file.open() as f:
        data = json.load(f)
    assert data["image_pairs"][0]["profile"] == "Raw"
    assert data["image_pairs"][0]["condition_results"] == {}
    assert tr("Raw") != "Raw"
    set_language("en")
