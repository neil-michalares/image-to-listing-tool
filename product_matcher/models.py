from django.db import models
from django.utils import timezone

# Create your models here.

class ProductImage(models.Model):
    image = models.ImageField(upload_to='product_images/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Product Image {self.id} - {self.uploaded_at}"

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
