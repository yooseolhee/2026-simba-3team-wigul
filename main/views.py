import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Room, RoomMember, GameRound, Question, TempEngine, Vote


def intro_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'main.html')


@login_required
def home_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')

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
        room_topic = request.POST.get('topic')  # 1, 2, 3, 4 중 하나

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

        # 방 생성 후 select 모달 페이지로
        return redirect('subject_select', room_id=new_room.id)

    return render(request, 'main/home/create_room.html')


@login_required
def subject_select_modal_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')

    room = get_object_or_404(Room, id=room_id)

    my_member, _ = RoomMember.objects.get_or_create(
        user=request.user,
        room=room,
        defaults={'is_host': False},
    )

    current_round = room.rounds.order_by('-round_number').first()

    # 라운드 없으면 1라운드 생성
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

    # ★★★ POST: INITIAL / FINAL 둘 다 여기서 처리 (다른 분기보다 먼저!) ★★★
    if request.method == 'POST' and current_round:
        side = request.POST.get('side')
        phase = request.POST.get('phase', Vote.Phase.INITIAL)

        valid_sides = {Vote.Side.A, Vote.Side.B}
        valid_phases = {Vote.Phase.INITIAL, Vote.Phase.FINAL}  # MID 제거

        if side in valid_sides and phase in valid_phases:
            Vote.objects.update_or_create(
                round=current_round,
                member=my_member,
                phase=phase,
                defaults={'side': side},
            )

            # FINAL이면 결과 페이지로, INITIAL이면 game으로
            if phase == Vote.Phase.FINAL:
                return redirect('result', room_id=room.id,
                                round_number=current_round.round_number)
            return redirect('game', room_id=room.id)

    # GET: 이미 INITIAL 투표한 사람은 select 모달 건너뛰고 game으로
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
def game_view(request, room_id):
    if not request.user.is_authenticated:
        return redirect('intro')

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

    # 현재 라운드 투표 집계
    a_count = 0
    b_count = 0
    my_side = None
    if current_round:
        round_votes = current_round.votes.all()

        # 점수는 INITIAL 기준
        initial_votes = round_votes.filter(phase=Vote.Phase.INITIAL)
        a_count = initial_votes.filter(side=Vote.Side.A).count()
        b_count = initial_votes.filter(side=Vote.Side.B).count()

        # 내 표는 FINAL 우선, 없으면 INITIAL
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
    if not request.user.is_authenticated:
        return redirect('intro')

    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    room_members = room.members.all()
    member_count = room_members.count()

    # FINAL 기준 점수 집계
    final_votes = game_round.votes.filter(phase=Vote.Phase.FINAL)
    score_a = final_votes.filter(side=Vote.Side.A).count()
    score_b = final_votes.filter(side=Vote.Side.B).count()

    # 의견 변화 횟수 (models.py 헬퍼: INITIAL→FINAL 비교)
    changes = game_round.count_changes()

    # 온도 계산
    temp_before = game_round.temp_before
    rise = TempEngine.round_rise(num_changes=changes, num_extensions=game_round.extensions)
    temp_after = round(min(TempEngine.MAX, temp_before + rise), 1)

    # 라운드 결과 확정 (PENDING일 때 한 번만)
    if game_round.result_status == 'PENDING':
        game_round.changes = changes
        game_round.rise = rise
        game_round.temp_after = temp_after
        game_round.change_rate = game_round.compute_change_rate(member_count)
        game_round.result_status = game_round.compute_result_status(member_count)
        game_round.save()

        # 방 온도 갱신
        room.temperature = temp_after
        room.save()

    # 멤버별 최종 사이드를 멤버 객체에 직접 붙이기 (템플릿에서 dict 조회 회피)
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