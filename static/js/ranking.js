// =====================
// 배경 화면 탭
// =====================
const buttons = document.querySelectorAll(
    ".ranking-content > .ranking-category .ranking-tab button"
);
const lists = document.querySelectorAll(
    ".ranking-content > .ranking-list"
);

buttons.forEach(button => {
    button.addEventListener("click", () => {

        buttons.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        lists.forEach(list => {
            list.style.display = "none";
        });

        const targetId = button.dataset.target;
        document.getElementById(targetId).style.display = "flex";
    });
});


// =====================
// 내 방 순위 모달 열기 / 닫기
// =====================
const openBtns = document.querySelectorAll(".my-rank-btn");
const modalOverlay = document.querySelector(".my-rank-modal-overlay");
const closeBtn = document.querySelector(".my-rank-close-btn");

openBtns.forEach(btn => {
    btn.addEventListener("click", () => {
        modalOverlay.classList.add("show");
    });
});

closeBtn.addEventListener("click", () => {
    modalOverlay.classList.remove("show");
});


// =====================
// 내 방 순위 모달 내부 탭
// =====================
const modal = document.querySelector(".my-rank-modal");

const modalButtons =
    modal.querySelectorAll(".ranking-tab button");

const modalLists =
    modal.querySelectorAll(".ranking-list");

modalButtons.forEach(button => {
    button.addEventListener("click", () => {

        modalButtons.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        modalLists.forEach(list => {
            list.style.display = "none";
        });

        const targetId = button.dataset.target;
        const targetList = modal.querySelector(`#${targetId}`);

        if (targetList) {
            targetList.style.display = "flex";
        }
    });
});


// =====================
// 상세 모달
// =====================
const detailModal = document.querySelector(
    ".time-detail-modal-overlay"
);

const detailCloseBtn = document.querySelector(
    ".time-detail-close-btn"
);

const detailValue = document.getElementById(
    "detail-value"
);

const detailIcon = document.getElementById(
    "detail-icon"
);


// ===== 최장 라운드 item =====
const timeItems = document.querySelectorAll(
    ".time-ranking-item"
);

timeItems.forEach(item => {
    item.addEventListener("click", () => {

        detailValue.textContent = "14:30";
        detailIcon.className = "fa-regular fa-clock";

        detailModal.classList.add("show");
    });
});



// ===== 상세 모달 닫기 =====
detailCloseBtn.addEventListener("click", () => {
    detailModal.classList.remove("show");
});