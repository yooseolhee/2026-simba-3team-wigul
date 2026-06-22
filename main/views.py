import random
from django.shortcuts import render, redirect, get_object_or_404

# app 이름에 맞춰 models 경로를 수정해 주세요. (예: from .models import Room, ...)
from .models import Room, GameRound, Question, TempEngine

def intro_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'main.html')

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')
    return render(request, 'main/home/home.html')

def create_room_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')

    # 프론트엔드 폼에서 넘어온 POST 데이터를 처리
    if request.method == 'POST':
        room_title = request.POST.get('title')
        room_topic = request.POST.get('topic') # 1, 2, 3, 4 중 하나
        
        # Room DB 생성 (여기서 UUID가 자동으로 생성됩니다!)
        new_room = Room.objects.create(
            title=room_title,
            current_topic=int(room_topic) if room_topic else None,
            status=Room.STATUS_STARTED, # 게임 시작 상태로 변경
            temperature=10.0
        )
        
        # DB에 방이 생성되었으므로, 해당 방의 고유 UUID를 가지고 게임 뷰로 리다이렉트
        return redirect('subject_select', room_id=new_room.id)
    # GET 요청 시 껍데기 화면 렌더링
    return render(request, 'main/home/create_room.html')

def subject_select_modal_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')

    room = get_object_or_404(Room, id=room_id)

    # 이미 1라운드가 있으면 재사용, 없으면 첫 질문을 뽑아서 생성
    current_round = room.rounds.order_by('-round_number').first()

    if current_round is None:
        current_zone = TempEngine.zone_for(room.temperature)
        target_zone = TempEngine.pick_question_zone(current_zone)

        questions = Question.objects.filter(
            topic=room.current_topic, zone=target_zone, is_active=True
        )
        if not questions.exists():
            # 뽑힌 zone에 질문이 없으면 같은 topic 전체에서 fallback
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

# ==========================================
# 핵심 수정: game_view에 room_id 파라미터 추가
# ==========================================
def game_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')
    # 1. 주소창에서 넘어온 room_id(UUID)로 방 객체 조회
    room = get_object_or_404(Room, id=room_id)
    
    # 2. 이 방의 가장 최근 라운드 가져오기
    latest_round = room.rounds.order_by('-round_number').first()
    
    # [테스트용] URL 끝에 ?next=1 이 붙어있으면 강제로 다음 라운드로 진행시킴
    force_next = request.GET.get('next') == '1'

    if not latest_round:
        # 방을 새로 만들고 처음 진입했을 때 (1라운드 세팅)
        current_temp = TempEngine.START
        next_round_num = 1
        is_new_round = True
    elif force_next:
        # 강제 라운드 전환 및 온도 상승 시뮬레이션
        current_temp = TempEngine.next_temp(room.temperature, num_changes=2, num_extensions=0)
        room.temperature = current_temp
        room.save() # 방 온도 변동 사항 DB 저장
        
        next_round_num = latest_round.round_number + 1
        is_new_round = True
    else:
        # 그냥 새로고침을 누른 경우 현재 라운드 유지
        current_temp = room.temperature
        is_new_round = False
        current_round = latest_round

    # 3. 새 라운드 생성 및 질문 추출 로직
    if is_new_round:
        # 현재 온도에 맞는 구역(Zone: GREEN, YELLOW, PINK) 판별
        current_zone = TempEngine.zone_for(current_temp)
        # TempEngine 가중치에 따라 최종 타겟 질문 구역 추첨
        target_zone = TempEngine.pick_question_zone(current_zone)
        
        # ✅ 핵심 수정: 원래 Question 모델 필드명인 'topic'과 'zone'으로 정확히 필터링
        questions = Question.objects.filter(
            topic=room.current_topic,  # 방 만들 때 모달에서 고른 주제 번호 (1~4)
            zone=target_zone,          # 추첨된 난이도 구역 (GREEN/YELLOW/PINK)
            is_active=True
        )
        
        if questions.exists():
            # 조건에 맞는 질문 풀 중에서 하나를 랜덤 선택
            selected_q = random.choice(questions)
            
            # GameRound 생성 및 데이터 스냅샷 저장
            current_round = GameRound.objects.create(
                room=room,
                round_number=next_round_num,
                question=selected_q,
                question_text=selected_q.text,        # Question.text 복사
                question_zone=target_zone,
                option_a=selected_q.option_a,         # Question.option_a 복사
                option_b=selected_q.option_b,         # Question.option_b 복사
                temp_before=room.temperature
            )
            current_round.start_timer(minutes=5)       # 5분 타이머 활성화
        else:
            # 💡 중요: 만약 화면이 빈칸으로 나온다면 이 구역으로 빠진 것입니다.
            # 데이터베이스 main_question 테이블에 현재 topic 번호와 zone에 일치하는 행이 없다는 의미입니다.
            current_round = None

    # 4. game.html 템플릿으로 전송할 데이터 바인딩
    context = {
        'room': room,
        'current_temp': current_temp,
        'temp_message': TempEngine.message_for(current_temp),
        'current_round': current_round, # html의 {% if current_round %} 검증 통과용
    }
    
    return render(request, 'main/game/game.html', context)
