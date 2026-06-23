// 온도별 멘트 리스트
const tempMessages = {
    green: [
        "이제 시작이죠!<br>뜨겁게 달려봐요!",
        "아직 쌀쌀하네요…<br>대화로 온도 올려봐요!",
        "워밍업 중!<br>우리 팀의 위력을 보여줄 때에요.",
        "아이스브레이킹 완료!<br>이제 진짜 시작이에요~",
        "아직 좀 차가운 사이네요~<br>조금만 더 달궈봐요!"
    ],
    yellow: [
        "슬슬 뜨거워지고 있어요!<br>여기서 멈추면 안 되죠~",
        "대화에 열이 오르고 있어요!<br>조금만 더 힘내봐요.",
        "이 정도면 꽤 친해진 거 같은데요? 😏",
        "온도가 무르익고 있어요~<br>진짜 속마음 꺼낼 시간!",
        "중간 지점이에요!<br>지금부터가 진짜예요."
    ],
    red: [
        "완전 뜨거워요!<br>이제 못 말리는 사이네요 🔥",
        "활활 타오르는 중!<br>소방서 불러야 할 것 같아요!!",
        "이 온도면 진심으로<br>친해진 거 같은데요? 😤🔥",
        "불꽃 토론 중!<br>서로의 이야기가 치열하게 오가고 있어요~",
        "100°C를 향해 달려가는 중~<br>끝까지 가봐요!"
    ]
};

// 방 이름 렌더링
function renderRoomName(name) {
    document.querySelector('.room-input').value = name;
}

// 온도 및 랜덤 멘트 렌더링
function renderTemperature(temp) {
    const tempValueEl = document.querySelector('.temp-value');
    const tempDescEl = document.querySelector('.temp-desc');
    
    // 온도 숫자 업데이트
    tempValueEl.innerHTML = `🌡️ ${temp}°C`;

    let messageList = [];
    let colorCode = "";

    // 온도 구간 체크
    if (temp >= 10 && temp <= 33) {
        messageList = tempMessages.green;
        colorCode = "#a4e135";
    } else if (temp >= 34 && temp <= 66) {
        messageList = tempMessages.yellow;
        colorCode = "#f2c94c";
    } else if (temp >= 67 && temp <= 100) {
        messageList = tempMessages.red;
        colorCode = "#eb5757";
    } else {
        messageList = ["아직 얼어붙어 있어요 ❄️"];
        colorCode = "#82ccdd";
    }

    // 배열에서 랜덤 멘트
    const randomIndex = Math.floor(Math.random() * messageList.length);
    tempDescEl.innerHTML = messageList[randomIndex];
    
    // 온도 숫자 색상
    tempValueEl.style.color = colorCode;
}

// 멤버 리스트 렌더링
function renderMembers(members) {
    const memberListEl = document.querySelector('.member-list');
    const membersHeaderEl = document.querySelector('.members-header');
    
    // 총 멤버 수 꼐산
    membersHeaderEl.textContent = `멤버 (${members.length})`;

    // 기존 더미데이터 비우기
    memberListEl.innerHTML = '';

    members.forEach(member => {
        // 접속 상태
        const statusClass = member.isOnline ? 'online' : 'offline';
        
        // 방장 여부
        const badgeHTML = member.isHost 
            ? `<div class="badge-host">방장</div>` 
            : `<div class="badge-kick">방출</div>`;

        // li 태그 생성 후 데이터 끼워넣기
        const li = document.createElement('li');
        li.className = 'member-item';
        li.innerHTML = `
            <div class="status-dot ${statusClass}"></div>
            <div class="avatar ${member.color}">${member.avatar}</div>
            <div class="nickname">${member.nickname}</div>
            ${badgeHTML}
        `;
        
        memberListEl.appendChild(li);
    });
}

function init() {
    renderRoomName(roomData.roomName);
    renderTemperature(roomData.temperature);
    renderMembers(roomData.members);
}

document.addEventListener('DOMContentLoaded', init);