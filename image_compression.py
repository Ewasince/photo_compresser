#!/usr/bin/env python3
"""
Image Compression Module
Handles image compression with configurable quality and size parameters.
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImageCompressor:
    """Handles image compression with various parameters."""
    
    def __init__(self, quality: int = 85, max_largest_side: int = 1920, max_smallest_side: int = 1080, 
                 preserve_structure: bool = True, output_format: str = 'JPEG'):
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
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def should_compress_image(self, image_path: Path) -> bool:
        """Check if the image should be compressed based on its current size."""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                largest_side = max(width, height)
                smallest_side = min(width, height)
                
                # Check if image needs resizing
                needs_resize = (largest_side > self.max_largest_side or 
                              smallest_side > self.max_smallest_side)
                
                # Check if image needs quality compression (for JPEG)
                needs_quality_compression = False
                if image_path.suffix.lower() in {'.jpg', '.jpeg'}:
                    # For JPEG, we'll always recompress to ensure quality setting
                    needs_quality_compression = True
                
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
                # Convert to RGB if necessary (for JPEG output)
                if output_path.suffix.lower() in {'.jpg', '.jpeg'} and img.mode != 'RGB':
                    img = img.convert('RGB')
                
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
                
                # Resize if necessary
                if new_width != width or new_height != height:
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save with appropriate settings based on output format
                if self.output_format == 'JPEG':
                    img.save(output_path, 'JPEG', quality=self.quality, optimize=True)
                elif self.output_format == 'WEBP':
                    img.save(output_path, 'WEBP', quality=self.quality)
                elif self.output_format == 'AVIF':
                    img.save(output_path, 'AVIF', quality=self.quality)
                else:
                    # Fallback to JPEG
                    img.save(output_path, 'JPEG', quality=self.quality, optimize=True)
                
                logger.info(f"Compressed: {input_path.name} -> {output_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to compress {input_path}: {e}")
            return False
    
    def process_directory(self, input_dir: Path, output_dir: Path) -> Tuple[int, int, List[Path]]:
        """
        Process all images in a directory recursively.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            
        Returns:
            Tuple of (total_files, compressed_files, compressed_paths)
        """
        total_files = 0
        compressed_files = 0
        compressed_paths = []
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Walk through all files recursively
        for root, dirs, files in os.walk(input_dir):
            # Calculate relative path based on preserve_structure setting
            if self.preserve_structure:
                rel_path = Path(root).relative_to(input_dir)
                output_root = output_dir / rel_path
                # Create corresponding output directory
                output_root.mkdir(parents=True, exist_ok=True)
            else:
                # Put all files in the root output directory
                output_root = output_dir
            
            # Process files in current directory
            for file in files:
                file_path = Path(root) / file
                
                # Check if it's an image file
                if file_path.suffix.lower() not in self.supported_formats:
                    # Copy non-image files
                    if self.preserve_structure:
                        output_file = output_root / file
                    else:
                        # Create unique filename for non-image files too
                        base_name = file_path.stem
                        extension = file_path.suffix
                        counter = 1
                        output_file = output_root / f"{base_name}{extension}"

                        while output_file.exists():
                            output_file = output_root / f"{base_name}_{counter}{extension}"
                            counter += 1

                    shutil.copy2(file_path, output_file)
                    logger.info(f"Copied (non-image): {file_path.name}")
                    continue

                total_files += 1

                base_name = file_path.stem
                new_extension = self._get_extension_according_format()
                output_file = output_root / f"{base_name}{new_extension}"

                # Determine output file path with correct extension
                if not self.preserve_structure:
                    # Create unique filename to avoid conflicts
                    counter = 1
                    # If file exists, add counter
                    while output_file.exists():
                        output_file = output_root / f"{base_name}_{counter}{new_extension}"
                        counter += 1

                if self.compress_image(file_path, output_file):
                    compressed_files += 1
                    compressed_paths.append(output_file)
        
        return total_files, compressed_files, compressed_paths
    
    def get_compression_stats(self, input_dir: Path, output_dir: Path) -> dict:
        """
        Get statistics about the compression process.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            
        Returns:
            Dictionary with compression statistics
        """
        input_size = sum(f.stat().st_size for f in input_dir.rglob('*') if f.is_file())
        output_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        
        compression_ratio = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
        
        return {
            'input_size_mb': input_size / (1024 * 1024),
            'output_size_mb': output_size / (1024 * 1024),
            'compression_ratio_percent': compression_ratio,
            'space_saved_mb': (input_size - output_size) / (1024 * 1024)
        }


    def _get_extension_according_format(self) -> str:
        if self.output_format == 'WEBP':
            return '.webp'
        if self.output_format == 'AVIF':
            return '.avif'
        return '.jpg'  # Default fallback


def create_image_pairs(compressed_dir: Path, original_dir: Path = None) -> List[Tuple[Path, Path]]:
    """
    Create pairs of images for comparison (original vs compressed).
    
    Args:
        compressed_dir: Directory containing compressed images
        original_dir: Directory containing original images (optional)
        
    Returns:
        List of tuples (original_path, compressed_path)
    """
    logger.info(f"Creating image pairs from compressed_dir: {compressed_dir}")
    if original_dir:
        logger.info(f"Using original_dir: {original_dir}")
    else:
        logger.info("No original_dir provided, will use compressed files only")
    
    image_pairs = []
    
    # Find all image files in the compressed directory
    compressed_files = []
    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
        compressed_files.extend(compressed_dir.rglob(f'*{ext}'))
        compressed_files.extend(compressed_dir.rglob(f'*{ext.upper()}'))
    
    # Sort files for consistent pairing
    compressed_files.sort()
    logger.info(f"Found {len(compressed_files)} compressed image files")
    
    # If original directory is provided, create original vs compressed pairs
    if original_dir and original_dir.exists():
        for compressed_file in compressed_files:
            # Calculate relative path from compressed directory
            rel_path = compressed_file.relative_to(compressed_dir)
            
            # Try to find corresponding original file using the provided original_dir
            original_file = original_dir / rel_path
            
            # If the compressed file is in the root of compressed directory (no subdirectories),
            # try to find the original file in the original directory recursively
            if not rel_path.parent.name and not original_file.exists():
                # Search for the file in the original directory recursively
                logger.info(f"Searching for {compressed_file.name} recursively in {original_dir}")
                for original_file_candidate in original_dir.rglob(compressed_file.name):
                    if original_file_candidate.is_file():
                        original_file = original_file_candidate
                        logger.info(f"Found original file at: {original_file}")
                        break
            
            if original_file.exists():
                image_pairs.append((original_file, compressed_file))
                logger.info(f"Found pair: {original_file.name} vs {compressed_file.name}")
            else:
                # If original not found, use compressed file for both
                image_pairs.append((compressed_file, compressed_file))
                logger.warning(f"Original not found for {compressed_file.name}, using same file for both")
    else:
        # Fallback: create pairs from compressed files only
        for i in range(0, len(compressed_files) - 1, 2):
            image_pairs.append((compressed_files[i], compressed_files[i + 1]))
        
        # If odd number of files, add the last one with itself
        if len(compressed_files) % 2 == 1:
            image_pairs.append((compressed_files[-1], compressed_files[-1]))
    
    logger.info(f"Created {len(image_pairs)} image pairs")
    return image_pairs


def save_compression_settings(output_dir: Path, compression_settings: dict, image_pairs: List[Tuple[Path, Path]]):
    """
    Save compression settings and image pairs to a JSON file.
    
    Args:
        output_dir: Directory where to save the settings file
        compression_settings: Dictionary with compression parameters
        image_pairs: List of image pairs for comparison
    """
    import json
    from datetime import datetime
    
    settings_data = {
        'compression_settings': compression_settings,
        'compression_date': datetime.now().isoformat(),
        'image_pairs': [
            {
                'original': str(original_path),
                'compressed': str(compressed_path),
                'original_name': original_path.name,
                'compressed_name': compressed_path.name
            }
            for original_path, compressed_path in image_pairs
        ],
        'total_pairs': len(image_pairs)
    }
    
    settings_file = output_dir / 'compression_settings.json'
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Compression settings saved to: {settings_file}")
        return settings_file
    except Exception as e:
        logger.error(f"Failed to save compression settings: {e}")
        return None


def load_compression_settings(settings_file: Path) -> dict:
    """
    Load compression settings from a JSON file.
    
    Args:
        settings_file: Path to the settings file
        
    Returns:
        Dictionary with settings data
    """
    import json
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        logger.info(f"Compression settings loaded from: {settings_file}")
        return settings_data
    except Exception as e:
        logger.error(f"Failed to load compression settings: {e}")
        return None
