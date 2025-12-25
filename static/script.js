
// Disable button to show Parising Text when clicked
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");

    if (form) {
        form / this.addEventListener("submit", function () {
            const btn = document.querySelector("button");
            btn.innerText = "Parsing... Please wait";
            btn.disabled = true;
        })
    }
});