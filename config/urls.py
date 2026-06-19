"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import home_view, intro_view
from accounts.views import signup_view, login_view, logout_view
from users import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', intro_view, name='intro'),

    path('home/', home_view, name='home'),

    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('mypage/', views.mypage_view, name='mypage'),
    path('mypage/profile/', views.profile_view, name='profile'),
    path('mypage/edit-info/', views.info_edit_view, name='edit_information'),
    path('mypage/edit-pw/', views.password_edit_view, name='edit'),
    path('mypage/logout/', views.logout_view, name='logout'),
    path('mypage/history/', views.room_history_view, name='room_history'),
    path('mypage/history/<int:room_id>/', views.room_history_detail_view, name='room_history_detail'),
    path('mypage/contact/', views.contact_us_view, name='contact_us'),
    path('mypage/withdraw/', views.withdraw_view, name='withdraw'),
    
]