from pathlib import Path

from PIL import Image

from service.compression_profiles import (
    CompressionProfile,
    NumericCondition,
    ProfileConditions,
    load_profiles,
    save_profiles,
    select_profile,
)


def test_profile_save_load_and_selection(tmp_path: Path) -> None:
    profiles = [
        CompressionProfile(name="default", quality=75),
        CompressionProfile(
            name="small",
            quality=90,
            conditions=ProfileConditions(smallest_side=NumericCondition(op="<=", value=1080)),
        ),
    ]
    file_path = tmp_path / "profiles.json"
    save_profiles(profiles, file_path)
    loaded = load_profiles(file_path)

    assert [p.name for p in loaded] == ["default", "small"]

    small_image = tmp_path / "small.jpg"
    Image.new("RGB", (800, 600)).save(small_image)
    profile = select_profile(small_image, loaded)
    assert profile is not None
    assert profile.name == "small"

    large_image = tmp_path / "large.jpg"
    Image.new("RGB", (2000, 1500)).save(large_image)
    profile = select_profile(large_image, loaded)
    assert profile is not None
    assert profile.name == "default"


def test_profile_orientation_and_format(tmp_path: Path) -> None:
    profiles = [
        CompressionProfile(name="default"),
        CompressionProfile(
            name="portrait_png",
            conditions=ProfileConditions(
                orientation="portrait",
                input_formats=["PNG"],
                requires_transparency=True,
            ),
        ),
    ]

    portrait = tmp_path / "portrait.png"
    Image.new("RGBA", (600, 800)).save(portrait)

    profile = select_profile(portrait, profiles)
    assert profile is not None
    assert profile.name == "portrait_png"

    landscape = tmp_path / "land.jpg"
    Image.new("RGB", (800, 600)).save(landscape)
    profile = select_profile(landscape, profiles)
    assert profile is not None
    assert profile.name == "default"


def test_profile_priority_interface() -> None:
    profiles = [
        CompressionProfile(name="default"),
        CompressionProfile(
            name="middle",
            conditions=ProfileConditions(smallest_side=NumericCondition(op=">=", value=500)),
        ),
        CompressionProfile(
            name="bottom",
            conditions=ProfileConditions(smallest_side=NumericCondition(op=">=", value=500)),
        ),
    ]
    img = Image.new("RGB", (600, 600))
    profile = select_profile(img, profiles)
    assert profile is not None
    assert profile.name == "bottom"


def test_profile_priority_loaded(tmp_path: Path) -> None:
    profiles = [
        CompressionProfile(name="default"),
        CompressionProfile(
            name="middle",
            conditions=ProfileConditions(smallest_side=NumericCondition(op=">=", value=500)),
        ),
        CompressionProfile(
            name="bottom",
            conditions=ProfileConditions(smallest_side=NumericCondition(op=">=", value=500)),
        ),
    ]
    file_path = tmp_path / "profiles.json"
    save_profiles(profiles, file_path)
    loaded = load_profiles(file_path)
    img = Image.new("RGB", (600, 600))
    profile = select_profile(img, loaded)
    assert profile is not None
    assert profile.name == "bottom"
