#!/usr/bin/env python3
"""
Image Compression Module
Handles image compression with configurable quality and size parameters.
"""

import logging
from pathlib import Path
from typing import Any

from PIL import Image
from pillow_heif import register_heif_opener

from service.constants import SUPPORTED_EXTENSIONS
from service.save_functions import save_avif, save_jpeg, save_webp

register_heif_opener()


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ImageCompressor:
    """Handles image compression with various parameters."""

    def __init__(
        self,
        quality: int = 85,
        max_largest_side: int = 1920,
        max_smallest_side: int = 1080,
        preserve_structure: bool = True,
        output_format: str = "JPEG",
    ):
        """
        Initialize the image compressor.

        Args:
            quality: JPEG/WebP/AVIF quality (1-100)
            max_largest_side: Maximum size of the largest side in pixels
            max_smallest_side: Maximum size of the smallest side in pixels
            preserve_structure: Whether to preserve folder structure
            output_format: Output format ('JPEG', 'WebP', 'AVIF')
        """
        self.quality = max(1, min(100, quality))
        self.max_largest_side = max_largest_side
        self.max_smallest_side = max_smallest_side
        self.preserve_structure = preserve_structure
        self.output_format = output_format.upper()

        # Store advanced parameters for each format
        self.jpeg_params: dict[str, Any] = {}
        self.webp_params: dict[str, Any] = {}
        self.avif_params: dict[str, Any] = {}

    def set_jpeg_parameters(self, **kwargs: Any) -> None:
        """Set JPEG-specific compression parameters."""
        self.jpeg_params = kwargs

    def set_webp_parameters(self, **kwargs: Any) -> None:
        """Set WebP-specific compression parameters."""
        self.webp_params = kwargs

    def set_avif_parameters(self, **kwargs: Any) -> None:
        """Set AVIF-specific compression parameters."""
        self.avif_params = kwargs

    def should_compress_image(self, image_path: Path) -> bool:
        """Check if the image should be compressed based on its current size."""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                largest_side = max(width, height)
                smallest_side = min(width, height)

                # Check if image needs resizing
                needs_resize = largest_side > self.max_largest_side or smallest_side > self.max_smallest_side

                # Check if image needs quality compression (for all formats)
                needs_quality_compression = True  # Always recompress to ensure quality settings

                return needs_resize or needs_quality_compression

        except Exception as e:
            logger.warning(f"Could not analyze image {image_path}: {e}")
            return False

    def compress_image(self, input_path: Path, output_path: Path) -> bool:
        """
        Compress a single image according to the specified parameters.

        Args:
            input_path: Path to the input image
            output_path: Path where the compressed image should be saved

        Returns:
            True if compression was successful, False otherwise
        """
        try:
            with Image.open(input_path) as img:
                # Calculate new dimensions
                width, height = img.size
                largest_side = max(width, height)
                smallest_side = min(width, height)

                # Determine if resizing is needed
                new_width, new_height = width, height

                if largest_side > self.max_largest_side:
                    # Scale down proportionally
                    scale_factor = self.max_largest_side / largest_side
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)

                if smallest_side > self.max_smallest_side:
                    # Check if we need to scale down further
                    current_smallest = min(new_width, new_height)
                    if current_smallest > self.max_smallest_side:
                        scale_factor = self.max_smallest_side / current_smallest
                        new_width = int(new_width * scale_factor)
                        new_height = int(new_height * scale_factor)

                # Resize image if needed
                if new_width != width or new_height != height:
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.info(f"Resized {input_path.name} from {width}x{height} to {new_width}x{new_height}")

                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Use custom save functions if available
                if self.output_format == "JPEG":
                    return self._save_jpeg_custom(img, input_path, output_path)
                if self.output_format == "WEBP":
                    return self._save_webp_custom(img, input_path, output_path)
                if self.output_format == "AVIF":
                    return self._save_avif_custom(img, input_path, output_path)
                # Fallback to basic Pillow saving
                return self._save_basic(img, output_path)

        except Exception as e:
            logger.exception(f"Error compressing {input_path}: {e}")
            return False

    def _save_jpeg_custom(self, img: Image.Image, input_path: Path, output_path: Path) -> bool:
        """Save image using custom JPEG save function."""
        try:
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Prepare parameters
            params = {
                "quality": self.quality,
                "progressive": self.jpeg_params.get("progressive", False),
                "subsampling": self.jpeg_params.get("subsampling", -1),
                "optimize": self.jpeg_params.get("optimize", False),
                "smooth": self.jpeg_params.get("smooth", 0),
                "keep_rgb": self.jpeg_params.get("keep_rgb", False),
            }

            # Call custom save function
            save_jpeg(img, input_path, output_path, **params)
            logger.info(f"Compressed JPEG: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error in custom JPEG save: {e}")
            return False

    def _save_webp_custom(self, img: Image.Image, input_path: Path, output_path: Path) -> bool:
        """Save image using custom WebP save function."""
        try:
            # Prepare parameters
            params = {
                "lossless": self.webp_params.get("lossless", False),
                "quality": self.quality,
                "method": self.webp_params.get("method", 4),
                "alpha_quality": self.webp_params.get("alpha_quality", 100),
                "exact": self.webp_params.get("exact", False),
            }

            # Call custom save function
            save_webp(img, input_path, output_path, **params)
            logger.info(f"Compressed WebP: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error in custom WebP save: {e}")
            return False

    def _save_avif_custom(self, img: Image.Image, input_path: Path, output_path: Path) -> bool:
        """Save image using custom AVIF save function."""
        try:
            # Prepare parameters
            params = {
                "quality": self.quality,
                "subsampling": self.avif_params.get("subsampling", "4:2:0"),
                "speed": self.avif_params.get("speed", 6),
                "codec": self.avif_params.get("codec", "auto"),
                "range_": self.avif_params.get("range", "full"),
                "qmin": self.avif_params.get("qmin", -1),
                "qmax": self.avif_params.get("qmax", -1),
                "autotiling": self.avif_params.get("autotiling", True),
                "tile_rows_log2": self.avif_params.get("tile_rows", 0),
                "tile_cols_log2": self.avif_params.get("tile_cols", 0),
            }

            # Call custom save function
            # Note: range_ is renamed to range in the function call
            avif_params = params.copy()
            save_avif(img, input_path, output_path, **avif_params)
            logger.info(f"Compressed AVIF: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error in custom AVIF save: {e}")
            return False

    def _save_basic(self, img: Image.Image, output_path: Path) -> bool:
        """Fallback to basic Pillow saving."""
        try:
            # Convert to RGB if necessary (for JPEG output)
            if output_path.suffix.lower() in {".jpg", ".jpeg"} and img.mode != "RGB":
                img = img.convert("RGB")

            # Save with appropriate settings based on output format
            if self.output_format == "JPEG":
                img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            elif self.output_format == "WEBP":
                img.save(output_path, "WEBP", quality=self.quality)
            elif self.output_format == "AVIF":
                # AVIF support requires pillow-avif-plugin
                try:
                    img.save(output_path, "AVIF", quality=self.quality)
                except Exception:
                    # Fallback to JPEG if AVIF fails
                    logger.warning(f"AVIF save failed, falling back to JPEG for {output_path.name}")
                    output_path = output_path.with_suffix(".jpg")
                    img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            else:
                # Fallback to JPEG
                img.save(output_path, "JPEG", quality=self.quality, optimize=True)

            logger.info(f"Compressed (basic): {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error in basic save: {e}")
            return False

    def _get_extension_according_format(self) -> str:
        """Get the correct file extension based on output format."""
        if self.output_format == "WEBP":
            return ".webp"
        if self.output_format == "AVIF":
            return ".avif"
        return ".jpg"  # Default fallback

    def process_directory(self, input_root: Path, output_root: Path) -> tuple[int, int, list[Path], list[Path]]:
        """
        Process a directory recursively, compressing all supported images.

        Args:
            input_root: Root input directory
            output_root: Root output directory

        Returns:
            Tuple of (total_files, compressed_files, compressed_paths, failed_files)
        """
        total_files = 0
        compressed_files = 0
        compressed_paths = []
        failed_files: list[Path] = []

        # Ensure output directory exists
        output_root.mkdir(parents=True, exist_ok=True)

        # Walk through input directory
        for file_path in input_root.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                total_files += 1

                # Determine output file path
                if self.preserve_structure:
                    # Change extension based on output format
                    base_name = file_path.stem
                    new_extension = self._get_extension_according_format()

                    output_file = output_root / f"{base_name}{new_extension}"
                else:
                    # Create unique filename to avoid conflicts
                    base_name = file_path.stem
                    new_extension = self._get_extension_according_format()

                    counter = 1
                    output_file = output_root / f"{base_name}{new_extension}"

                    # If file exists, add counter
                    while output_file.exists():
                        output_file = output_root / f"{base_name}_{counter}{new_extension}"
                        counter += 1

                # Compress the image
                if self.compress_image(file_path, output_file):
                    compressed_files += 1
                    compressed_paths.append(output_file)
                    logger.info(f"Successfully compressed: {file_path.name}")
                else:
                    logger.warning(f"Failed to compress: {file_path.name}")
                    failed_files.append(file_path)

        logger.info(f"Compression complete: {compressed_files}/{total_files} files processed")
        return total_files, compressed_files, compressed_paths, failed_files

    def get_compression_stats(
        self, input_dir: Path, output_dir: Path, failed_files: list[Path] | None = None
    ) -> dict[str, Any]:
        """Get compression statistics."""
        try:
            failed_set = {f.resolve() for f in failed_files or []}

            input_files = [
                f
                for f in input_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS and f.resolve() not in failed_set
            ]
            output_files = [f for f in output_dir.rglob("*") if f.is_file()]
            input_size = sum(f.stat().st_size for f in input_files)
            output_size = sum(f.stat().st_size for f in output_files)

            input_size_mb = input_size / (1024 * 1024)
            output_size_mb = output_size / (1024 * 1024)
            space_saved_mb = input_size_mb - output_size_mb
            compression_ratio_percent = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0

            return {
                "input_size_mb": input_size_mb,
                "output_size_mb": output_size_mb,
                "space_saved_mb": space_saved_mb,
                "compression_ratio_percent": compression_ratio_percent,
            }
        except Exception as e:
            logger.error(f"Error calculating compression stats: {e}")
            return {
                "input_size_mb": 0,
                "output_size_mb": 0,
                "space_saved_mb": 0,
                "compression_ratio_percent": 0,
            }


