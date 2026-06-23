from django.contrib import admin
from django.urls import include, path
from accounts.views import signup_view, login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('main.urls')),

    # 2. 로그인/회원가입 계정 기능
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'), 

    path('user/', include('main.urls')), 
]