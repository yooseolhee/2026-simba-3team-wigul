import random
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.templatetags.static import static
from .models import Room, RoomMember, GameRound, Question, TempEngine, Vote, RoundPhase
from django.db.models import Count, Sum, Max, Value
from django.db.models.functions import Coalesce

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


# ==========================================
# ⭐ 스마트 방 생성 & 대기방 플로우 시작
# ==========================================

@login_required
def create_room_action(request):
    """
    [STEP 1] 홈 화면에서 '방 만들기' 버튼 클릭 시 즉시 껍데기 방을 생성합니다.
    """
    user_profile = getattr(request.user, 'userprofile', None)
    nickname = user_profile.nickname if hasattr(user_profile, 'nickname') else request.user.username

    new_room = Room.objects.create(
        title=f"{nickname}님의 토론방",
        status=Room.STATUS_WAITING,
        temperature=10.0
    )

    RoomMember.objects.create(
        user=request.user,
        room=new_room,
        is_host=True
    )

    return redirect('waiting_room', room_id=new_room.id)


@login_required
def waiting_room_view(request, room_id):
    """
    [STEP 2] 대기방 화면 (QR 코드 및 멤버 리스트 노출, 주제 선택)
    """
    room = get_object_or_404(Room, id=room_id)

    # QR을 찍고 들어온 유저를 멤버로 자동 등록
    my_member, created = RoomMember.objects.get_or_create(
        user=request.user,
        room=room,
        defaults={'is_host': False}
    )
    is_host = my_member.is_host

    if request.method == 'POST':
        if is_host:
            new_title = request.POST.get('title')
            room_topic = request.POST.get('topic')

            if new_title:
                room.title = new_title
                room.save()

            if room_topic:
                room.current_topic = int(room_topic)
                room.status = Room.STATUS_STARTED
                room.save()
                return redirect('subject_select', room_id=room.id)

        return redirect('waiting_room', room_id=room.id)

    room_members = room.members.all()
    absolute_join_url = request.build_absolute_uri()

    context = {
        'room': room,
        'room_id': room.id,
        'room_name': room.title,
        'temperature': room.temperature,
        'room_members': room_members,
        'room_join_url': absolute_join_url,
        'is_host': is_host,
    }
    return render(request, 'main/home/create_room.html', context)


@login_required
def waiting_room_members_api(request, room_id):
    """[polling] 현재 방의 멤버 목록과 방 상태를 JSON으로 반환."""
    room = get_object_or_404(Room, id=room_id)

    members_data = []
    for member in room.members.select_related('user__userprofile'):
        profile = getattr(member.user, 'userprofile', None)
        nickname = profile.nickname if profile else member.user.username
        color = getattr(profile, 'background_color', 'bg-red') if profile else 'bg-red'
        char_key = getattr(profile, 'profile_character', 'wigul_1') if profile else 'wigul_1'

        members_data.append({
            'id': member.id,
            'nickname': nickname,
            'color': color,
            'avatar': static(f'images/{char_key}.png'),
            'is_host': member.is_host,
        })

    return JsonResponse({
        'members': members_data,
        'member_count': len(members_data),
        'status': room.status,
        'started': room.status == Room.STATUS_STARTED,
    })


# ==========================================
# ⭐ 스마트 방 생성 & 대기방 플로우 끝
# ==========================================


def room_detail_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    members = RoomMember.objects.filter(room=room).select_related('user__userprofile')

    context = {
        'room': room,
        'room_members': members,
        'room_join_url': f'/game/{room.id}/',
        'temperature': room.temperature,
    }
    return render(request, 'main/room/detail.html', context)


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


# ==========================================
# ⭐ 방장 전용 라운드 제어 & polling
# ==========================================

def _get_host_member(room, user):
    """해당 유저가 이 방의 방장이면 RoomMember 반환, 아니면 None."""
    member = room.members.filter(user=user).first()
    if member and member.is_host:
        return member
    return None


