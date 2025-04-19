// Show loading spinner on submit
function showSpinner(form) {
    const spinner = document.getElementById("spinner");
    const btn = document.getElementById("submit-btn");
    spinner.classList.remove("d-none");
    btn.setAttribute("disabled", "true");
}

// Auto redirect delay after success
document.addEventListener("DOMContentLoaded", function () {
    const alertBox = document.querySelector(".alert-success");
    if (alertBox) {
        setTimeout(() => {
            window.location.href = "/accounts/login/";
        }, 3000);
    }
});

// Resend cooldown
let seconds = 60;
const resendBtn = document.getElementById("resendBtn");
const countdown = document.getElementById("countdown");

const interval = setInterval(() => {
    seconds--;
    countdown.innerText = seconds;

    if (seconds <= 0) {
        clearInterval(interval);
        resendBtn.removeAttribute("disabled");
        resendBtn.innerHTML = "Resend OTP";
    }
}, 1000);
