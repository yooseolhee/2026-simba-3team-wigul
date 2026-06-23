from django.urls import path
from .views import create_room_view, game_view, home_view, intro_view, myroom_detail_view, myroom_view ,subject_select_modal_view, result_view,extend_timer_view
from users import views as user_views
from . import views

urlpatterns = [
    path('', intro_view, name='intro'),
    path('home/', home_view, name='home'),
    path('game/', game_view, name='game'),
    path('create-room/', create_room_view, name='create-room'),
    path('game/<str:room_id>/', game_view, name='game'),
    path('subject-select/<uuid:room_id>/', subject_select_modal_view, name='subject_select'),
    path('result/<uuid:room_id>/<int:round_number>/', result_view, name='result'),
    path('extend/<uuid:room_id>/<int:round_number>/', extend_timer_view, name='extend_timer'),



    path('mypage/', user_views.mypage_view, name='mypage'),
    path('mypage/profile/', user_views.profile_view, name='profile'),
    path('mypage/edit-info/', user_views.info_edit_view, name='edit_information'),
    path('mypage/edit-pw/', user_views.password_edit_view, name='edit'),
    path('mypage/logout/', user_views.logout_view, name='mypage_logout'),
    path('mypage/history/', user_views.room_history_view, name='room_history'),
    path('mypage/history/<int:room_id>/', user_views.room_history_detail_view, name='room_history_detail'),
    path('mypage/contact/', user_views.contact_us_view, name='contact_us'),
    path('mypage/contact-list/', user_views.contact_us_list_view, name='contact_us_list'),
    path('mypage/withdraw/', user_views.withdraw_view, name='withdraw'),
    
    path('ranking/', views.ranking_list, name='ranking'),
    path('room/', myroom_view, name='myroom'),
    path('room/detail', myroom_detail_view, name='myroom-detail'),
]