import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import UserProfile
from main.models import GameRound, Room, RoomMember, Inquiry

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe # 💡 텍스트를 HTML 태그로 안전하게 변환해주는 장치
from accounts.models import UserProfile
from main.models import RoomMember

def mypage_view(request):
    """
    1. 마이페이지 메인 (mypage.html)
    - profile_character 필드 이름에 맞춰 완벽하게 연동
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    user_rooms = RoomMember.objects.filter(user=user)
    
    # 전적 통계 집계
    # 전적 통계 집계
    total_rooms_count = user_rooms.count()
    highest_temp = 36.5

    # 사용자가 참여했던 모든 방의 실제 진행 라운드 수
    total_rounds = GameRound.objects.filter(
        room__members__user=user
    ).count()

    for member in user_rooms:
        room = member.room

        if room.temperature > highest_temp:
            highest_temp = room.temperature

    db_color = profile.background_color or 'bg-red'

    avatar_html = mark_safe(
        f'<img src="{profile.avatar_url}" alt="위굴이" '
        f'style="width:100%; height:100%; object-fit:contain;">'
    )

    context = {
        'user_profile': {
            'nickname': profile.nickname,
            'color': db_color,
            'avatar': avatar_html,
        },
        'stats': {
            'total_rounds': total_rounds,
            'max_temp': highest_temp,
            'room_count': total_rooms_count,
        },
        'history_list': [
            {
                'room': member.room,
                'temp': member.room.temperature,
                'name': member.room.title,
            }
            for member in user_rooms
        ]
    }
    return render(request, 'main/mypage/mypage.html', context)

def profile_view(request):
    """
    2. 간단 프로필 상자/요약 페이지 (profile.html)
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, 'main/mypage/edit_profile.html', {'profile': profile})


def info_edit_view(request):
    """
    3. 정보 수정 메인 페이지 (edit_profile.html)
    - 클릭 없이 제출되어도 기존 데이터가 유지되도록 방어 로직 추가
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        new_nickname = request.POST.get('nickname')
        new_color = request.POST.get('profile_color')
        raw_avatar_path = request.POST.get('profile_image')
        
        # 1. 닉네임 수정
        if new_nickname:
            profile.nickname = new_nickname
            
        # 2. 배경 색상 수정 (하드코딩 초기값 제출 방어)
        if new_color:
            # 사용자가 아무것도 클릭하지 않아서 HTML 초기값인 bg-red가 그대로 날아왔고,
            # 정작 사용자의 기존 색상은 bg-red가 아니라면 무시하고 기존 색상을 유지합니다.
            if new_color == 'bg-red' and profile.background_color != 'bg-red' and not new_color:
                pass
            else:
                profile.background_color = new_color
            
        # 3. 캐릭터 이미지 수정 (하드코딩 초기값 제출 방어)
        if raw_avatar_path:
            clean_filename = os.path.basename(raw_avatar_path)
            
            # 클릭 없이 static 경로 문구가 그대로 전송되었거나 wigul_1.png로 강제 덮어쓰기 되려는 현상 차단
            if "static" in clean_filename or "{" in clean_filename:
                pass
            elif clean_filename == 'wigul_1.png' and profile.profile_character != 'wigul_1.png':
                # 사용자가 고른 적이 없는데 1번 개구리로 강제 전송된 거라면 기존 캐릭터 유지
                pass
            else:
                profile.profile_character = clean_filename
            
        profile.save()
        messages.success(request, "성공적으로 프로필이 수정되었습니다.")
        return redirect('mypage')
        
    return render(request, 'main/mypage/edit_profile.html', {'profile': profile})
def password_edit_view(request):
    """
    4. 비밀번호 변경 처리 페이지 (edit_information.html)
    - 현재 비밀번호가 일치할 때만 새 비밀번호를 암호화해서 DB에 덮어씁니다.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    template_name = 'main/mypage/edit_information.html'
        
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, "현재 비밀번호가 일치하지 않습니다.")
            return render(request, template_name)
            
        if new_password != confirm_password:
            messages.error(request, "새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다.")
            return render(request, template_name)
            
        if new_password:
            request.user.set_password(new_password) 
            request.user.save()

            update_session_auth_hash(request, request.user)  
            
            messages.success(request, "비밀번호가 성공적으로 변경되었습니다.")
            return redirect('mypage')
            
    return render(request, template_name)


def logout_view(request):
    """
    5. 로그아웃 (mypage 내 버튼 액션)
    """
    auth_logout(request)
    messages.success(request, "로그아웃 되었습니다.")
    return redirect('home')


def room_history_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    rooms = Room.objects.filter(
        members__user=request.user
    ).distinct().order_by('-created_at')

    return render(
        request,
        'main/mypage/room_history.html',
        {
            'history_list': rooms
        }
    )

from django.utils.safestring import mark_safe

def room_history_detail_view(request, room_id):

    if not request.user.is_authenticated:
        return redirect('login')

    room = get_object_or_404(Room, id=room_id)

    room_members = RoomMember.objects.filter(room=room)

    members = []

    for m in room_members:

        profile = m.user.userprofile

        avatar_html = mark_safe(
            f'<img src="{profile.avatar_url}" '
            f'style="width:100%;height:100%;object-fit:contain;">'
        )

        members.append({
            "nickname": profile.nickname,
            "avatar": avatar_html,
            "color": profile.background_color,
            "is_host": m.is_host,
        })

    rounds = GameRound.objects.filter(room=room)

    summary = {
        "total_rounds": rounds.count(),
        "votes": sum(r.extensions for r in rounds),
        "avg_change":
            round(
                sum(r.change_rate for r in rounds) / rounds.count(),
                1
            ) if rounds.exists() else 0
    }

    questions = []

    for r in rounds:

        if r.question_zone == "GREEN":
            color = "green"

        elif r.question_zone == "YELLOW":
            color = "yellow"

        else:
            color = "pink"

        questions.append({
            "round_num": r.round_number,
            "text": r.question_text,
            "color": color
        })

    context = {
        "room": room,
        "members": members,
        "summary": summary,
        "questions": questions
    }

    return render(
        request,
        "main/mypage/room_history_detail.html",
        context
    )

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
        return redirect('contact_us_list')

    return render(request, 'main/mypage/contact_us.html')


def contact_us_list_view(request):
    """
    [추가] 내가 문의한 내역 목록 보기 (contact_us_list.html)
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    my_inquiries = Inquiry.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'main/mypage/contact_us_list.html', {'my_inquiries': my_inquiries})

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
        
        return redirect('intro') 
        
    return render(request, 'main/mypage/withdraw.html')