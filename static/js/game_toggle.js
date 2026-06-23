function initializeToggle(container) {

    const toggle = container.querySelector(".my-side-toggle-input");
    const frog = container.querySelector(".frog");
    const sliderText = container.querySelector(".slider-text");
    const sideText = container.querySelector(".my-side-dsc");
    const slider = container.querySelector(".slider");

    toggle.addEventListener("change", () => {

        frog.src = frog.dataset.jump;

        setTimeout(() => {

            if (toggle.checked) {
                frog.style.left = "140px";

                container.classList.add("b-side");
                slider.classList.add("b-side");
            }
            else {
                frog.style.left = "25px";

                container.classList.remove("b-side");
                slider.classList.remove("b-side");
            }

            sideText.innerText =
                toggle.checked ? "당신은 B SIDE!" : "당신은 A SIDE!";

            sliderText.innerText =
                toggle.checked ? "B" : "A";

        }, 150);

        setTimeout(() => {
            frog.src = frog.dataset.land;
        }, 350);

        setTimeout(() => {
            frog.src = frog.dataset.sit;
        }, 600);

    });

}

document.querySelectorAll(".toggle-container").forEach(container => {
    initializeToggle(container);
});