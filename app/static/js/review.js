// Human-in-the-Loop Review Client-side Script
document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("review-container");
    const imageId = container.getAttribute("data-image-id");

    const reviewCard = document.getElementById("review-card");
    const finishCard = document.getElementById("finish-card");
    const progressBar = document.getElementById("queue-progress-bar");
    const statusText = document.getElementById("queue-status-text");
    const percentText = document.getElementById("queue-percent-text");

    const qBadge = document.getElementById("q-badge");
    const qTitle = document.getElementById("q-title");
    const qReason = document.getElementById("q-reason");
    const qAiGuess = document.getElementById("q-ai-guess");
    const roiOriginal = document.getElementById("roi-original");
    const roiBinary = document.getElementById("roi-binary");
    const fillRatiosContainer = document.getElementById("fill-ratios-container");
    const btnSkip = document.getElementById("btn-skip");

    let queue = [];
    let currentIndex = 0;
    let initialCount = 0;

    // Fetch ambiguous queue from API
    try {
        const res = await fetch(`/api/review/${imageId}/queue`);
        if (!res.ok) throw new Error("ไม่สามารถโหลดรายการข้อที่ต้องตรวจทานได้");
        const data = await res.json();

        queue = data.queue || [];
        initialCount = queue.length;

        if (queue.length === 0) {
            showFinishScreen();
        } else {
            renderCurrentQuestion();
        }
    } catch (err) {
        statusText.textContent = "เกิดข้อผิดพลาด: " + err.message;
    }

    function renderCurrentQuestion() {
        if (currentIndex >= queue.length) {
            showFinishScreen();
            return;
        }

        const item = queue[currentIndex];
        const qNum = item.question;
        const progressPct = Math.round((currentIndex / initialCount) * 100);

        // Update progress bar
        progressBar.style.width = `${progressPct}%`;
        percentText.textContent = `${progressPct}%`;
        statusText.textContent = `กำลังตรวจทานข้อที่ ${currentIndex + 1} จาก ${initialCount} ข้อ (เหลือ ${queue.length - currentIndex} ข้อ)`;

        // Update headers
        qBadge.textContent = `Q${qNum}`;
        qTitle.textContent = `ข้อที่ ${qNum}`;
        qReason.textContent = item.reason || "หลักฐานไม่เพียงพอ หรือมีรอยเปื้อน";
        qAiGuess.textContent = item.tentative_guess || "—";

        // Load zoomed ROIs
        roiOriginal.src = `/api/review/${imageId}/${qNum}/roi/orig?t=${Date.now()}`;
        roiBinary.src = `/api/review/${imageId}/${qNum}/roi/bin?t=${Date.now()}`;

        // Render Fill-Ratios
        fillRatiosContainer.innerHTML = "";
        const fRatios = item.fill_ratios || {};
        const topTwo = item.top_two || [];

        ["A", "B", "C", "D", "E"].forEach(opt => {
            const val = fRatios[opt] || 0.0;
            const pct = Math.round(val * 100);
            const isTop = topTwo.includes(opt);

            const div = document.createElement("div");
            div.className = `p-2 rounded-md border text-center ${isTop ? 'bg-amber-50/70 border-amber-300 font-semibold text-amber-900' : 'bg-white border-slate-200 text-slate-700'}`;
            div.innerHTML = `
                <div class="text-[11px] font-mono text-slate-500">${opt}</div>
                <div class="text-xs font-mono font-bold tabular-nums mt-0.5">${pct}%</div>
            `;
            fillRatiosContainer.appendChild(div);
        });
    }

    async function submitDecision(decision) {
        if (currentIndex >= queue.length) return;
        const item = queue[currentIndex];
        const qNum = item.question;

        try {
            const res = await fetch(`/api/review/${imageId}/decide`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: qNum,
                    decision: decision
                })
            });

            if (!res.ok) throw new Error("ส่งผลตรวจไม่สำเร็จ");

            // Advance to next
            currentIndex++;
            renderCurrentQuestion();
        } catch (err) {
            alert("บันทึกไม่สำเร็จ: " + err.message);
        }
    }

    function showFinishScreen() {
        reviewCard.classList.add("hidden");
        finishCard.classList.remove("hidden");
        progressBar.style.width = "100%";
        percentText.textContent = "100%";
        statusText.innerHTML = '<i class="fa-solid fa-circle-check text-emerald-600 mr-1"></i> ตรวจทานครบทุกข้อสมบูรณ์';
    }

    // Button event listeners
    document.querySelectorAll(".decision-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const choice = btn.getAttribute("data-choice");
            submitDecision(choice);
        });
    });

    btnSkip.addEventListener("click", () => {
        currentIndex++;
        renderCurrentQuestion();
    });

    // Keyboard Shortcuts
    window.addEventListener("keydown", (e) => {
        // Prevent trigger if user is typing in an input field
        if (["input", "textarea"].includes(document.activeElement.tagName.toLowerCase())) return;

        const key = e.key.toUpperCase();
        if (["1", "2", "3", "4", "5"].includes(key)) {
            const mapping = { "1": "A", "2": "B", "3": "C", "4": "D", "5": "E" };
            submitDecision(mapping[key]);
        } else if (["A", "B", "C", "D", "E"].includes(key)) {
            submitDecision(key);
        } else if (key === "0" || key === " ") {
            submitDecision("Blank");
        } else if (key === "S") {
            currentIndex++;
            renderCurrentQuestion();
        }
    });
});
