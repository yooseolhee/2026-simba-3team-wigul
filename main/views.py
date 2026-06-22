import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Room, RoomMember, GameRound, Question, TempEngine

def intro_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'main.html')

@login_required
def home_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')
    
    # ✅ 수정 포인트 3: 중복 방지를 위해 distinct() 추가 및 최신방 상위 정렬
    rooms = Room.objects.filter(members__user=request.user).distinct().order_by('-created_at')
    
    context = {
        'rooms': rooms,
    }
    return render(request, 'main/home/home.html', context)

@login_required
def create_room_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')

    if request.method == 'POST':
        room_title = request.POST.get('title')
        room_topic = request.POST.get('topic') # 1, 2, 3, 4 중 하나
        
        # Room DB 생성
        new_room = Room.objects.create(
            title=room_title,
            current_topic=int(room_topic) if room_topic else None,
            status=Room.STATUS_STARTED, 
            temperature=10.0
        )
        
        # ✅ 수정 포인트 1: 방을 만든 유저를 이 방의 '방장' 멤버로 자동 등록
        RoomMember.objects.create(
            user=request.user,
            room=new_room,
            is_host=True
        )
        
        # 주소 매핑 규칙에 맞게 리다이렉트 경로 확인 (game 뷰로 바로 쏘거나 subject_select로 전송)
        return redirect('subject_select', room_id=new_room.id)

    return render(request, 'main/home/create_room.html')

@login_required
def subject_select_modal_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')

    room = get_object_or_404(Room, id=room_id)
    current_round = room.rounds.order_by('-round_number').first()

    if current_round is None:
        current_zone = TempEngine.zone_for(room.temperature)
        target_zone = TempEngine.pick_question_zone(current_zone)

        questions = Question.objects.filter(
            topic=room.current_topic, zone=target_zone, is_active=True
        )
        if not questions.exists():
            questions = Question.objects.filter(
                topic=room.current_topic, is_active=True
            )

        if questions.exists():
            selected_q = random.choice(questions)
            current_round = GameRound.objects.create(
                room=room,
                round_number=1,
                question=selected_q,
                question_text=selected_q.text,
                question_zone=selected_q.zone,
                option_a=selected_q.option_a,
                option_b=selected_q.option_b,
                temp_before=room.temperature,
            )
            current_round.start_timer(minutes=5)

    context = {
        'room': room,
        'current_round': current_round,
        'temp_message': TempEngine.message_for(room.temperature),
    }
    return render(request, 'main/home/subject_select_modal.html', context)


def game_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')
    # 1. 주소창에서 넘어온 room_id(UUID)로 방 객체 조회
    room = get_object_or_404(Room, id=room_id)
    
    # ✅ 수정 포인트 2-1: 현재 이 방에 들어와 있는 실시간 멤버 목록(역참조) 및 나 자신 조회
    room_members = room.members.all()
    my_member = room_members.filter(user=request.user).first()
    
    # 만약 유저가 다이렉트 링크를 타고 들어와 멤버에 없다면 참여자로 즉시 등록
    if not my_member:
        my_member = RoomMember.objects.create(
            user=request.user,
            room=room,
            is_host=False
        )
        room_members = room.members.all() # 리스트 리프레시
    
    # 2. 이 방의 가장 최근 라운드 가져오기
    latest_round = room.rounds.order_by('-round_number').first()
    force_next = request.GET.get('next') == '1'

    if not latest_round:
        current_temp = TempEngine.START
        next_round_num = 1
        is_new_round = True
    elif force_next:
        current_temp = TempEngine.next_temp(room.temperature, num_changes=2, num_extensions=0)
        room.temperature = current_temp
        room.save() 
        
        next_round_num = latest_round.round_number + 1
        is_new_round = True
    else:
        current_temp = room.temperature
        is_new_round = False
        current_round = latest_round

    # 3. 새 라운드 생성 및 질문 추출 로직
    if is_new_round:
        current_zone = TempEngine.zone_for(current_temp)
        target_zone = TempEngine.pick_question_zone(current_zone)
        
        questions = Question.objects.filter(
            topic=room.current_topic,  
            zone=target_zone,          
            is_active=True
        )
        
        if questions.exists():
            selected_q = random.choice(questions)
            
            current_round = GameRound.objects.create(
                room=room,
                round_number=next_round_num,
                question=selected_q,
                question_text=selected_q.text,        
                question_zone=target_zone,
                option_a=selected_q.option_a,         
                option_b=selected_q.option_b,         
                temp_before=room.temperature
            )
            current_round.start_timer(minutes=5)       
        else:
            current_round = None

    # ✅ 수정 포인트 2-2: JS 카운트다운 스크립트 연동을 위한 타이머 만료 절대 시각 추출
    expires_at_iso = ""
    if current_round and current_round.expires_at:
        expires_at_iso = current_round.expires_at.isoformat()

    # 4. game.html 템플릿으로 전송할 데이터 바인딩
    context = {
        'room': room,
        'current_temp': current_temp,
        'temp_message': TempEngine.message_for(current_temp),
        'current_round': current_round, 
        
        # ✅ 수정 포인트 2-3: 템플릿 제어를 위한 신규 컨텍스트 추가
        'expires_at_iso': expires_at_iso,     # 타이머용
        'room_members': room_members,         # 참여자 목록용
        'my_member': my_member,               # 본인 프로필 식별용
        'member_count': room_members.count(), # 상단 총 인원수 표시용
    }
    
    return render(request, 'main/game/game.html', context)

@login_required
def ranking_list(request):
    sort_by = request.GET.get('sort', 'temperature')
    
    if sort_by == 'rounds':
        rooms = Room.objects.all().order_by('-rounds', '-temperature')
        active_filter = 'rounds'
    elif sort_by == 'change_rate':
        rooms = Room.objects.all().order_by('-change_rate', '-temperature')
        active_filter = 'change_rate'
    else:
        rooms = Room.objects.all().order_by('-temperature', '-created_at')
        active_filter = 'temperature'
        
    context = {
        'rooms': rooms,
        'active_filter': active_filter,
    }

    return render(request, 'main/ranking/ranking.html', context)
