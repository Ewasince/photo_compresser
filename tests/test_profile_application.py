from pathlib import Path

from PIL import Image

from service.compression_profiles import CompressionProfile, NumericCondition, ProfileConditions
from service.image_compression import ImageCompressor


def test_process_directory_uses_profiles(tmp_path: Path) -> None:
    small_img = tmp_path / "small.jpg"
    large_img = tmp_path / "large.jpg"
    Image.new("RGB", (500, 500), color="red").save(small_img)
    Image.new("RGB", (2000, 2000), color="blue").save(large_img)

    default = CompressionProfile(name="Default")
    small_profile = CompressionProfile(
        name="Small",
        output_format="WEBP",
        conditions=ProfileConditions(
            smallest_side=NumericCondition("<", 1000),
        ),
    )
    profiles = [default, small_profile]

    compressor = ImageCompressor()
    output_dir = tmp_path / "out"
    compressor.process_directory(tmp_path, output_dir, profiles)

    assert (output_dir / "small.webp").exists()
    assert (output_dir / "large.jpg").exists()
