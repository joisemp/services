"""
Test script to verify image optimization utilities.
Run this with: docker exec -it sfs-services-dev-container python manage.py shell -c "exec(open('test_image_utils.py').read())"
Or run directly: docker exec -it sfs-services-dev-container python test_image_utils.py
"""

import os
import django

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from config.utils import generate_alphanumeric_filename, generate_unique_image_filename, compress_image
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
import sys

def test_alphanumeric_filename():
    """Test alphanumeric filename generation"""
    print("\n=== Testing Alphanumeric Filename Generation ===")
    
    # Test with default settings
    filename1 = generate_alphanumeric_filename()
    print(f"Default filename: {filename1}")
    assert len(filename1) == 21  # 16 chars + '.webp' (5 chars)
    assert filename1.endswith('.webp')
    
    # Test with custom length
    filename2 = generate_alphanumeric_filename(length=12, extension='jpg')
    print(f"Custom length filename: {filename2}")
    assert len(filename2) == 16  # 12 chars + '.jpg' (4 chars)
    
    # Test with original filename
    filename3 = generate_alphanumeric_filename(original_filename='photo.png')
    print(f"From original filename: {filename3}")
    assert filename3.endswith('.png')
    
    print("✅ Alphanumeric filename generation tests passed!")


def test_unique_filename_generation():
    """Test unique filename generation with storage check"""
    print("\n=== Testing Unique Filename Generation ===")
    
    # Generate multiple filenames and ensure they're unique
    filenames = set()
    for i in range(10):
        filename = generate_unique_image_filename(upload_path='test/', extension='webp')
        assert filename not in filenames, f"Duplicate filename generated: {filename}"
        filenames.add(filename)
        print(f"Generated unique filename {i+1}: {filename}")
    
    print(f"✅ Generated {len(filenames)} unique filenames successfully!")
    
    # Test that it checks storage for existing files
    test_path = 'public/test_images/'
    unique_name = generate_unique_image_filename(upload_path=test_path, extension='webp')
    print(f"Unique filename with storage check: {unique_name}")
    assert not default_storage.exists(f"{test_path}{unique_name}"), "Filename should not exist in storage"
    
    print("✅ Unique filename generation with storage check passed!")


def test_image_compression():
    """Test image compression and WebP conversion"""
    print("\n=== Testing Image Compression and WebP Conversion ===")
    
    # Create a test image
    img = Image.new('RGB', (2000, 2000), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    
    # Create an InMemoryUploadedFile
    test_image = InMemoryUploadedFile(
        buffer,
        'ImageField',
        'test_image.jpg',
        'image/jpeg',
        sys.getsizeof(buffer),
        None
    )
    
    print(f"Original image: {test_image.name}, Size: {img.size}")
    
    # Compress to WebP with upload path for uniqueness check
    compressed = compress_image(
        test_image, 
        max_width=1920, 
        max_height=1920, 
        quality=85, 
        format='WEBP',
        upload_path='public/issue_images/'
    )
    print(f"Compressed image: {compressed.name}")
    print(f"Content type: {compressed.content_type}")
    
    # Verify
    assert compressed.name.endswith('.webp'), "File should have .webp extension"
    assert compressed.content_type == 'image/webp', "Content type should be image/webp"
    assert len(compressed.name) == 21, "Filename should be 16 alphanumeric chars + .webp"
    
    # Test multiple compressions produce unique names
    buffer.seek(0)
    compressed2 = compress_image(
        test_image,
        max_width=1920,
        max_height=1920,
        quality=85,
        format='WEBP',
        upload_path='public/issue_images/'
    )
    assert compressed.name != compressed2.name, "Multiple compressions should produce unique filenames"
    print(f"Second compression unique name: {compressed2.name}")
    
    # Verify image was resized
    compressed.seek(0)
    compressed_img = Image.open(compressed)
    print(f"Compressed dimensions: {compressed_img.size}")
    assert compressed_img.size[0] <= 1920 and compressed_img.size[1] <= 1920, "Image should be resized"
    
    print("✅ Image compression and WebP conversion tests passed!")


def test_formats():
    """Test different output formats"""
    print("\n=== Testing Different Output Formats ===")
    
    # Create test image
    img = Image.new('RGB', (1000, 1000), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    test_image = InMemoryUploadedFile(
        buffer, 'ImageField', 'test.png', 'image/png', sys.getsizeof(buffer), None
    )
    
    # Test WebP
    webp = compress_image(test_image, format='WEBP')
    assert webp.content_type == 'image/webp'
    print(f"✓ WebP format: {webp.name}")
    
    # Test JPEG
    buffer.seek(0)
    jpeg = compress_image(test_image, format='JPEG')
    assert jpeg.content_type == 'image/jpeg'
    print(f"✓ JPEG format: {jpeg.name}")
    
    # Test PNG
    buffer.seek(0)
    png = compress_image(test_image, format='PNG')
    assert png.content_type == 'image/png'
    print(f"✓ PNG format: {png.name}")
    
    print("✅ Format conversion tests passed!")


if __name__ == '__main__':
    try:
        test_alphanumeric_filename()
        test_unique_filename_generation()
        test_image_compression()
        test_formats()
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("="*50 + "\n")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
