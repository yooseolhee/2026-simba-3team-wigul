import random
import uuid

from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User


# =====================================================================
# 기존 모델 (Room / RoomMember / Inquiry) — 변경 없음
# =====================================================================
class Room(models.Model):
    """방 한 개. 흐름도의 '공유 상태(DB)'에 해당합니다."""

    STATUS_WAITING = "waiting"        # 대기방, 아직 시작 전
    STATUS_STARTED = "started"        # 시작됨 → 주제 선택 페이지
    STATUS_TOPIC = "topic_selected"   # 주제가 정해짐
    STATUS_CHOICES = [
        (STATUS_WAITING, "대기중"),
        (STATUS_STARTED, "시작됨"),
        (STATUS_TOPIC, "주제선택됨"),
    ]

    # 랜덤 고유 아이디 = 방의 PK. 방 만들기 버튼을 누르면 자동 생성됩니다.
    # (QR/공유 링크에 이 id가 들어갑니다)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    temperature = models.FloatField(default=10)
    total_rounds = models.IntegerField(default=100)

    # 방 진행 상태와 방장이 고른 주제(1~4). 아직 안 골랐으면 None.
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING
    )
    current_topic = models.IntegerField("선택된 주제", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def host(self):
        """이 방의 방장(RoomMember)을 돌려준다. 없으면 None."""
        return self.members.filter(is_host=True).first()


class RoomMember(models.Model):
    """방에 들어온 사람 한 명. 방장/참여자 권한을 is_host로 구분합니다."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, related_name="members", on_delete=models.CASCADE)
    # 방장 여부 = 권한. 주제 선택은 is_host=True 만 가능.
    is_host = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        # 같은 사람이 같은 방에 두 번 들어가지 못하게 막음
        unique_together = ("user", "room")
        ordering = ["joined_at"]

    def __str__(self):
        role = "방장" if self.is_host else "참여자"
        return f"{self.user.username} - {self.room.title} [{role}]"


class Inquiry(models.Model):
    """1:1 문의 게시판."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user.username}] {self.title}"


# =====================================================================
# 온도 게임 모델 (추가분)
#
# game.html 기준 온도/질문 로직
#   시작 온도 = 10.0  (게임 시작 시 Room.temperature 를 10 으로 초기화)
#   구역      = Green 10~33 / Yellow 34~66 / Pink 67~100   (경계 34, 67)
#   상승분    = 1.0(완료) + 0.3 × 변경건수 + min(0.5 × 연장횟수, 1.0)
#             └ 연장 3회 이상이어도 +1.0 고정 (어뷰징 방지)
#   질문 출현율(가중치 추첨) — '질문별 출현율' 팝업과 동일
# =====================================================================
class Zone(models.TextChoices):
    GREEN = "GREEN", "초록 (10~33)"
    YELLOW = "YELLOW", "노랑 (34~66)"
    PINK = "PINK", "핑크 (67~100)"


# Room.current_topic(정수 1~4)에 맞춘 주제 라벨
TOPIC_CHOICES = [
    (1, "사랑과 연애"),
    (2, "취향과 라이프스타일"),
    (3, "최악의 상황은"),
    (4, "갓생과 일"),
]


class TempEngine:
    """프레임워크 무관 순수 계산. (Room.temperature 는 FloatField → float 사용)"""

    START = 10.0
    # 테스트용: 라운드 하나 끝날 때마다 온도가 25도씩 확 오르게 설정
    COMPLETION = 25.0 
    PER_CHANGE = 5.0
    PER_EXTENSION = 2.0
    EXTENSION_CAP = 10.0
    MAX = 100.0

    GREEN_MAX = 34        # [10, 34)  초록
    YELLOW_MAX = 67       # [34, 67)  노랑,  [67, 100] 핑크

    # 온도 레벨별 질문 난이도 출현 가중치 (game.html 팝업과 동일)
    QUESTION_WEIGHTS = {
        Zone.GREEN:  [(Zone.GREEN, 70), (Zone.YELLOW, 25), (Zone.PINK, 5)],
        Zone.YELLOW: [(Zone.GREEN, 20), (Zone.YELLOW, 65), (Zone.PINK, 15)],
        Zone.PINK:   [(Zone.GREEN, 15), (Zone.YELLOW, 15), (Zone.PINK, 70)],
    }

    # 구역별 안내 문구 (room-temp-subtitle). 자유롭게 수정하세요.
    MESSAGES = {
        Zone.GREEN: "더 많은 대화가 필요해요!",
        Zone.YELLOW: "대화가 무르익고 있어요!",
        Zone.PINK: "대화가 후끈 달아올랐어요!",
    }

    @classmethod
    def round_rise(cls, num_changes, num_extensions):
        change = cls.PER_CHANGE * num_changes
        ext = min(cls.PER_EXTENSION * num_extensions, cls.EXTENSION_CAP)
        return round(cls.COMPLETION + change + ext, 1)

    @classmethod
    def next_temp(cls, current, num_changes, num_extensions):
        rise = cls.round_rise(num_changes, num_extensions)
        return round(min(cls.MAX, current + rise), 1)

    @classmethod
    def zone_for(cls, temp):
        """온도 → 레벨(Zone)."""
        if temp < cls.GREEN_MAX:
            return Zone.GREEN
        if temp < cls.YELLOW_MAX:
            return Zone.YELLOW
        return Zone.PINK

    @classmethod
    def message_for(cls, temp):
        return cls.MESSAGES[cls.zone_for(temp)]

    @classmethod
    def pick_question_zone(cls, level):
        """현재 온도 레벨의 가중치로 '질문 난이도 버킷'을 추첨."""
        buckets, weights = zip(*cls.QUESTION_WEIGHTS[level])
        return random.choices(buckets, weights=weights, k=1)[0]


class Question(models.Model):
    """토픽(1~4) × 난이도 구역(초록/노랑/핑크) 버킷. A/B 선택지 텍스트 포함."""

    topic = models.IntegerField(choices=TOPIC_CHOICES)      # Room.current_topic 와 매칭
    zone = models.CharField(max_length=6, choices=Zone.choices)  # 난이도 버킷
    text = models.TextField()                               # 주제 질문
    option_a = models.CharField(max_length=120)            # A 선택지 (예: 일주일에 5번…)
    option_b = models.CharField(max_length=120)            # B 선택지 (예: 한 달에 한 번…)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["topic", "zone", "is_active"])]

    def __str__(self):
        return f"[{self.get_topic_display()}·{self.get_zone_display()}] {self.text[:24]}"


class ResultStatus(models.TextChoices):
    PENDING = "PENDING", "진행/미완"
    MATCHED = "MATCHED", "의견 일치"
    UNMATCHED = "UNMATCHED", "의견 갈림"


class GameRound(models.Model):
    """라운드 전적. 기존 Room 을 FK 참조 (Room 자체는 수정하지 않음)."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="rounds")
    round_number = models.IntegerField()                   # R1, R2 ...
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="rounds")

    # 출제 시점 스냅샷 (질문이 나중에 수정/비활성화돼도 전적은 보존)
    question_text = models.TextField()
    question_zone = models.CharField(max_length=6, choices=Zone.choices)  # 뽑힌 난이도 버킷
    option_a = models.CharField(max_length=120, default="A")
    option_b = models.CharField(max_length=120, default="B")

    # 집계
    changes = models.IntegerField(default=0)
    extensions = models.IntegerField(default=0)
    rise = models.FloatField(default=0)
    temp_before = models.FloatField(default=0)
    temp_after = models.FloatField(default=0)
    change_rate = models.FloatField(default=0)

    result_status = models.CharField(
        max_length=10, choices=ResultStatus.choices, default=ResultStatus.PENDING
    )
    duration = models.PositiveIntegerField(default=0)      # 초 단위
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    # ✅ 핵심 추가: 이 라운드의 타이머가 0이 되는 절대 시각 (기준점)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["room", "round_number"]
        unique_together = ("room", "round_number")

    def __str__(self):
        return f"{self.room.title} R{self.round_number}"
    
    # ==========================================
    # ✅ 추가: 타이머 제어 및 계산 헬퍼 메서드
    # ==========================================
    def start_timer(self, minutes=5):
        """라운드 시작 시 5분 타이머 세팅"""
        self.expires_at = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['expires_at'])

    def extend_timer(self, minutes=5):
        """5분 연장 버튼 클릭 시: 마감 시각을 뒤로 미루고 연장 횟수 증가"""
        if self.expires_at:
            self.expires_at += timedelta(minutes=minutes)
            self.extensions += 1
            self.save(update_fields=['expires_at', 'extensions'])

    def get_remaining_seconds(self):
        """현재 시각 기준으로 남은 시간(초) 계산"""
        if not self.expires_at:
            return 0
        
        now = timezone.now()
        if now >= self.expires_at:
            return 0
            
        return int((self.expires_at - now).total_seconds())

    # ----- 현재 라이브 사이드: 멤버별 가장 최근 단계의 표 (2:2 점수 표시용) -----
    def live_sides(self):
        priority = {Vote.Phase.INITIAL: 0, Vote.Phase.MID: 1, Vote.Phase.FINAL: 2}
        best = {}  # member_id -> (priority, side)
        for v in self.votes.all():
            p = priority[v.phase]
            if v.member_id not in best or p >= best[v.member_id][0]:
                best[v.member_id] = (p, v.side)
        return {mid: side for mid, (_, side) in best.items()}

    # ----- 변경 집계: 초기→중간→결과 순서로 마음 바꾼 횟수 (멤버당 최대 2회) -----
    def count_changes(self):
        order = [Vote.Phase.INITIAL, Vote.Phase.MID, Vote.Phase.FINAL]
        by_member = {}
        for v in self.votes.all():
            by_member.setdefault(v.member_id, {})[v.phase] = v.side
        total = 0
        for sides in by_member.values():
            seq = [sides[p] for p in order if p in sides]
            total += sum(1 for a, b in zip(seq, seq[1:]) if a != b)
        return total

    def compute_change_rate(self, member_count):
        """변화율 = 실제 변경 / (인원 × 2단계). 분모 정의는 조정 가능."""
        max_changes = member_count * 2
        return round(self.changes / max_changes * 100, 1) if max_changes else 0.0

    def compute_result_status(self, member_count):
        finals = list(
            self.votes.filter(phase=Vote.Phase.FINAL).values_list("side", flat=True)
        )
        if not finals or len(finals) < member_count:
            return ResultStatus.PENDING
        return ResultStatus.MATCHED if len(set(finals)) == 1 else ResultStatus.UNMATCHED


class Vote(models.Model):
    """(라운드 × RoomMember × 단계) 마다 한 행.

    game.html 토글 매핑:
        라운드 시작 후 첫 선택        → phase=INITIAL
        타이머 중반 이후 토글         → phase=MID   (변경 집계 ①)
        '바로 투표하기'/시간종료 직전 → phase=FINAL (변경 집계 ②)
    """

    class Phase(models.TextChoices):
        INITIAL = "INITIAL", "초기 투표"
        MID = "MID", "중간 투표"
        FINAL = "FINAL", "결과 투표"

    class Side(models.TextChoices):
        A = "A", "A"
        B = "B", "B"

    round = models.ForeignKey(GameRound, on_delete=models.CASCADE, related_name="votes")
    member = models.ForeignKey(RoomMember, on_delete=models.CASCADE, related_name="votes")
    phase = models.CharField(max_length=7, choices=Phase.choices)
    side = models.CharField(max_length=1, choices=Side.choices)
    voted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("round", "member", "phase")  # 단계당 1표 (재투표 시 갱신)

    def __str__(self):
        return f"{self.round} · {self.member.user.username} · {self.phase} → {self.side}"