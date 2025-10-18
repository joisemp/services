# Image Compression Feature

## Overview
All images uploaded to the system are now automatically compressed to optimize storage space and improve page load times while maintaining visual quality.

## Technical Details

### Compression Utility
Location: `src/config/utils.py`

The `compress_image()` function handles all image compression with the following features:

- **Maximum Dimensions**: Images are resized to a maximum of 1920x1920 pixels while maintaining aspect ratio
- **Quality**: JPEG quality set to 85% (optimal balance between file size and visual quality)
- **Format Handling**: 
  - Converts RGBA/LA/P images to RGB with white background when saving as JPEG
  - Supports both JPEG and PNG formats
  - Uses high-quality LANCZOS resampling for resizing
- **Optimization**: Enables optimization flags for both JPEG and PNG formats

### Parameters
```python
compress_image(
    image_field,
    max_width=1920,      # Maximum width in pixels
    max_height=1920,     # Maximum height in pixels
    quality=85,          # JPEG quality (1-100)
    format='JPEG'        # Output format ('JPEG' or 'PNG')
)
```

## Models with Compression

All image models in the system automatically compress uploaded images:

1. **IssueImage** - Images attached to issues
2. **WorkTaskResolutionImage** - Images attached to work task resolutions
3. **IssueResolutionImage** - Images attached to issue resolutions
4. **SiteVisitImage** - Images captured during site visits
5. **IssueReviewCommentImage** - Images attached to review comments

## How It Works

1. When an image is uploaded, the model's `save()` method is called
2. Before saving to the database, the compression check is performed:
   - Checks if it's a new upload or if the image has been changed
   - Only compresses new images (not on every save)
3. The `compress_image()` utility processes the image:
   - Opens the image using PIL (Pillow)
   - Converts color modes if necessary
   - Resizes if dimensions exceed maximum values
   - Compresses with specified quality
   - Returns an in-memory file ready to save
4. The compressed image is saved to storage (local or DigitalOcean Spaces)

## Benefits

- **Reduced Storage Costs**: Compressed images take up less space
- **Faster Loading**: Smaller file sizes load faster, improving user experience
- **Bandwidth Savings**: Less data transferred between server and clients
- **Maintained Quality**: 85% JPEG quality is barely distinguishable from original
- **Automatic**: No manual intervention required - all images are compressed on upload

## Storage Impact

### Before Compression
- Average photo from smartphone: 3-8 MB
- High-resolution images: 10+ MB

### After Compression (1920x1920, Quality 85)
- Typical compressed size: 200-800 KB
- Storage reduction: 80-95% depending on original image

## Configuration

To adjust compression settings, modify the parameters in each model's `save()` method:

```python
# Example: More aggressive compression
self.image = compress_image(
    self.image, 
    max_width=1280,      # Smaller max size
    max_height=1280, 
    quality=75           # Lower quality
)

# Example: Higher quality for critical images
self.image = compress_image(
    self.image, 
    max_width=2560,      # Larger max size
    max_height=2560, 
    quality=90           # Higher quality
)
```

## Dependencies

The compression feature uses **Pillow** (PIL fork), which is already included in `requirements.txt`:
```
pillow==11.3.0
```

## Notes

- Compression only occurs on **new uploads** or when images are **changed**
- Existing images in the database are NOT automatically recompressed
- Images already smaller than max dimensions are still recompressed for quality optimization
- Original filenames are preserved (only extension may change to .jpg)
- Compression is lossless for PNG format, lossy for JPEG
