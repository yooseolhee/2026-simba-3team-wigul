import random
import uuid

from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User


class Room(models.Model):
    """
    토론방 도메인 모델. 
    대기방(WAITING) 상태에서 생성되어 QR 코드로 팀원을 모집한 뒤, 
    주제가 선택되면 게임 진행(STARTED) 상태로 전환됩니다.
    """

    STATUS_WAITING = "waiting"
    STATUS_STARTED = "started"
    STATUS_TOPIC = "topic_selected"
    STATUS_CHOICES = [
        (STATUS_WAITING, "대기중"),
        (STATUS_STARTED, "시작됨"),
        (STATUS_TOPIC, "주제선택됨"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    temperature = models.FloatField(default=10.0)
    total_rounds = models.IntegerField(default=100)

    # 방 전체 누적 소비 시간 (초 단위 저장)
    total_duration = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING
    )
    current_topic = models.IntegerField("선택된 주제", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def host(self):
        """이 방의 방장(Host) RoomMember 객체를 반환합니다."""
        return self.members.filter(is_host=True).first()

    @property
    def duration_display(self):
        """
        초 단위로 저장된 total_duration을 템플릿에서 보기 좋게 변환합니다.
        사용 예: {{ room.duration_display }} -> '3분 15초'
        """
        minutes = self.total_duration // 60
        seconds = self.total_duration % 60
        if minutes == 0:
            return f"{seconds}초"
        return f"{minutes}분 {seconds}초"


class RoomMember(models.Model):
    """방에 입장한 개별 사용자 권한 매핑 테이블 (방장/일반 팀원 구분)"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, related_name="members", on_delete=models.CASCADE)
    is_host = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "room")
        ordering = ["joined_at"]

    def __str__(self):
        role = "방장" if self.is_host else "참여자"
        return f"{self.user.username} - {self.room.title} [{role}]"


class Inquiry(models.Model):
    """1:1 문의 게시판"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user.username}] {self.title}"


class Zone(models.TextChoices):
    GREEN = "GREEN", "초록 (10~33)"
    YELLOW = "YELLOW", "노랑 (34~66)"
    PINK = "PINK", "핑크 (67~100)"


TOPIC_CHOICES = [
    (1, "사랑과 연애"),
    (2, "취향과 라이프스타일"),
    (3, "최악의 상황은"),
    (4, "갓생과 일"),
]


class TempEngine:
    """온도 증감폭 및 구역별 질문 가중치를 관장하는 프레임워크 무관 순수 계산 엔진"""

    START = 10.0
    COMPLETION = 25.0
    PER_CHANGE = 5.0
    PER_EXTENSION = 2.0
    EXTENSION_CAP = 10.0
    MAX = 100.0

    GREEN_MAX = 34
    YELLOW_MAX = 67

    QUESTION_WEIGHTS = {
        Zone.GREEN:  [(Zone.GREEN, 70), (Zone.YELLOW, 25), (Zone.PINK, 5)],
        Zone.YELLOW: [(Zone.GREEN, 20), (Zone.YELLOW, 65), (Zone.PINK, 15)],
        Zone.PINK:   [(Zone.GREEN, 15), (Zone.YELLOW, 15), (Zone.PINK, 70)],
    }

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
        buckets, weights = zip(*cls.QUESTION_WEIGHTS[level])
        return random.choices(buckets, weights=weights, k=1)[0]


class Question(models.Model):
    """토론 질문 메타데이터. A/B 선택지 포함."""

    topic = models.IntegerField(choices=TOPIC_CHOICES)
    zone = models.CharField(max_length=6, choices=Zone.choices)
    text = models.TextField()
    option_a = models.CharField(max_length=120)
    option_b = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["topic", "zone", "is_active"])]

    def __str__(self):
        return f"[{self.get_topic_display()}·{self.get_zone_display()}] {self.text[:24]}"


class ResultStatus(models.TextChoices):
    PENDING = "PENDING", "진행/미완"
    MATCHED = "MATCHED", "의견 일치"
    UNMATCHED = "UNMATCHED", "의견 갈림"


