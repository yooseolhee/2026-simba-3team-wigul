const subjectBtns = document.querySelectorAll(".subject button");
const startBtn = document.querySelector(".start");
const openSubjectModalBtn = document.querySelector("#openSubjectModalBtn");
const subjectModal = document.querySelector("#subjectModal");
const subjectSelectModal = document.querySelector("#subjectSelectModal");


// 방장에게만 존재하는 버튼들이므로(팀원 화면엔 없음) 가드로 감싼다
if (openSubjectModalBtn && subjectModal) {
    openSubjectModalBtn.addEventListener("click", () => {
        subjectModal.style.display = "flex";
    });
}

subjectBtns.forEach(btn => {
    btn.addEventListener("click", () => {

        // 이전 선택 제거
        subjectBtns.forEach(b => b.classList.remove("selected"));

        // 현재 버튼 선택
        btn.classList.add("selected");

        // 시작하기 버튼 활성화
        if (startBtn) {
            startBtn.classList.add("active");
            startBtn.disabled = false;
        }
    });
});

// subjectSelectModal은 별도 페이지(subject_select_modal.html)에 있어
// create_room 화면에선 존재하지 않는다. 있을 때만 바인딩한다.
if (startBtn && subjectSelectModal) {
    startBtn.addEventListener("click", () => {
        // 첫 번째 모달 숨기기
        if (subjectModal) subjectModal.style.display = "none";

        // 두 번째 모달 띄우기
        subjectSelectModal.style.display = "flex";
    });
}