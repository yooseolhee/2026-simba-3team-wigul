from django.urls import path
from users import views as user_views
from . import views

urlpatterns = [
    # 🏠 메인/홈 화면
    path('', views.intro_view, name='intro'),
    path('home/', views.home_view, name='home'),

    # ⭐ 스마트 방 생성 & 대기방 플로우
    path('create-room/', views.create_room_action, name='create_room_action'),
    path('waiting-room/<uuid:room_id>/', views.waiting_room_view, name='waiting_room'),
    path('waiting-room/<uuid:room_id>/members/', views.waiting_room_members_api, name='waiting_room_members'),

    # 🎮 게임 진행 및 결과 플로우
    path('game/<uuid:room_id>/', views.game_view, name='game'),
    path('subject-select/<uuid:room_id>/', views.subject_select_modal_view, name='subject_select'),
    path('game/<uuid:room_id>/<int:round_number>/state/', views.round_state_api, name='round_state'),
    path('game/<uuid:room_id>/<int:round_number>/start-voting/', views.start_voting_view, name='start_voting'),
    path('game/<uuid:room_id>/<int:round_number>/final-vote/', views.final_vote_view, name='final_vote'),
    path('game/<uuid:room_id>/<int:round_number>/final-status/', views.final_status_api, name='final_status'),
    path('result/<uuid:room_id>/<int:round_number>/', views.result_view, name='result'),
    path('extend/<uuid:room_id>/<int:round_number>/', views.extend_timer_view, name='extend_timer'),

    # 👤 마이페이지 플로우 (users 앱 연동)
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

    # 🏆 랭킹 및 나의 방 플로우
    path('ranking/', views.ranking_list, name='ranking'),
    path('room/', views.myroom_view, name='myroom'),
    path('room/detail/', views.myroom_detail_view, name='myroom-detail'),
]