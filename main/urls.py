from django.urls import path
from .views import game_view, home_view, intro_view


urlpatterns = [
    path('', intro_view, name='intro'),
    path('home/', home_view, name='home'),
    path('game/', game_view, name='game'),

]