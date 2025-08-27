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
    
    def __init__(self, quality: int = 85, max_largest_side: int = 1920, max_smallest_side: int = 1080, preserve_structure: bool = True):
        """
        Initialize the image compressor.
        
        Args:
            quality: JPEG quality (1-100)
            max_largest_side: Maximum size of the largest side in pixels
            max_smallest_side: Maximum size of the smallest side in pixels
            preserve_structure: Whether to preserve folder structure
        """
        self.quality = max(1, min(100, quality))
        self.max_largest_side = max_largest_side
        self.max_smallest_side = max_smallest_side
        self.preserve_structure = preserve_structure
        
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
                
                # Save with appropriate settings
                if output_path.suffix.lower() in {'.jpg', '.jpeg'}:
                    img.save(output_path, 'JPEG', quality=self.quality, optimize=True)
                elif output_path.suffix.lower() == '.png':
                    img.save(output_path, 'PNG', optimize=True)
                elif output_path.suffix.lower() == '.webp':
                    img.save(output_path, 'WEBP', quality=self.quality)
                else:
                    img.save(output_path)
                
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
                if file_path.suffix.lower() in self.supported_formats:
                    total_files += 1
                    
                    # Determine output file path
                    if self.preserve_structure:
                        output_file = output_root / file
                    else:
                        # Create unique filename to avoid conflicts
                        base_name = file_path.stem
                        extension = file_path.suffix
                        counter = 1
                        output_file = output_root / f"{base_name}{extension}"
                        
                        # If file exists, add counter
                        while output_file.exists():
                            output_file = output_root / f"{base_name}_{counter}{extension}"
                            counter += 1
                    
                    # Check if compression is needed
                    if self.should_compress_image(file_path):
                        if self.compress_image(file_path, output_file):
                            compressed_files += 1
                            compressed_paths.append(output_file)
                    else:
                        # Copy file without compression
                        shutil.copy2(file_path, output_file)
                        logger.info(f"Copied (no compression needed): {file_path.name}")
                else:
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


def create_image_pairs(compressed_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Create pairs of images for comparison (original vs compressed).
    
    Args:
        compressed_dir: Directory containing compressed images
        
    Returns:
        List of tuples (original_path, compressed_path)
    """
    image_pairs = []
    
    # Find all image files in the compressed directory
    image_files = []
    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
        image_files.extend(compressed_dir.rglob(f'*{ext}'))
        image_files.extend(compressed_dir.rglob(f'*{ext.upper()}'))
    
    # Sort files for consistent pairing
    image_files.sort()
    
    # Create pairs (each image with the next one)
    for i in range(0, len(image_files) - 1, 2):
        image_pairs.append((image_files[i], image_files[i + 1]))
    
    # If odd number of files, add the last one with itself
    if len(image_files) % 2 == 1:
        image_pairs.append((image_files[-1], image_files[-1]))
    
    return image_pairs
