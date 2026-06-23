import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from .models import Room, RoomMember, GameRound, Question, TempEngine, Vote


def intro_view(request):
    """비로그인 유저에게는 소개 페이지를, 로그인 유저에게는 홈 피드를 제공합니다."""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'main.html')


@login_required
def home_view(request):
    """사용자가 참여 중인 토론방 목록을 생성일 역순으로 나열합니다."""
    rooms = Room.objects.filter(members__user=request.user).distinct().order_by('-created_at')
    
    context = {
        'rooms': rooms,
    }
    return render(request, 'main/home/home.html', context)


@login_required
def create_room_view(request):
    """새로운 토론방을 생성하고 호스트 권한을 부여한 뒤 주제 선택 단계로 이동합니다."""
    if request.method == 'POST':
        room_title = request.POST.get('title')
        room_topic = request.POST.get('topic')  # 1, 2, 3, 4 등 카테고리 ID

        new_room = Room.objects.create(
            title=room_title,
            current_topic=int(room_topic) if room_topic else None,
            status=Room.STATUS_STARTED,
            temperature=10.0
        )

        RoomMember.objects.create(
            user=request.user,
            room=new_room,
            is_host=True
        )

        return redirect('subject_select', room_id=new_room.id)

    return render(request, 'main/home/create_room.html')


@login_required
def subject_select_modal_view(request, room_id):
    """라운드 진입 전 투표 단계입니다. 최초 투표(INITIAL) 여부에 따라 유기적으로 흐름을 제어합니다."""
    room = get_object_or_404(Room, id=room_id)

    my_member, _ = RoomMember.objects.get_or_create(
        user=request.user,
        room=room,
        defaults={'is_host': False},
    )

    current_round = room.rounds.order_by('-round_number').first()

    # 방에 첫 라운드가 없는 경우 1라운드를 동적으로 자동 생성합니다.
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

    # POST 요청: INITIAL 또는 FINAL 단계 투표 처리
    if request.method == 'POST' and current_round:
        side = request.POST.get('side')
        phase = request.POST.get('phase', Vote.Phase.INITIAL)

        valid_sides = {Vote.Side.A, Vote.Side.B}
        valid_phases = {Vote.Phase.INITIAL, Vote.Phase.FINAL}

        if side in valid_sides and phase in valid_phases:
            Vote.objects.update_or_create(
                round=current_round,
                member=my_member,
                phase=phase,
                defaults={'side': side},
            )

            if phase == Vote.Phase.FINAL:
                return redirect('result', room_id=room.id, round_number=current_round.round_number)
            return redirect('game', room_id=room.id)

    # GET 요청: 이미 INITIAL 투표를 마친 인원은 모달을 생략하고 게임방으로 리다이렉트합니다.
    if request.method == 'GET' and current_round and Vote.objects.filter(
        round=current_round, member=my_member, phase=Vote.Phase.INITIAL
    ).exists():
        return redirect('game', room_id=room.id)

    context = {
        'room': room,
        'current_round': current_round,
        'temp_message': TempEngine.message_for(room.temperature),
    }
    return render(request, 'main/home/subject_select_modal.html', context)


