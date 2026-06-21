from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import UserProfile
from main.models import Room, RoomMember, Inquiry

def mypage_view(request):
    """
    1. 마이페이지 메인 (mypage.html)
    - 프로필 정보 조회
    - 전적 통계 집계 (총 라운드, 최고 온도, 방 개수, 벌칙 수 등)
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)

    user_rooms = RoomMember.objects.filter(user=user)
    total_rooms_count = user_rooms.count()
    
    # 전적 통계 초기값
    highest_temp = 36.5
    total_rounds = 0
    penalty_count = 0
    
    for member in user_rooms:
        room = member.room
        if room.temperature > highest_temp:
            highest_temp = room.temperature
        
        if hasattr(room, 'total_rounds'):
            total_rounds += room.total_rounds
            
    context = {
        'profile': profile,
        'total_rooms_count': total_rooms_count,
        'highest_temp': highest_temp,
        'total_rounds': total_rounds,
        'penalty_count': penalty_count,
    }
    return render(request, 'main/mypage/mypage.html', context)


def profile_view(request):
    """
    2. 간단 프로필 상자/요약 페이지 (profile.html)
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, 'main/mypage/profile.html', {'profile': profile})


def info_edit_view(request):
    """
    3. 정보 수정 메인 페이지 (edit_information.html 또는 edit.html)
    - 닉네임, 위굴이(프로필 캐릭터) 변경 처리
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        new_nickname = request.POST.get('nickname')
        new_profile_character = request.POST.get('profile_character')
        
        # 데이터가 프론트에서 들어왔을 때만 변경 후 세이브
        if new_nickname:
            profile.nickname = new_nickname
        if new_profile_character:
            profile.profile_image = new_profile_character
            
        profile.save()
        messages.success(request, "성공적으로 프로필이 수정되었습니다.")
        return redirect('mypage')
        
    return render(request, 'main/mypage/edit_information.html', {'profile': profile})


def password_edit_view(request):
    """
    4. 비밀번호 변경 분리 페이지 (edit.html)
    - 닉네임 변경 폼과 분리되거나 패스워드 전용 단독 처리 시 사용
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.method == 'POST':
        new_password = request.POST.get('password')
        if new_password:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # 비밀번호 변경 후 로그아웃 방지
            messages.success(request, "비밀번호가 변경되었습니다.")
            return redirect('mypage')
            
    return render(request, 'main/mypage/edit.html')


def logout_view(request):
    """
    5. 로그아웃 (mypage 내 버튼 액션)
    """
    auth_logout(request)
    messages.success(request, "로그아웃 되었습니다.")
    return redirect('home')


def room_history_view(request):
    """
    6. 내 방 히스토리 전체 리스트 (room_history.html)
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    room_history = RoomMember.objects.filter(user=request.user).order_by('-id')
    return render(request, 'main/mypage/room_history.html', {'room_history': room_history})


def room_history_detail_view(request, room_id):
    """
    7. 내 방 히스토리 상세 (room_history_detail.html)
    - 소속 멤버 목록, 질문 전적(활동 요약) 조회
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    room = get_object_or_404(Room, id=room_id)
    room_members = RoomMember.objects.filter(room=room)
    
    context = {
        'room': room,
        'room_members': room_members,
    }
    return render(request, 'main/mypage/room_history_detail.html', context)


def contact_us_view(request):
    """
    8. 문의하기 (contact_us.html)
    - 자주 묻는 질문(FAQ) 데이터 전송, 문의 내역 확인, 신규 문의 작성
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        Inquiry.objects.create(
            user=request.user,
            title=title,
            content=content
        )
        messages.success(request, "문의사항이 접수되었습니다.")
        return redirect('contact_us')

    my_inquiries = Inquiry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/mypage/contact_us.html', {'my_inquiries': my_inquiries})


def withdraw_view(request):
    """
    9. 탈퇴하기 (withdraw.html)
    - 탈퇴 전 최종 안내 확인창 보여주기 및 POST 요청 시 실제 삭제
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.method == 'POST':
        user = request.user
        auth_logout(request)
        user.delete()
        messages.success(request, "그동안 서비스를 이용해 주셔서 감사합니다.")
        return redirect('home')
        
    return render(request, 'main/mypage/withdraw.html')