// EcoWise — front-end interactions

/* ---------------- Search autocomplete ---------------- */
(function () {
    const input = document.getElementById("heroSearch");
    const list = document.getElementById("suggest");
    if (!input || !list) return;

    let active = -1;
    let items = [];
    let timer = null;

    const close = () => {
        list.classList.remove("show");
        list.innerHTML = "";
        active = -1;
        items = [];
    };

    const render = (suggestions) => {
        items = suggestions;
        if (!suggestions.length) { close(); return; }
        list.innerHTML = suggestions
            .map((s, i) => `<li role="option" data-i="${i}">${s.replace(/</g, "&lt;")}</li>`)
            .join("");
        list.classList.add("show");
        active = -1;
    };

    const fetchSuggestions = async (q) => {
        try {
            const r = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
            if (!r.ok) return;
            const data = await r.json();
            render(data);
        } catch (_) { /* noop */ }
    };

    input.addEventListener("input", () => {
        const q = input.value.trim();
        clearTimeout(timer);
        if (q.length < 2) { close(); return; }
        timer = setTimeout(() => fetchSuggestions(q), 160);
    });

    const updateActive = () => {
        [...list.children].forEach((li, i) => {
            li.setAttribute("aria-selected", i === active ? "true" : "false");
        });
    };

    input.addEventListener("keydown", (e) => {
        if (!list.classList.contains("show")) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            active = (active + 1) % items.length;
            updateActive();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            active = (active - 1 + items.length) % items.length;
            updateActive();
        } else if (e.key === "Enter" && active >= 0) {
            e.preventDefault();
            input.value = items[active];
            close();
            input.form && input.form.submit();
        } else if (e.key === "Escape") {
            close();
        }
    });

    list.addEventListener("mousedown", (e) => {
        const li = e.target.closest("li");
        if (!li) return;
        input.value = li.textContent;
        close();
        input.form && input.form.submit();
    });

    document.addEventListener("click", (e) => {
        if (!input.contains(e.target) && !list.contains(e.target)) close();
    });
})();

/* ---------------- Onboarding guide ---------------- */
(function () {
    const overlay = document.getElementById("onboardOverlay");
    if (!overlay) return;

    const steps = overlay.querySelectorAll(".onboard-step");
    const dots = overlay.querySelectorAll(".onboard-dots .dot");
    const nextBtn = document.getElementById("onboardNext");
    const skipBtn = document.getElementById("onboardSkip");
    const closeBtn = document.getElementById("onboardClose");
    const fab = document.getElementById("helpFab");
    const footerHelp = document.getElementById("footerHelp");

    const STORAGE_KEY = "ecowise_onboarded_v1";
    let current = 0;

    const showStep = (i) => {
        current = i;
        steps.forEach((s, idx) => s.classList.toggle("active", idx === i));
        dots.forEach((d, idx) => d.classList.toggle("active", idx === i));
        if (nextBtn) {
            nextBtn.textContent = i === steps.length - 1 ? "Get started" : "Next";
        }
    };

    const open = () => {
        overlay.classList.add("show");
        document.body.style.overflow = "hidden";
        showStep(0);
    };
    const close = () => {
        overlay.classList.remove("show");
        document.body.style.overflow = "";
        try { localStorage.setItem(STORAGE_KEY, "1"); } catch (_) {}
    };

    nextBtn && nextBtn.addEventListener("click", () => {
        if (current < steps.length - 1) showStep(current + 1);
        else close();
    });
    skipBtn && skipBtn.addEventListener("click", close);
    closeBtn && closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
    document.addEventListener("keydown", (e) => {
        if (!overlay.classList.contains("show")) return;
        if (e.key === "Escape") close();
        if (e.key === "ArrowRight" && current < steps.length - 1) showStep(current + 1);
        if (e.key === "ArrowLeft" && current > 0) showStep(current - 1);
    });

    fab && fab.addEventListener("click", open);
    footerHelp && footerHelp.addEventListener("click", (e) => { e.preventDefault(); open(); });
    dots.forEach((d, idx) => d.addEventListener("click", () => showStep(idx)));

    // Auto-open on first visit (only on the home page)
    const isHome = location.pathname === "/" || location.pathname === "";
    let seen = false;
    try { seen = !!localStorage.getItem(STORAGE_KEY); } catch (_) {}
    if (isHome && !seen) {
        setTimeout(open, 600);
    }
})();
