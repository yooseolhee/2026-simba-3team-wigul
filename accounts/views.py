from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile 

# 1. 회원가입 처리
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        nickname = request.POST.get('nickname')
        profile_image = request.POST.get('profile_image', 'default_frog')
        background_color = request.POST.get('background_color', '#FFFFFF')

        if User.objects.filter(username=username).exists():
            messages.error(request, "이미 존재하는 아이디입니다.")
            return render(request, 'accounts/signup.html')

        # Django 기본 User 생성 (비밀번호 자동 암호화)
        user = User.objects.create_user(username=username, password=password)

        UserProfile.objects.create(
            user=user,
            nickname=nickname,
            profile_image=profile_image,
            background_color=background_color
        )

        messages.success(request, "회원가입이 완료되었습니다! 로그인을 진행해 주세요.")
        return redirect('login') 
    
    return render(request, 'accounts/signup.html')


# 2. 로그인 처리
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"{user.userprofile.nickname}님 환영합니다!")
            return redirect('home') 
        else:
            messages.error(request, "올바른 아이디 혹은 비밀번호를 입력하세요.")
            return render(request, 'accounts/login.html')
        
    return render(request, 'accounts/login.html')


# 3. 로그아웃 처리
def logout_view(request):
    auth_logout(request)
    return redirect('login')