from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from .models import ProductImage, EbayListing
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
import cv2
import numpy as np
from skimage.feature import match_template
import os
from dotenv import load_dotenv

load_dotenv()

def home(request):
    return render(request, 'product_matcher/home.html')

def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        product_image = ProductImage.objects.create(image=image_file)
        
        # Process the image and search eBay
        try:
            # Convert uploaded image to OpenCV format
            image_path = os.path.join(settings.MEDIA_ROOT, str(product_image.image))
            img = cv2.imread(image_path)
            
            # Basic image processing (you might want to enhance this)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Extract features or characteristics that could help in search
            # For this example, we'll just use basic terms from the filename
            search_terms = os.path.splitext(image_file.name)[0].replace('_', ' ')
            
            # Search eBay API with direct configuration
            api = Finding(domain='svcs.ebay.com',
                        appid=os.getenv('EBAY_APP_ID'),
                        config_file=None)
                        
            response = api.execute('findItemsByKeywords', {
                'keywords': search_terms,
                'outputSelector': ['SellerInfo', 'PictureURLSuperSize'],
                'paginationInput': {'entriesPerPage': 10}
            })
            
            # Process and save results
            for item in response.reply.searchResult.item:
                EbayListing.objects.create(
                    product_image=product_image,
                    title=item.title,
                    price=float(item.sellingStatus.currentPrice.value),
                    url=item.viewItemURL,
                    item_id=item.itemId,
                    condition=getattr(item, 'condition', {}).get('conditionDisplayName', 'Not specified'),
                    location=item.location,
                    seller=item.sellerInfo.sellerUserName
                )
            
            return redirect('results', image_id=product_image.id)
            
        except Exception as e:
            # Delete the product image if the search fails
            product_image.delete()
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'No image provided'}, status=400)

def results(request, image_id):
    try:
        product_image = ProductImage.objects.get(id=image_id)
        listings = product_image.ebay_listings.all()
        return render(request, 'product_matcher/results.html', {
            'product_image': product_image,
            'listings': listings
        })
    except ProductImage.DoesNotExist:
        return redirect('home')
