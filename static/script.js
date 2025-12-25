
// Disable button to show Parising Text when clicked
document.querySelector("form").addEventListener("submit", function () {
    const btn = document.querySelector("button");
    btn.innerText = "Parsing... Please wait";
    btn.disabled = true;
});