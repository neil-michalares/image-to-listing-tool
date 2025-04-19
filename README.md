# eBay Tool Lister

A Django web application that uses Google Cloud Vision API to analyze images and find similar items on eBay. The application can detect objects, text, and labels in images and match them with relevant eBay listings.

## Features

- Image upload via file selection, drag & drop, or clipboard paste
- Google Cloud Vision API integration for:
  - Label Detection
  - Text Detection
  - Web Detection
- eBay API integration for finding matching listings
- Display of detailed product information including:
  - Prices
  - Item conditions
  - Seller locations
  - Similar images
  - Related web pages

## Prerequisites

- Python 3.8 or higher
- Django 4.2.10
- Google Cloud Vision API access
- eBay Developer Account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/neil-michalares/image-to-listing-tool.git
cd image-to-listing-tool
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in a `.env` file:
```
EBAY_APP_ID=your-ebay-app-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
DJANGO_SECRET_KEY=your-django-secret-key
DEBUG=True  # Set to False in production
```

## Required Environment Variables

### Google Cloud Vision API
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud service account key file
  - Create a project in Google Cloud Console
  - Enable the Vision API
  - Create a service account and download the JSON key file
  - Set this variable to the path of your JSON key file

### eBay API
- `EBAY_APP_ID`: Your eBay Developer Application ID
  - Register at [eBay Developers Program](https://developer.ebay.com)
  - Create a new application
  - Copy the Application ID (Production)

### Django Settings
- `DJANGO_SECRET_KEY`: Secret key for Django
- `DEBUG`: Boolean flag for debug mode (set to False in production)

## Development Setup

1. Apply database migrations:
```bash
python manage.py migrate
```

2. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

3. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Access the application at `http://localhost:8000`
2. Upload an image using one of the available methods:
   - Click to browse files
   - Drag and drop an image
   - Paste from clipboard
3. The application will analyze the image and display:
   - Detected labels and objects
   - Similar eBay listings
   - Related web content
   - Detected text (if any)

## Security Considerations

- Never commit the `.env` file or Google Cloud credentials to version control
- Keep your eBay API credentials secure
- In production:
  - Set DEBUG=False
  - Use secure HTTPS connections
  - Update Django's SECRET_KEY
  - Configure proper ALLOWED_HOSTS

## API Usage and Costs

### Google Cloud Vision API
- Free tier: First 1,000 units per month
- Paid usage (1,001 - 5,000,000 units):
  - Label Detection: $1.50 per 1,000 units
  - Text Detection: $1.50 per 1,000 units
  - Web Detection: $3.50 per 1,000 units

### eBay API
- Check [eBay Developer Program](https://developer.ebay.com) for current API call limits and pricing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License