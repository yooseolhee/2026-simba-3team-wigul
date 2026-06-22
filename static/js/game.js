function openMidtermModal() {
    document.getElementById("midtermModal").style.display = "flex";
}

setTimeout(() => { //백엔드 로직 개발 전이므로 임의 시간 조정
    openMidtermModal();
}, 3000);