const currentSide = document.querySelector(".current-side");
const detailBtn = document.querySelector(".current-side-more");
const arrow = document.querySelector(".detail-arrow");

detailBtn.addEventListener("click", () => {
    currentSide.classList.toggle("active");

    arrow.classList.toggle("fa-angle-down");
    arrow.classList.toggle("fa-angle-up");
});