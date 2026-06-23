from django.contrib import admin

from .models import Room, RoomMember, Question, GameRound, Vote


# =====================================================================
# Question — 시드 데이터를 '여기서' 입력하게 될 핵심 화면
# =====================================================================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    # 목록에 보이는 열
    list_display = ('id', 'topic', 'zone', 'short_text', 'option_a', 'option_b', 'is_active')
    # 오른쪽 필터 (토픽·구역별로 몇 개 넣었는지 한눈에 확인)
    list_filter = ('topic', 'zone', 'is_active')
    # 검색창
    search_fields = ('text', 'option_a', 'option_b')
    # 목록에서 바로 체크 토글 (페이지 안 들어가고 활성/비활성)
    list_editable = ('is_active',)
    list_per_page = 50

    @admin.display(description='질문')
    def short_text(self, obj):
        return obj.text[:30]


# =====================================================================
# GameRound — 라운드 전적(읽기 위주). 안에 투표를 같이 펼쳐 봄
# =====================================================================
class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    can_delete = False
    readonly_fields = ('member', 'phase', 'side', 'voted_at')


@admin.register(GameRound)
class GameRoundAdmin(admin.ModelAdmin):
    list_display = (
        'room', 'round_number', 'question_zone', 'result_status',
        'changes', 'extensions', 'temp_before', 'temp_after', 'duration', 'started_at',
    )
    list_filter = ('result_status', 'question_zone', 'room')
    search_fields = ('question_text',)
    readonly_fields = ('started_at', 'ended_at')
    inlines = [VoteInline]


# =====================================================================
# Vote — 단계별 투표 원장(디버깅용)
# =====================================================================
@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('round', 'member', 'phase', 'side', 'voted_at')
    list_filter = ('phase', 'side')
    search_fields = ('member__user__username',)


# =====================================================================
# (선택) Room / RoomMember — 이미 다른 곳에서 register 했다면 이 블록은 지우세요.
# =====================================================================
class RoomMemberInline(admin.TabularInline):
    model = RoomMember
    extra = 0
    readonly_fields = ('joined_at',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'temperature', 'status', 'current_topic', 'created_at')
    list_filter = ('status', 'current_topic')
    search_fields = ('title',)
    readonly_fields = ('id', 'created_at')
    inlines = [RoomMemberInline]