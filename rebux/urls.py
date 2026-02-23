from django.urls import path
from .views import GenerateLevelsView, PlayGameView, WinGameView

urlpatterns = [
    path('', PlayGameView.as_view(), name='play_game'),
    path('win/', WinGameView.as_view(), name='win_game'),
    path('generate-levels/', GenerateLevelsView.as_view(), name='generate_levels'),
]