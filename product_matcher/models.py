from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

def validate_file_size(value):
    filesize = value.size
    megabyte_limit = 6
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError(f"The maximum file size that can be uploaded is {megabyte_limit}MB")

# Create your models here.

class ProductImage(models.Model):
    image = models.ImageField(upload_to='product_images/', validators=[validate_file_size])
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Product Image {self.id} - {self.uploaded_at}"

class VisionAPICall(models.Model):
    product_image = models.ForeignKey(ProductImage, on_delete=models.CASCADE, related_name='vision_api_calls')
    request_timestamp = models.DateTimeField(default=timezone.now)
    api_response = models.JSONField()  # Stores the complete API response
    labels = models.JSONField(null=True, blank=True)  # Stores label detection results
    text = models.JSONField(null=True, blank=True)    # Stores text detection results
    detected_objects = models.JSONField(null=True, blank=True)  # Stores object detection results
    error = models.TextField(null=True, blank=True)    # Stores any error messages
    processing_time_ms = models.IntegerField(null=True)  # Time taken for API call
    
    def __str__(self):
        return f"Vision API Call for Image {self.product_image_id} at {self.request_timestamp}"
    
    class Meta:
        ordering = ['-request_timestamp']

class EbayListing(models.Model):
    product_image = models.ForeignKey(ProductImage, on_delete=models.CASCADE, related_name='ebay_listings')
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField()
    item_id = models.CharField(max_length=100)
    condition = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    seller = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
