from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_image, name='upload_image'),
    path('results/<int:image_id>/', views.results, name='results'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 