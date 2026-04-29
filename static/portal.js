document.querySelectorAll("[data-clear-query]").forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        window.location.href = `${window.location.pathname}${link.getAttribute("href")}`;
    });
});
