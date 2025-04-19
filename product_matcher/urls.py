from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_image, name='upload_image'),
    path('results/<int:image_id>/', views.results, name='results'),
    path('test-vision/', views.test_vision, name='test_vision'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 