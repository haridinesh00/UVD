from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('search-results/', views.search_results, name='search_results'),
    path('download/', views.download_video, name='download_video'),
]