@login_required
@require_POST
def extend_timer_view(request, room_id, round_number):
    """비동기 요청을 받아 토론 시간을 5분 연장하고 새 만료 정보를 반환합니다."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    game_round.extend_timer(minutes=5)

    return JsonResponse({
        'expires_at': game_round.expires_at.isoformat(),
        'extensions': game_round.extensions,
    })


@login_required
def game_view(request, room_id):
    """실시간 토론 메인 화면입니다. 강제 다음 라운드 실행(next=1) 및 투표 현황을 집계합니다."""
    room = get_object_or_404(Room, id=room_id)

    room_members = room.members.all()
    my_member = room_members.filter(user=request.user).first()

    if not my_member:
        my_member = RoomMember.objects.create(
            user=request.user,
            room=room,
            is_host=False
        )
        room_members = room.members.all()

    latest_round = room.rounds.order_by('-round_number').first()
    force_next = request.GET.get('next') == '1'

    current_round = None

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

    expires_at_iso = ""
    if current_round and current_round.expires_at:
        expires_at_iso = current_round.expires_at.isoformat()

    # 현재 라운드 실시간 실황 스코어링 (INITIAL 기준 투표 수 산출)
    a_count = 0
    b_count = 0
    my_side = None
    if current_round:
        round_votes = current_round.votes.all()

        initial_votes = round_votes.filter(phase=Vote.Phase.INITIAL)
        a_count = initial_votes.filter(side=Vote.Side.A).count()
        b_count = initial_votes.filter(side=Vote.Side.B).count()

        # 내 투표 성향 추적 (FINAL 우선 반영, 미투표 시 INITIAL 배치)
        my_final = round_votes.filter(member=my_member, phase=Vote.Phase.FINAL).first()
        my_initial = round_votes.filter(member=my_member, phase=Vote.Phase.INITIAL).first()
        my_vote = my_final or my_initial
        if my_vote:
            my_side = my_vote.side

    context = {
        'room': room,
        'current_temp': current_temp,
        'temp_message': TempEngine.message_for(current_temp),
        'current_round': current_round,
        'expires_at_iso': expires_at_iso,
        'room_members': room_members,
        'my_member': my_member,
        'member_count': room_members.count(),
        'a_count': a_count,
        'b_count': b_count,
        'my_side': my_side,
    }

    return render(request, 'main/game/game.html', context)


@login_required
def result_view(request, room_id, round_number):
    """최종 투표 결과를 취합하고, 방 온도 변화 및 누적 토론 진행 시간을 최종 확정(Idempotent 처리)합니다."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    room_members = room.members.all()
    member_count = room_members.count()

    final_votes = game_round.votes.filter(phase=Vote.Phase.FINAL)
    score_a = final_votes.filter(side=Vote.Side.A).count()
    score_b = final_votes.filter(side=Vote.Side.B).count()

    # 인원별 생각 변화 데이터 산출
    changes = game_round.count_changes()

    temp_before = game_round.temp_before
    rise = TempEngine.round_rise(num_changes=changes, num_extensions=game_round.extensions)
    temp_after = round(min(TempEngine.MAX, temp_before + rise), 1)

    # 상태가 PENDING일 때 한 번만 트랜잭션을 처리하여 데이터 오염을 예방합니다.
    if game_round.result_status == 'PENDING':
        elapsed = game_round.finalize_duration()   # 실제 소비 시간 연산 및 저장

        game_round.changes = changes
        game_round.rise = rise
        game_round.temp_after = temp_after
        game_round.change_rate = game_round.compute_change_rate(member_count)
        game_round.result_status = game_round.compute_result_status(member_count)
        game_round.save()

        # 방 도메인 메타데이터 동기화
        room.temperature = temp_after
        room.total_duration += elapsed             # 소요 누적 시간 합산
        room.save()

    # 템플릿 레이어 최적화를 위해 멤버 인스턴스에 직접 동적 애트리뷰트 바인딩
    final_map = {v.member_id: v.side for v in final_votes}
    members_with_side = []
    for m in room_members:
        m.final_side = final_map.get(m.id, '-')
        members_with_side.append(m)

    context = {
        'room': room,
        'current_round': game_round,
        'room_members': members_with_side,
        'member_count': member_count,
        'score_a': score_a,
        'score_b': score_b,
        'changes': changes,
        'extensions': game_round.extensions,
        'temp_before': temp_before,
        'temp_after': temp_after,
        'rise': rise,
    }

    return render(request, 'main/game/result.html', context)


@login_required
def ranking_list(request):
    """정렬 필터 스키마에 따라 방 목록 랭킹을 노출합니다."""
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