@login_required
@require_POST
def extend_timer_view(request, room_id, round_number):
    """[방장 전용] 토론 시간을 5분 연장하고 새 만료 정보를 반환합니다."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    if not _get_host_member(room, request.user):
        return JsonResponse({'error': '방장만 연장할 수 있습니다.'}, status=403)

    game_round.extend_timer(minutes=5)

    return JsonResponse({
        'expires_at': game_round.expires_at.isoformat(),
        'extensions': game_round.extensions,
    })


@login_required
@require_POST
def start_voting_view(request, room_id, round_number):
    """[방장 전용] '바로 투표하기' → 라운드를 VOTING 단계로 전환 (DB 저장)."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    if not _get_host_member(room, request.user):
        return JsonResponse({'error': '방장만 시작할 수 있습니다.'}, status=403)

    game_round.go_to_voting()
    return JsonResponse({'phase': game_round.phase})


@login_required
def round_state_api(request, room_id, round_number):
    """[polling] 라운드의 현재 단계·남은시간·표수를 JSON으로 반환."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    initial_votes = game_round.votes.filter(phase=Vote.Phase.INITIAL)
    a_count = initial_votes.filter(side=Vote.Side.A).count()
    b_count = initial_votes.filter(side=Vote.Side.B).count()

    return JsonResponse({
        'phase': game_round.phase,
        'remaining': game_round.get_remaining_seconds(),
        'expires_at': game_round.expires_at.isoformat() if game_round.expires_at else '',
        'extensions': game_round.extensions,
        'a_count': a_count,
        'b_count': b_count,
        'member_count': room.members.count(),
    })

@login_required
@require_POST
def final_vote_view(request, room_id, round_number):
    """[AJAX] 최종 투표를 DB에 저장만 한다. 이동은 polling이 판단."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)
    my_member = room.members.filter(user=request.user).first()

    side = request.POST.get('side')
    if side in {Vote.Side.A, Vote.Side.B} and my_member:
        Vote.objects.update_or_create(
            round=game_round,
            member=my_member,
            phase=Vote.Phase.FINAL,
            defaults={'side': side},
        )

    final_count = game_round.votes.filter(phase=Vote.Phase.FINAL).count()
    member_count = room.members.count()
    return JsonResponse({
        'voted': final_count,
        'total': member_count,
        'all_done': final_count >= member_count,
    })


