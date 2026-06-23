from django.urls import path
from .views import game_view, home_view, intro_view
from users import views as user_views
from . import views

urlpatterns = [
    path('', intro_view, name='intro'),
    path('home/', home_view, name='home'),
    path('game/', game_view, name='game'),
    
    path('mypage/', user_views.mypage_view, name='mypage'),
    path('mypage/profile/', user_views.profile_view, name='profile'),
    path('mypage/edit-info/', user_views.info_edit_view, name='edit_information'),
    path('mypage/edit-pw/', user_views.password_edit_view, name='edit'),
    path('mypage/logout/', user_views.logout_view, name='mypage_logout'),
    path('mypage/history/', user_views.room_history_view, name='room_history'),
    path('mypage/history/<int:room_id>/', user_views.room_history_detail_view, name='room_history_detail'),
    path('mypage/contact/', user_views.contact_us_view, name='contact_us'),
    path('mypage/withdraw/', user_views.withdraw_view, name='withdraw'),

    path('ranking/', views.ranking_list, name='ranking'),
]