def create_image_pairs(compressed_dir: Path, original_dir: Path | None = None) -> list[tuple[Path, Path]]:
    """
    Create pairs of original and compressed images for comparison.

    Args:
        compressed_dir: Directory containing compressed images
        original_dir: Directory containing original images

    Returns:
        List of tuples (original_path, compressed_path)
    """
    if not original_dir:
        logger.warning("No original directory provided, cannot create image pairs")
        return []

    image_pairs = []
    logger.info(f"Creating image pairs from compressed dir: {compressed_dir}")
    logger.info(f"Original dir: {original_dir}")

    # Get all compressed image files
    compressed_files = []
    for file_path in compressed_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            compressed_files.append(file_path)

    logger.info(f"Found {len(compressed_files)} compressed files")

    for compressed_file in compressed_files:
        try:
            # Try to find corresponding original file
            if original_dir:
                # Calculate relative path from compressed file to compressed dir root
                rel_path = compressed_file.relative_to(compressed_dir)

                # Try to find original file at the same relative path
                original_file = original_dir / rel_path

                # If original file doesn't exist, try with different extensions
                if not original_file.exists():
                    # Try common image extensions
                    for ext in SUPPORTED_EXTENSIONS:
                        test_path = original_file.with_suffix(ext)
                        if test_path.exists():
                            original_file = test_path
                            break

                # If still not found and we're in flattened mode, search recursively
                if not original_file.exists() and compressed_file.parent == compressed_dir:
                    # Search recursively in original directory
                    for search_file in original_dir.rglob(compressed_file.stem + "*"):
                        if search_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                            original_file = search_file
                            break

                if original_file.exists():
                    image_pairs.append((original_file, compressed_file))
                    logger.info(f"Created pair: {original_file.name} <-> {compressed_file.name}")
                else:
                    logger.warning(f"Original file not found for: {compressed_file.name}")
                    # Fallback: use compressed file for both
                    image_pairs.append((compressed_file, compressed_file))
            else:
                # No original directory, use compressed file for both
                image_pairs.append((compressed_file, compressed_file))

        except Exception as e:
            logger.error(f"Error creating pair for {compressed_file}: {e}")
            continue

    logger.info(f"Created {len(image_pairs)} image pairs")
    return image_pairs


