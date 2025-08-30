import json
from pathlib import Path

from PIL import Image

from service.compression_profiles import CompressionProfile
from service.image_compression import (
    ImageCompressor,
    create_image_pairs,
    save_compression_settings,
)


def test_profile_saved_in_settings(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    Image.new("RGB", (100, 100), color="red").save(input_dir / "img.jpg")

    compressor = ImageCompressor()
    default_profile = CompressionProfile(name="Default")
    compressor.process_directory(input_dir, output_dir, [default_profile])

    raw_pairs = create_image_pairs(output_dir, input_dir)
    profile_map = compressor.last_profile_map
    image_pairs = [(orig, comp, profile_map.get(comp, "Raw")) for orig, comp in raw_pairs]
    save_compression_settings(output_dir, {}, image_pairs, {}, profiles=[default_profile])

    settings_file = output_dir / "compression_settings.json"
    with settings_file.open() as f:
        data = json.load(f)
    assert data["image_pairs"][0]["profile"] == "Default"
    assert data["profiles"][0]["name"] == "Default"