@login_required
def final_status_api(request, room_id, round_number):
    """[polling] 모두 FINAL 투표를 마쳤는지 확인."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    final_count = game_round.votes.filter(phase=Vote.Phase.FINAL).count()
    member_count = room.members.count()
    return JsonResponse({
        'voted': final_count,
        'total': member_count,
        'all_done': final_count >= member_count,
    })


@login_required
def game_view(request, room_id):
    """QR 접속 시 방장/팀원 정체 판별, 방장 강제 진행 보안 등을 관장하는 메인 게임 뷰"""
    room = get_object_or_404(Room, id=room_id)

    room_members = room.members.all()
    my_member = room_members.filter(user=request.user).first()

    if not my_member:
        is_this_user_host = (room.host and room.host.user == request.user)
        my_member = RoomMember.objects.create(
            user=request.user,
            room=room,
            is_host=is_this_user_host
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
        if my_member.is_host:
            current_temp = TempEngine.next_temp(room.temperature, num_changes=2, num_extensions=0)
            room.temperature = current_temp
            room.save()
            next_round_num = latest_round.round_number + 1
            is_new_round = True
        else:
            current_temp = room.temperature
            is_new_round = False
            current_round = latest_round
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

        if not questions.exists():
            questions = Question.objects.filter(
                topic=room.current_topic,
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

    a_count, b_count, my_side = 0, 0, None
    if current_round:
        round_votes = current_round.votes.all()
        initial_votes = round_votes.filter(phase=Vote.Phase.INITIAL)
        a_count = initial_votes.filter(side=Vote.Side.A).count()
        b_count = initial_votes.filter(side=Vote.Side.B).count()

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
        'is_host': my_member.is_host,
        'member_count': room_members.count(),
        'a_count': a_count,
        'b_count': b_count,
        'my_side': my_side,
    }

    return render(request, 'main/game/game.html', context)


@login_required
def result_view(request, room_id, round_number):
    """최종 투표 결과를 취합하고 방 온도를 동기화합니다."""
    room = get_object_or_404(Room, id=room_id)
    game_round = get_object_or_404(GameRound, room=room, round_number=round_number)

    room_members = room.members.all()
    member_count = room_members.count()

    final_votes = game_round.votes.filter(phase=Vote.Phase.FINAL)
    score_a = final_votes.filter(side=Vote.Side.A).count()
    score_b = final_votes.filter(side=Vote.Side.B).count()

    changes = game_round.count_changes()

    temp_before = game_round.temp_before
    rise = TempEngine.round_rise(num_changes=changes, num_extensions=game_round.extensions)
    temp_after = round(min(TempEngine.MAX, temp_before + rise), 1)

    if game_round.result_status == 'PENDING':
        elapsed = game_round.finalize_duration()

        game_round.changes = changes
        game_round.rise = rise
        game_round.temp_after = temp_after
        game_round.change_rate = game_round.compute_change_rate(member_count)
        game_round.result_status = game_round.compute_result_status(member_count)
        game_round.phase = RoundPhase.FINISHED  # 결과 확정 시 라운드 종료 마킹
        game_round.save()

        room.temperature = temp_after
        room.total_duration += elapsed
        room.save()

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
def ranking_view(request):
    # 1. 쿼리셋 준비
    # total_duration은 모델에 있으므로 annotate에서 제외하고, 
    # 나머지 계산이 필요한 값들만 별칭(alias)을 다르게 지정합니다.
    rooms_qs = Room.objects.annotate(
        round_count=Count('rounds'),
        sum_changes=Coalesce(Sum('rounds__changes'), Value(0))
    )
    
    # 2. 각 정렬 기준별 상위 10개 추출
    # temp_ranking은 모델 필드(temperature) 그대로 사용
    temp_ranking = rooms_qs.order_by('-temperature')[:10]
    
    # round_count는 annotate한 별칭 사용
    round_ranking = rooms_qs.order_by('-round_count')[:10]
    
    # total_duration은 모델 필드 그대로 사용 (가장 효율적!)
    time_ranking = rooms_qs.order_by('-total_duration')[:10]
    
    # sum_changes는 annotate한 별칭 사용
    change_ranking = rooms_qs.order_by('-sum_changes')[:10]
    
    # 3. 내 방 순위 계산 (온도 기준 예시)
    my_room_ranking = None
    my_room_ids = RoomMember.objects.filter(
        user=request.user
        ).values_list('room_id', flat=True)
    
    my_rooms_qs = rooms_qs.filter(id__in=my_room_ids)

    my_temp_ranking = my_rooms_qs.order_by('-temperature')
    my_round_ranking = my_rooms_qs.order_by('-round_count')
    my_time_ranking = my_rooms_qs.order_by('-total_duration')
    my_change_ranking = my_rooms_qs.order_by('-sum_changes')
    
    
    all_temp_rooms = list(rooms_qs.order_by('-temperature'))
    
    for index, room_item in enumerate(all_temp_rooms):
        if room_item.id in my_room_ids:
            my_room_ranking = {
                'room': room_item,
                'rank': index + 1,
                'type': 'temperature'
            }
            break
            
    context = {
        'temp_ranking': temp_ranking,
        'round_ranking': round_ranking,
        'time_ranking': time_ranking,
        'change_ranking': change_ranking,
        'my_room_ranking': my_room_ranking,
        'my_temp_ranking': my_temp_ranking,
        'my_round_ranking': my_round_ranking,
        'my_time_ranking': my_time_ranking,
        'my_change_ranking': my_change_ranking,
        'tabs_config': [
            ('temp', temp_ranking, '°C', 'ranking-temp'),
            ('round', round_ranking, '회', 'ranking-max-round'),
            ('time', time_ranking, '시간', 'ranking-max-time'), # 유닛 이름을 명시
            ('change', change_ranking, '회', 'ranking-max-change'),
        ]
    }
    
    return render(request, 'main/ranking/ranking.html', context)

@login_required
def myroom_list_view(request):
    rooms = Room.objects.filter(members__user=request.user).distinct().order_by('-created_at')

    for room in rooms:
        room_members_data = []
        for member in room.members.select_related('user__userprofile'):
            profile = member.user.userprofile
            room_members_data.append({
                'nickname': profile.nickname,
                'color': getattr(profile, 'background_color', 'bg-red'),
                'avatar': getattr(profile, 'profile_character', 'wigul_1.png'),
            })
        room.member_profiles = room_members_data

    return render(request, 'main/myroom/myroom_list.html', {'rooms': rooms})


@login_required
def myroom_view(request):
    return render(request, 'main/myroom/myroom_list.html')


@login_required
def myroom_detail_view(request):
    return render(request, 'main/myroom/myroom_detail.html')