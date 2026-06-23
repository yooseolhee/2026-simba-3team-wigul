const infoBtn = document.querySelector(".temp-info-btn");
const popup = document.getElementById("temp-popup");

infoBtn.addEventListener("click", () => {
    popup.classList.toggle("active");
});