class RoundPhase(models.TextChoices):
    """라운드 진행 단계. 방장의 버튼 조작과 팀원의 polling을 잇는 다리."""
    DISCUSSION = "DISCUSSION", "토론중"      # 타이머가 돌아가는 토론 단계
    VOTING = "VOTING", "최종투표중"          # 방장이 '바로 투표하기'를 눌러 최종 투표 진입
    FINISHED = "FINISHED", "종료"           # 결과 확정 완료


class GameRound(models.Model):
    """개별 라운드의 전적, 투표 결과 및 시간 흐름을 기록하는 엔티티"""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="rounds")
    round_number = models.IntegerField()
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="rounds")

    question_text = models.TextField()
    question_zone = models.CharField(max_length=6, choices=Zone.choices)
    option_a = models.CharField(max_length=120, default="A")
    option_b = models.CharField(max_length=120, default="B")

    changes = models.IntegerField(default=0)
    extensions = models.IntegerField(default=0)
    rise = models.FloatField(default=0)
    temp_before = models.FloatField(default=0)
    temp_after = models.FloatField(default=0)
    change_rate = models.FloatField(default=0)

    result_status = models.CharField(
        max_length=10, choices=ResultStatus.choices, default=ResultStatus.PENDING
    )

    # 라운드 진행 단계 (polling 기반 실시간 동기화의 핵심 필드)
    phase = models.CharField(
        max_length=10, choices=RoundPhase.choices, default=RoundPhase.DISCUSSION
    )

    duration = models.PositiveIntegerField(default=0)      # 실제 소요된 초 단위 시간
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["room", "round_number"]
        unique_together = ("room", "round_number")

    def __str__(self):
        return f"{self.room.title} R{self.round_number}"

    def start_timer(self, minutes=5):
        """라운드 시작 시 지정된 분(minutes)만큼 타이머 세팅"""
        self.expires_at = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['expires_at'])

    def extend_timer(self, minutes=5):
        """연장 버튼 클릭 시 마감 시각을 늦추고 연장 횟수 증가"""
        if self.expires_at:
            self.expires_at += timedelta(minutes=minutes)
            self.extensions += 1
            self.save(update_fields=['expires_at', 'extensions'])

    def go_to_voting(self):
        """[방장 전용] '바로 투표하기' → 토론 종료 + 최종 투표 단계 진입 (DB 저장)."""
        if self.phase == RoundPhase.DISCUSSION:
            self.phase = RoundPhase.VOTING
            self.expires_at = timezone.now()  # 남은 타이머 즉시 0으로 만료
            self.save(update_fields=['phase', 'expires_at'])

    def get_remaining_seconds(self):
        """현재 시각 기준 남은 시간(초)을 동적으로 계산"""
        if not self.expires_at:
            return 0
        now = timezone.now()
        if now >= self.expires_at:
            return 0
        return int((self.expires_at - now).total_seconds())

    def finalize_duration(self):
        """라운드 종료 시 started_at부터 지금까지 흐른 시간을 duration에 영구 저장"""
        if self.ended_at is None:
            self.ended_at = timezone.now()
        elapsed = int((self.ended_at - self.started_at).total_seconds())
        self.duration = elapsed
        self.save(update_fields=['duration', 'ended_at'])
        return elapsed

    def live_sides(self):
        """가장 최신 단계(FINAL > MID > INITIAL)의 투표 성향을 산출"""
        priority = {Vote.Phase.INITIAL: 0, Vote.Phase.MID: 1, Vote.Phase.FINAL: 2}
        best = {}
        for v in self.votes.all():
            p = priority[v.phase]
            if v.member_id not in best or p >= best[v.member_id][0]:
                best[v.member_id] = (p, v.side)
        return {mid: side for mid, (_, side) in best.items()}

    def count_changes(self):
        """멤버별로 INITIAL -> MID -> FINAL 사이의 의견 변동 횟수를 합산"""
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
    """특정 라운드, 특정 멤버의 개별 투표 데이터를 기록합니다."""

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
        unique_together = ("round", "member", "phase")

    def __str__(self):
        return f"{self.round} · {self.member.user.username} · {self.phase} → {self.side}"