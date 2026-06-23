// ===========================================
// 랭킹 페이지 전체 통합 JS
// ===========================================

// 1. 메인 화면 탭 전환 로직
const mainButtons = document.querySelectorAll(".ranking-content > .ranking-category .ranking-tab button");
const mainLists = document.querySelectorAll(".ranking-content > .ranking-list");

mainButtons.forEach(button => {
    button.addEventListener("click", () => {
        mainButtons.forEach(btn => btn.classList.remove("active"));
        button.classList.add("active");

        mainLists.forEach(list => list.style.display = "none");
        const targetId = button.dataset.target;
        document.getElementById(targetId).style.display = "flex";
    });
});

// 2. 내 방 순위 모달 열기/닫기
const openBtns = document.querySelectorAll(".my-rank-btn");
const modalOverlay = document.querySelector(".my-rank-modal-overlay");
const closeBtn = document.querySelector(".my-rank-close-btn");

if (openBtns) {
    openBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            modalOverlay.classList.add("show");

            // 버튼 숨기기
            openBtns.forEach(b => b.classList.add("hidden"));
        });
    });
}

if (closeBtn) {
    closeBtn.addEventListener("click", () => {
        modalOverlay.classList.remove("show");

        // 버튼 다시 보이기
        openBtns.forEach(b => b.classList.remove("hidden"));
    });
}

// 3. 내 방 순위 모달 내부 탭 전환
const modal = document.querySelector(".my-rank-modal");
if(modal) {
    const modalButtons = modal.querySelectorAll(".ranking-tab button");
    const modalLists = modal.querySelectorAll(".ranking-list");

    modalButtons.forEach(button => {
        button.addEventListener("click", () => {
            modalButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");

            modalLists.forEach(list => list.style.display = "none");
            const targetId = button.dataset.target;
            const targetList = modal.querySelector(`#${targetId}`);
            if (targetList) targetList.style.display = "flex";
        });
    });
}

// 4. 상세 모달 열기 및 데이터 연동
const detailModal = document.querySelector(".time-detail-modal-overlay");
const detailCloseBtn = document.querySelector(".time-detail-close-btn");

document.querySelectorAll(".ranking-list-item").forEach(item => {
    item.addEventListener("click", () => {
        // 내 방 순위 살펴보기 버튼 등 모달이 아닌 아이템은 클릭 이벤트 제외
        if(item.classList.contains('my-rank-btn')) return;

        // 클릭한 항목의 정보 추출
        const roomName = item.querySelector(".ranking-room-name").textContent;
        const leaderName = item.querySelector(".ranking-leader").textContent;
        const rank = item.querySelector(".ranking-num")?.textContent || "1위";
        
        // 정렬 기준에 따라 다르게 표시될 값 추출
        const valueElement = item.querySelector(".ranking-temp, .ranking-max-round, .ranking-max-time, .ranking-max-change");
        const detailValue = valueElement ? valueElement.textContent : "";
        
        // 모달에 데이터 주입
        document.getElementById("detail-room-name").textContent = roomName;
        document.getElementById("detail-leader").textContent = leaderName;
        document.getElementById("detail-value").textContent = detailValue;
        document.getElementById("detail-rank").textContent = rank;

        detailModal.classList.add("show");
    });
});

// 상세 모달 닫기
if(detailCloseBtn) {
    detailCloseBtn.addEventListener("click", () => {
        detailModal.classList.remove("show");
    });
}