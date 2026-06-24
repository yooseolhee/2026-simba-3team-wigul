# ⚖️ WE, SIDE

> 20대를 위한 밸런스 게임 앱 — 깊은 대화로 우리(we)가 되는 실시간 밸런스 게임 서비스

---

## 📱 소개

우리에겐 지금, 마음 속 대화를 자연스럽게 
꺼낼 수 있는 즐거운 서비스가 필요하다!

**WE, SIDE!** 는 처음 만나는 자리에서도, 이미 친한 사이에서도 유용하게 쓰이는 실시간 밸런스게임 웹 서비스입니다.

제시된 질문에 따라 SIDE A 또는 B를 선택해, 타이머 안에서 서로를 설득하고 사이드를 바꿀 수 있습니다.
라운드가 쌓일수록 온도가 올라가고, 질문은 점점 깊어집니다.

- 🎮 실시간으로 참여 가능한 밸런스 게임
- 👥 친구와 결과 비교 가능
- 🔥 룸별 랭킹 경쟁
- 📊 내 history 한 눈에 확인

---

## 🖼️ 스크린샷

| 홈 화면 | 게임 화면 | 결과 화면 |
|--------|---------|---------|
| ![홈](./static/images/homepage.png) | ![게임](./static/images/gamepage.png) | ![결과](./static/images/resultpage.png) |

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | `HTML/CSS` / `JAVASCRIPT` |
| Backend | `DJANGO` / `PYTHON` |
| Database | `SQLite3` |


---


### 설치 및 실행

```bash
# 레포지토리 클론
git clone https://github.com/[username]/[repo-name].git

# 디렉토리 이동
cd 2026-simba-3team-wigul

# 개발 서버 실행
python manage.py runserver


---

## 📁 프로젝트 구조

```
2026-simba-3te.../
├── accounts/            # 사용자 인증 앱
├── config/              # Django 설정 (settings, urls 등)
├── main/                # 메인 앱 (게임 로직 등)
├── static/
│   ├── css/             # 스타일시트
│   ├── fonts/           # 폰트 파일
│   ├── images/          # 이미지 파일
│   └── js/              # JavaScript 파일
├── templates/
│   ├── layouts/         # 공통 레이아웃 템플릿
│   ├── main/
│   │   ├── game/        # 게임 화면 템플릿
│   │   ├── home/        # 홈 화면 템플릿
│   │   ├── mypage/      # 마이페이지 템플릿
│   │   ├── myroom/      # 마이룸 템플릿
│   │   ├── ranking/     # 랭킹 화면 템플릿
│   │   └── first_loading.html
│   ├── shared/          # 공유 컴포넌트 템플릿
│   ├── base.html        # 베이스 템플릿
│   └── main.html
├── users/               # 유저 관련 앱
├── .gitignore
├── db.sqlite3           # 개발용 SQLite DB
└── manage.py            # Django 관리 스크립트
```

---

✨ 주요 기능

📲 QR / URL 입장


앱 설치 없이 QR 스캔 또는 링크만으로 즉시 참여 가능


⚖️ Before & After 투표


A/B 선택 후 결과 공개
타이머 속 열띤 토론 후 SIDE 재선택 기능으로 마음을 바꿀 수 있음


⏱️ 타이머


SIDE 공개 후 타이머 안에서 자유롭게 상대방 설득 가능
바로 투표 / 연장 기능으로 라운드 길이 유동적으로 조절


🌡️ 온도 시스템


대화가 잦고 활발할수록 온도 상승
온도에 따라 질문 난이도(레벨) 자동 상향


🐾 위굴이


나를 나타내는 나만의 캐릭터 위굴이 커스터마이징


🏆 랭킹

4개 종목으로 경쟁하는 랭킹 시스템

종목설명🌡️ 최고 온도가장 뜨거웠던 방🔄 최다 라운드가장 많은 라운드를 진행한 방⏳ 최장 시간가장 오래 플레이한 방🔀 최고 변화 횟수SIDE를 가장 많이 바꾼 방
