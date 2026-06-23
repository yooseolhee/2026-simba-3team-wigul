import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile 


# 1. 회원가입 처리 (닉네임 유효성 검사 + 자동 로그인 & 워프 연동)
def signup_view(request):
    if request.method == 'GET' and request.user.is_authenticated:
        return redirect('home')

    # 주소창에 ?next=... 가 들어와 있다면 추출합니다.
    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        nickname = request.POST.get('nickname')
        profile_character = request.POST.get('profile_character', 'basic')
        background_color = request.POST.get('profile_color', 'bg-red')
        
        # 템플릿 hidden 필드로 넘어온 next 주소까지 2중 방어망으로 수집
        next_url = request.POST.get('next', next_url)

        # 오류 발생 시 기존 입력 데이터와 next 주소를 유지하기 위한 context
        context = {
            'username': username,
            'nickname': nickname,
            'profile_character': profile_character,
            'background_color': background_color,
            'next': next_url  # 이 값이 들어가야 템플릿이 지치지 않고 주소를 기억합니다.
        }

        # [검사 1] 아이디 중복 검사
        if User.objects.filter(username=username).exists():
            messages.error(request, "이미 존재하는 아이디입니다.")
            return render(request, 'accounts/signup.html', context)
        
        # [검사 2] 닉네임 검사: 길이 (2자 이상 15자 이하)
        if not (2 <= len(nickname) <= 15):
            messages.error(request, "닉네임은 2자 이상 15자 이하로 설정해야 합니다.")
            return render(request, 'accounts/signup.html', context)
        
        # [검사 3] 닉네임 검사: 특수문자 금지 (영문, 숫자, 한글만 허용)
        if not re.match(r'^[a-zA-Z0-9가-힣]+$', nickname):
            messages.error(request, "닉네임에 특수문자는 사용할 수 없습니다.")
            return render(request, 'accounts/signup.html', context)
        
        # 데이터 검증 완료 후 유저 및 프로필 생성
        user = User.objects.create_user(username=username, password=password)

        UserProfile.objects.create(
            user=user,
            nickname=nickname,
            profile_character=profile_character,
            background_color=background_color
        )

        # ⭐ [QR 패스 패키지] 가입과 즉시 로그인을 시켜주어 팀원의 피로도를 대폭 줄입니다.
        auth_login(request, user)
        messages.success(request, f"{nickname}님, 회원가입 및 로그인이 완료되었습니다!")

        # 초대받은 방 주소(next)가 있다면 바로 입장, 없으면 홈으로 보냅니다.
        if next_url:
            return redirect(next_url)
        return redirect('home') 
    
    # 최초 GET 요청 시 템플릿에 ?next= 주소를 할당합니다.
    return render(request, 'accounts/signup.html', {'next': next_url})


# 2. 로그인 처리 (방 바로 가기 추적 기능 탑재)
def login_view(request):
    if request.method == 'GET' and request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', next_url)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
    
            try:
                nickname = user.userprofile.nickname
            except UserProfile.DoesNotExist:
                new_profile = UserProfile.objects.create(
                    user=user,
                    nickname=user.username,
                    profile_character='default_frog',
                    background_color='#FFFFFF'
                )
                nickname = new_profile.nickname

            messages.success(request, f"{nickname}님 환영합니다!")
            
            # QR을 타고 넘어온 주소가 있다면 로그인 즉시 방으로 다이렉트 워프
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            # 에러 발생 시 입력 폼에 주소를 잃어버리지 않도록 딕셔너리로 에러 마킹 전달
            messages.error(request, "올바른 아이디 혹은 비밀번호를 입력하세요.")
            return render(request, 'accounts/login.html', {'next': next_url, 'error': True})
        
    return render(request, 'accounts/login.html', {'next': next_url})


# 3. 로그아웃 처리
def logout_view(request):
    auth_logout(request)
    return redirect('login')