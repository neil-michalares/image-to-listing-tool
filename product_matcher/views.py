from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from .models import ProductImage, EbayListing
from ebaysdk.finding import Connection as Finding
from ebaysdk.shopping import Connection as Shopping
from ebaysdk.exception import ConnectionError
from google.cloud import vision
import os
from dotenv import load_dotenv
import re
import requests
from urllib.parse import urlparse
import uuid
import base64
from django.views.decorators.csrf import csrf_exempt

load_dotenv()

def home(request):
    return render(request, 'product_matcher/home.html')

def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        product_image = ProductImage.objects.create(image=image_file)
        
        try:
            # Get the full path to the uploaded image
            image_path = os.path.join(settings.MEDIA_ROOT, str(product_image.image))
            
            # Initialize Google Cloud Vision client
            client = vision.ImageAnnotatorClient()

            # Read the image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            # Create image object
            image = vision.Image(content=content)

            # Perform label detection
            label_response = client.label_detection(image=image)
            labels = label_response.label_annotations

            # Perform web detection
            web_response = client.web_detection(image=image)
            web = web_response.web_detection

            # Collect all relevant terms
            search_terms = []
            
            # Add labels (general image classification)
            for label in labels[:3]:  # Top 3 labels
                if label.score > 0.8:  # Only high confidence labels
                    search_terms.append(label.description)
                    print("label API",label.description)

            # Add web entities
            for entity in web.web_entities[:3]:  # Top 3 web entities
                if entity.score > 0.8:  # Only high confidence entities
                    search_terms.append(entity.description)
                    print("entity API",entity.description)

            # Create search query from the collected terms
            search_query = ' '.join(search_terms)
            
            # Search eBay API with direct configuration
            api = Finding(domain='svcs.ebay.com',
                        appid=os.getenv('EBAY_APP_ID'),
                        config_file=None)
                        
            response = api.execute('findItemsByKeywords', {
                'keywords': search_query,
                'outputSelector': ['SellerInfo', 'PictureURLSuperSize'],
                'paginationInput': {'entriesPerPage': 10},
                'sortOrder': 'BestMatch'  # Sort by best match
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

def extract_ebay_item_id(url):
    # Common eBay URL patterns
    patterns = [
        r'/itm/(?:[^/]+/)?(\d+)',  # Matches /itm/title/123456 or /itm/123456
        r'item=(\d+)',             # Matches item=123456
        r'ItemId=(\d+)',          # Matches ItemId=123456
        r'/(\d{12})',             # Matches 12-digit item IDs in URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_ebay_item_details(item_id):
    try:
        api = Shopping(domain='open.api.ebay.com',
                      appid=os.getenv('EBAY_APP_ID'),
                      config_file=None)
        
        response = api.execute('GetSingleItem', {
            'ItemID': item_id,
            'IncludeSelector': 'Details,ItemSpecifics'
        })
        
        item = response.reply.Item
        return {
            'title': item.Title,
            'price': f"${float(item.CurrentPrice.value):.2f}",
            'currency': item.CurrentPrice._currencyID,
            'condition': item.ConditionDisplayName if hasattr(item, 'ConditionDisplayName') else 'Not specified',
            'location': item.Location if hasattr(item, 'Location') else 'Not specified',
            'url': item.ViewItemURLForNaturalSearch if hasattr(item, 'ViewItemURLForNaturalSearch') else None
        }
    except Exception as e:
        print(f"Error fetching eBay item details: {str(e)}")
        return None

@csrf_exempt
def test_vision(request):
    """View for testing the Google Cloud Vision API."""
    return render(request, 'product_matcher/test_vision.html')

def process_image(request, file_path):
    try:
        # Initialize Google Cloud Vision client
        client = vision.ImageAnnotatorClient()

        # Read the image file
        with open(file_path, 'rb') as f:
            image_content = f.read()

        # Create image object
        image = vision.Image(content=image_content)

        # Perform various detections
        label_response = client.label_detection(image=image)
        web_response = client.web_detection(image=image)
        text_response = client.text_detection(image=image)

        # Get web detection results
        web = web_response.web_detection
        
        # Extract eBay-specific results with details
        ebay_results = []
        if web.pages_with_matching_images:
            for page in web.pages_with_matching_images:
                if 'ebay' in page.url.lower():
                    item_id = extract_ebay_item_id(page.url)
                    listing_info = {
                        'url': page.url,
                        'title': page.page_title if page.page_title else 'eBay Listing'
                    }
                    
                    if item_id:
                        details = get_ebay_item_details(item_id)
                        if details:
                            listing_info.update(details)
                    
                    ebay_results.append(listing_info)

        # Get relative URL for the image
        fs = FileSystemStorage()
        relative_path = os.path.relpath(file_path, fs.location)
        image_url = fs.url(relative_path)

        # Collect results
        results = {
            'image_url': image_url,
            'labels': [
                {'description': label.description, 'score': f"{label.score:.2%}"}
                for label in label_response.label_annotations
            ],
            'web_entities': [
                {'description': entity.description, 'score': f"{entity.score:.2%}"}
                for entity in web_response.web_detection.web_entities
            ],
            'text': text_response.text_annotations[0].description if text_response.text_annotations else None,
            'web_matches': {
                'ebay_listings': ebay_results,
                'similar_images': [
                    {'url': image.url}
                    for image in web.visually_similar_images[:5]
                ] if web.visually_similar_images else [],
                'pages': [
                    {'url': page.url, 'title': page.page_title}
                    for page in web.pages_with_matching_images[:5]
                    if page.page_title  # Only include pages with titles
                ] if web.pages_with_matching_images else []
            }
        }

        return render(request, 'product_matcher/test_vision.html', {'results': results})

    except Exception as e:
        # Clean up the file if there's an error
        try:
            os.remove(file_path)
            if 'temp_file' in request.session:
                del request.session['temp_file']
        except (FileNotFoundError, OSError):
            pass
        
        return render(request, 'product_matcher/test_vision.html', {
            'error': f'Error processing image: {str(e)}'
        })
