from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from .models import ProductImage, EbayListing
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from google.cloud import vision
import os
from dotenv import load_dotenv

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

            # Perform object detection
            object_response = client.object_localization(image=image)
            objects = object_response.localized_object_annotations

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

            # Add detected objects
            for obj in objects[:3]:  # Top 3 objects
                if obj.score > 0.8:  # Only high confidence objects
                    search_terms.append(obj.name)
                    print("obj API",obj.name)
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

def test_vision(request):
    # Clean up old file if it exists
    if 'temp_file' in request.session:
        try:
            fs = FileSystemStorage()
            fs.delete(request.session['temp_file'])
        except:
            pass
        del request.session['temp_file']

    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(f'temp/{image_file.name}', image_file)
        image_path = fs.path(filename)
        
        try:
            # Initialize Google Cloud Vision client
            client = vision.ImageAnnotatorClient()

            # Read the image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            # Create image object
            image = vision.Image(content=content)

            # Perform various detections
            label_response = client.label_detection(image=image)
            object_response = client.object_localization(image=image)
            web_response = client.web_detection(image=image)
            text_response = client.text_detection(image=image)

            # Store the filename in session for cleanup on next request
            request.session['temp_file'] = filename

            # Get web detection results
            web = web_response.web_detection
            
            # Extract eBay-specific results
            ebay_results = []
            if web.pages_with_matching_images:
                for page in web.pages_with_matching_images:
                    if 'ebay' in page.url.lower():
                        ebay_results.append({
                            'url': page.url,
                            'title': page.page_title if page.page_title else 'eBay Listing'
                        })

            # Collect results
            results = {
                'labels': [
                    {'description': label.description, 'score': f"{label.score:.2%}"}
                    for label in label_response.label_annotations
                ],
                'objects': [
                    {'name': obj.name, 'score': f"{obj.score:.2%}"}
                    for obj in object_response.localized_object_annotations
                ],
                'web_entities': [
                    {'description': entity.description, 'score': f"{entity.score:.2%}"}
                    for entity in web_response.web_detection.web_entities
                ],
                'text': text_response.text_annotations[0].description if text_response.text_annotations else None,
                'image_url': fs.url(filename),
                'web_matches': {
                    'ebay_listings': ebay_results,
                    'similar_images': [
                        {'url': image.url}
                        for image in web.visually_similar_images[:5]
                    ] if web.visually_similar_images else [],
                    'full_matches': [
                        {'url': image.url}
                        for image in web.full_matching_images[:5]
                    ] if web.full_matching_images else [],
                    'partial_matches': [
                        {'url': image.url}
                        for image in web.partial_matching_images[:5]
                    ] if web.partial_matching_images else [],
                    'pages': [
                        {'url': page.url, 'title': page.page_title}
                        for page in web.pages_with_matching_images[:5]
                        if page.page_title  # Only include pages with titles
                    ] if web.pages_with_matching_images else []
                }
            }
            
            return render(request, 'product_matcher/vision_test.html', {'results': results})
            
        except Exception as e:
            # Clean up the file if there's an error
            fs.delete(filename)
            if 'temp_file' in request.session:
                del request.session['temp_file']
            return render(request, 'product_matcher/vision_test.html', {'error': str(e)})
    
    return render(request, 'product_matcher/vision_test.html')
