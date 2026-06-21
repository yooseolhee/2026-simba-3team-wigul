const subjectBtns = document.querySelectorAll(".subject button");
const startBtn = document.querySelector(".start");
const openSubjectModalBtn = document.querySelector("#openSubjectModalBtn");
const subjectModal = document.querySelector("#subjectModal");
const subjectSelectModal = document.querySelector("#subjectSelectModal");


openSubjectModalBtn.addEventListener("click", () => {
    subjectModal.style.display = "flex";
});

subjectBtns.forEach(btn => {
    btn.addEventListener("click", () => {

        // 이전 선택 제거
        subjectBtns.forEach(b => b.classList.remove("selected"));

        // 현재 버튼 선택
        btn.classList.add("selected");

        // 시작하기 버튼 활성화
        startBtn.classList.add("active");
        startBtn.disabled = false;
    });
});

startBtn.addEventListener("click", () => {
    // 첫 번째 모달 숨기기
    subjectModal.style.display = "none";

    // 두 번째 모달 띄우기
    subjectSelectModal.style.display = "flex";
});