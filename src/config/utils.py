import random
import string
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
import sys


def generate_alphanumeric_filename(original_filename=None, length=16, extension=None):
    """
    Generates a unique alphanumeric filename.
    
    Args:
        original_filename (str, optional): Original filename to extract extension from. Defaults to None.
        length (int): Length of the alphanumeric name. Defaults to 16.
        extension (str, optional): File extension to use. If not provided, extracted from original_filename.
    
    Returns:
        str: A unique alphanumeric filename with extension (e.g., 'a3f9k2m7p1q5r8t4.webp')
    """
    # Generate alphanumeric name
    alphanumeric_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    # Determine extension
    if extension:
        ext = extension if extension.startswith('.') else f'.{extension}'
    elif original_filename:
        ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        ext = f'.{ext}' if ext else '.webp'
    else:
        ext = '.webp'
    
    return f"{alphanumeric_name}{ext}"


def generate_unique_image_filename(upload_path='', length=16, extension='webp', max_attempts=100):
    """
    Generates a unique alphanumeric filename that doesn't exist in storage.
    
    Args:
        upload_path (str): The upload path where the file will be stored (e.g., 'public/issue_images/')
        length (int): Length of the alphanumeric name. Defaults to 16.
        extension (str): File extension to use. Defaults to 'webp'.
        max_attempts (int): Maximum attempts to generate a unique name. Defaults to 100.
    
    Returns:
        str: A unique alphanumeric filename with extension
        
    Raises:
        ValueError: If unable to generate a unique filename after max_attempts
    """
    ext = extension if extension.startswith('.') else f'.{extension}'
    
    for attempt in range(max_attempts):
        # Generate alphanumeric name
        alphanumeric_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        filename = f"{alphanumeric_name}{ext}"
        full_path = f"{upload_path}{filename}" if upload_path else filename
        
        # Check if file exists in storage
        if not default_storage.exists(full_path):
            return filename
    
    # If we reach here, we couldn't generate a unique name
    raise ValueError(f"Could not generate unique filename after {max_attempts} attempts")


def compress_image(image_field, max_width=1920, max_height=1920, quality=85, format='WEBP', upload_path=''):
    """
    Compresses an image while maintaining aspect ratio and renames it with unique alphanumeric name.
    
    Args:
        image_field: Django ImageField instance
        max_width (int): Maximum width in pixels. Defaults to 1920.
        max_height (int): Maximum height in pixels. Defaults to 1920.
        quality (int): Image quality (1-100). Defaults to 85.
        format (str): Output format ('WEBP', 'JPEG', or 'PNG'). Defaults to 'WEBP'.
        upload_path (str): The upload path where file will be stored (for uniqueness check). Defaults to ''.
    
    Returns:
        InMemoryUploadedFile: Compressed image file with unique alphanumeric name
    """
    # Open the image
    img = Image.open(image_field)
    
    # Convert to RGB if needed (WebP supports RGBA, but JPEG doesn't)
    if format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
        # Create a white background for JPEG
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif format == 'WEBP' and img.mode == 'P':
        # Convert palette mode to RGBA for WebP
        img = img.convert('RGBA')
    elif format not in ('WEBP', 'PNG') and img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    
    # Get original dimensions
    width, height = img.size
    
    # Calculate new dimensions while maintaining aspect ratio
    if width > max_width or height > max_height:
        # Calculate scaling factor
        width_ratio = max_width / width
        height_ratio = max_height / height
        scale_factor = min(width_ratio, height_ratio)
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Resize image with high-quality resampling
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Save to BytesIO object
    output = BytesIO()
    
    # Save with compression based on format
    if format == 'WEBP':
        img.save(output, format='WEBP', quality=quality, method=6, lossless=False)
        content_type = 'image/webp'
        file_extension = 'webp'
    elif format == 'JPEG':
        img.save(output, format='JPEG', quality=quality, optimize=True)
        content_type = 'image/jpeg'
        file_extension = 'jpg'
    else:  # PNG
        img.save(output, format='PNG', optimize=True)
        content_type = 'image/png'
        file_extension = 'png'
    
    output.seek(0)
    
    # Generate UNIQUE alphanumeric filename by checking storage
    new_name = generate_unique_image_filename(upload_path=upload_path, extension=file_extension)
    
    # Create InMemoryUploadedFile
    compressed_image = InMemoryUploadedFile(
        output,
        'ImageField',
        new_name,
        content_type,
        sys.getsizeof(output),
        None
    )
    
    return compressed_image


def generate_unique_slug(instance, base_slug, max_length=50):
    """
    Generates a unique slug for a given model instance by appending a 4-character
    alphanumeric code to a base slug. Ensures the generated slug is unique within
    the model's database table and fits within the specified max_length.
    
    Args:
        instance: The model instance for which the slug is being generated. The
            instance's class is used to query the database for existing slugs.
        base_slug (str): The base string to which the unique code will be appended.
        max_length (int): Maximum length of the final slug. Defaults to 50.
    
    Returns:
        str: A unique slug in the format "{truncated_base_slug}-{unique_code}".
    
    Raises:
        AttributeError: If the model class does not have a `objects.filter` method
            to query the database.
    """
    def generate_code():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    # Reserve 5 characters for the separator and 4-character code ("-xxxx")
    max_base_length = max_length - 5
    
    # Truncate base_slug if it's too long
    if len(base_slug) > max_base_length:
        base_slug = base_slug[:max_base_length]
    
    slug = f"{base_slug}-{generate_code()}"
    model_class = instance.__class__
    
    # Ensure the generated slug doesn't exceed max_length
    while len(slug) > max_length or model_class.objects.filter(slug=slug).exists():
        code = generate_code()
        slug = f"{base_slug}-{code}"
        
        # Double-check length constraint
        if len(slug) > max_length:
            # Further truncate base if needed
            max_base_length = max_length - 5
            base_slug = base_slug[:max_base_length]
            slug = f"{base_slug}-{code}"
    
    return slug


def generate_unique_code(model, no_of_char=6, unique_field='id'):
    """
    Generates a unique alphanumeric code for a given model by checking for uniqueness in the specified field.
    Args:
        model: A Django model class (not instance) for which the unique code is to be generated.
        no_of_char (int, optional): The length of the generated code. Defaults to 6.
        unique_field (str, optional): The name of the model field that should be unique. Defaults to 'id'.
    Returns:
        str: A unique alphanumeric code of the specified length.
    Notes:
        - The function generates random codes consisting of lowercase letters and digits.
        - It checks the database to ensure the generated code does not already exist in the specified field.
        - The function assumes the model has a manager named 'objects' and supports the 'filter' and 'exists' methods.
    """
    def generate_code():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=no_of_char))
    
    code = generate_code()
    filter_kwargs = {unique_field: code}
    while model.objects.filter(**filter_kwargs).exists():
        code = generate_code()
    return code