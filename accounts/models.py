from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    nickname = models.CharField(max_length=15)          # 사용할 닉네임 
    profile_character = models.CharField(max_length=100)     # 선택한 캐릭터 종류 (기본값: default_icon) 
    background_color = models.CharField(max_length=20)   # 선택한 배경 색상 헥스코드 (기본값: #FFFFFF) 

    def __str__(self):
        return self.nickname