def save_compression_settings(
    output_dir: Path,
    compression_settings: dict[str, Any],
    image_pairs: list[tuple[Path, Path]],
    stats: dict[str, Any],
    failed_files: list[Path] | None = None,
) -> Path | None:
    """
    Save compression settings and image pairs to a JSON file.

    Args:
        output_dir: Directory where to save the settings file
        compression_settings: Dictionary with compression parameters
        image_pairs: List of image pairs for comparison
        failed_files: List of image paths that failed to compress
    """
    import json
    from datetime import datetime

    failed_files = failed_files or []

    settings_data = {
        "compression_settings": compression_settings,
        "compression_date": datetime.now().isoformat(),
        "image_pairs": [
            {
                "original": str(original_path),
                "compressed": str(compressed_path),
                "original_name": original_path.name,
                "compressed_name": compressed_path.name,
            }
            for original_path, compressed_path in image_pairs
        ],
        "total_pairs": len(image_pairs),
        "failed_files": [str(path) for path in failed_files],
        "stats": stats,
    }

    settings_file = output_dir / "compression_settings.json"
    try:
        with settings_file.open("w") as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Compression settings saved to: {settings_file}")
        return settings_file
    except Exception as e:
        logger.error(f"Failed to save compression settings: {e}")
        return None


def load_compression_settings(settings_file: Path) -> dict | None:
    """
    Load compression settings from a JSON file.

    Args:
        settings_file: Path to the settings file

    Returns:
        Dictionary with settings data or None if failed
    """
    import json

    try:
        with settings_file.open() as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load compression settings: {e}")
        return None
