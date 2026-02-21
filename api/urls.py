from django.urls import path
from . import views
from .views import YouTubeSearchAPIView, YouTubeDownloadAPIView

urlpatterns = [
    # path('example/', views.example_view, name='example_view'),
    path('youtube-search/', YouTubeSearchAPIView.as_view(), name='youtube_search'),
    path('youtube-download/', YouTubeDownloadAPIView.as_view(), name='youtube_download'),
]