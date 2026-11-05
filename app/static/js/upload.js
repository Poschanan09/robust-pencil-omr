// Interactive Upload & Live OMR Inspection Script
// Course: ICE415 Digital Image Processing (KMUTT)

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const cameraInput = document.getElementById("camera-input");
    
    // Preview components
    const previewContainer = document.getElementById("preview-container");
    const previewThumbnail = document.getElementById("preview-thumbnail");
    const previewName = document.getElementById("preview-name");
    const previewSize = document.getElementById("preview-size");
    const btnRemove = document.getElementById("btn-remove-file");
    const previewLoadingOverlay = document.getElementById("preview-loading-overlay");
    const previewLoadingText = document.getElementById("preview-loading-text");
    const previewRejectionBox = document.getElementById("preview-rejection-box");
    const previewRejectionMsg = document.getElementById("preview-rejection-msg");
    const previewStatusDot = document.getElementById("preview-status-dot");
    
    // Live counts
    const liveCountFilled = document.getElementById("live-count-filled");
    const liveCountAmbiguous = document.getElementById("live-count-ambiguous");
    const liveCountBlank = document.getElementById("live-count-blank");
    
    // Stage Switcher Tabs
    const stageTabs = document.querySelectorAll(".stage-tab");
    
    // Sliders & Values
    const inputTlow = document.getElementById("input-tlow");
    const inputThigh = document.getElementById("input-thigh");
    const inputDelta = document.getElementById("input-delta");
    const valTlow = document.getElementById("val-tlow");
    const valThigh = document.getElementById("val-thigh");
    const valDelta = document.getElementById("val-delta");
    const paramStatusBadge = document.getElementById("param-status-badge");
    const paramSummaryText = document.getElementById("param-summary-text");
    const btnResetParams = document.getElementById("btn-reset-params");
    
    // Submit & Progress
    const btnProcess = document.getElementById("btn-process");
    const btnProcessLabel = document.getElementById("btn-process-label");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressText = document.getElementById("progress-text");
    const progressPercent = document.getElementById("progress-percent");

    const DEFAULT_TLOW = "0.15";
    const DEFAULT_THIGH = "0.40";
    const DEFAULT_DELTA = "0.20";

    let currentSessionId = null;
    let currentStage = "overlay";
    let isProcessing = false;
    let debounceTimer = null;

    // --- 1. Parameter State Management (Red / Green toggling) ---
    function updateParameterState() {
        if (!inputTlow || !inputThigh || !inputDelta) return;

        const tlow = Number(inputTlow.value).toFixed(2);
        const thigh = Number(inputThigh.value).toFixed(2);
        const delta = Number(inputDelta.value).toFixed(2);

        if (valTlow) valTlow.textContent = tlow;
        if (valThigh) valThigh.textContent = thigh;
        if (valDelta) valDelta.textContent = delta;

        const isTlowChanged = (tlow !== DEFAULT_TLOW);
        const isThighChanged = (thigh !== DEFAULT_THIGH);
        const isDeltaChanged = (delta !== DEFAULT_DELTA);
        const isAnyChanged = isTlowChanged || isThighChanged || isDeltaChanged;

        // Individual Value Colors
        if (valTlow) {
            valTlow.className = isTlowChanged
                ? "font-mono font-bold text-xs text-accent"
                : "font-mono font-bold text-xs text-emerald-700";
        }
        if (valThigh) {
            valThigh.className = isThighChanged
                ? "font-mono font-bold text-xs text-accent"
                : "font-mono font-bold text-xs text-emerald-700";
        }
        if (valDelta) {
            valDelta.className = isDeltaChanged
                ? "font-mono font-bold text-xs text-accent"
                : "font-mono font-bold text-xs text-emerald-700";
        }

        // Header Status Badge & Reset Button
        if (isAnyChanged) {
            if (paramStatusBadge) {
                paramStatusBadge.textContent = "ปรับแต่งเอง (Customized)";
                paramStatusBadge.className = "ml-2.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-100 text-red-800 border border-red-300";
            }
            if (paramSummaryText) {
                paramSummaryText.innerHTML = `<span class="text-accent font-bold">ใช้ค่าปรับแต่ง: เริ่มนับ ${tlow} | ฝนชัด ${thigh} | ระยะห่าง ${delta}</span>`;
            }
            if (btnResetParams) {
                btnResetParams.innerHTML = '<i class="fa-solid fa-rotate-left text-xs"></i> <span class="font-bold underline text-accent">รีเซ็ตเป็นค่าเดิม</span>';
                btnResetParams.className = "font-display font-bold text-xs flex items-center space-x-1.5 py-1 px-2.5 text-accent hover:text-red-800 transition-all cursor-pointer";
            }
        } else {
            if (paramStatusBadge) {
                paramStatusBadge.textContent = "ค่าเริ่มต้น (Default)";
                paramStatusBadge.className = "ml-2.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300";
            }
            if (paramSummaryText) {
                paramSummaryText.textContent = "ค่าเริ่มต้น: เริ่มนับ 0.15 | ฝนชัด 0.40 | ระยะห่าง 0.20";
            }
            if (btnResetParams) {
                btnResetParams.innerHTML = '<i class="fa-solid fa-check text-xs text-emerald-600"></i> <span class="text-emerald-700 font-bold">ค่าเริ่มต้น</span>';
                btnResetParams.className = "font-display font-bold text-xs flex items-center space-x-1.5 py-1 px-2.5 text-emerald-700 transition-all cursor-pointer";
            }
        }
    }

    // --- 2. Live Re-processing with Image Feedback (Debounced) ---
    async function triggerLiveReprocess() {
        if (!currentSessionId || isProcessing) return;

        const tlow = inputTlow ? inputTlow.value : DEFAULT_TLOW;
        const thigh = inputThigh ? inputThigh.value : DEFAULT_THIGH;
        const delta = inputDelta ? inputDelta.value : DEFAULT_DELTA;

        if (previewLoadingOverlay) {
            previewLoadingOverlay.classList.remove("hidden");
            if (previewLoadingText) previewLoadingText.textContent = "กำลังคำนวณและอัปเดตผลตรวจบนภาพ...";
        }

        try {
            const res = await fetch(`/api/process/${currentSessionId}?t_low=${tlow}&t_high=${thigh}&delta_min=${delta}`, {
                method: "POST"
            });
            if (!res.ok) throw new Error("Re-process failed");
            const resultData = await res.json();

            // Update live metrics
            if (resultData.summary) {
                if (liveCountFilled) liveCountFilled.textContent = resultData.summary.filled_count ?? 0;
                if (liveCountAmbiguous) liveCountAmbiguous.textContent = resultData.summary.ambiguous_count ?? 0;
                if (liveCountBlank) liveCountBlank.textContent = resultData.summary.blank_count ?? 0;
            }

            // Refresh Image Viewport with Cache-Buster
            refreshPreviewImage();

        } catch (err) {
            console.error("Live tuning update error:", err);
        } finally {
            if (previewLoadingOverlay) {
                previewLoadingOverlay.classList.add("hidden");
            }
        }
    }

    function onSliderChange() {
        updateParameterState();
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            triggerLiveReprocess();
        }, 220);
    }

    [inputTlow, inputThigh, inputDelta].forEach(slider => {
        if (slider) {
            slider.addEventListener("input", onSliderChange);
            slider.addEventListener("change", onSliderChange);
        }
    });

    // --- 3. Reset Button Action ---
    window.resetOMRParameters = function(e) {
        if (e && e.preventDefault) e.preventDefault();
        if (e && e.stopPropagation) e.stopPropagation();

        if (inputTlow) inputTlow.value = DEFAULT_TLOW;
        if (inputThigh) inputThigh.value = DEFAULT_THIGH;
        if (inputDelta) inputDelta.value = DEFAULT_DELTA;

        updateParameterState();
        triggerLiveReprocess();
    };

    if (btnResetParams) {
        btnResetParams.addEventListener("click", window.resetOMRParameters);
    }

    // --- 4. Stage Tab Switching ---
    function refreshPreviewImage() {
        if (!currentSessionId || !previewThumbnail) return;
        const targetUrl = `/api/process/${currentSessionId}/debug/${currentStage}?t=${Date.now()}`;
        previewThumbnail.src = targetUrl;
    }

    stageTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const stage = tab.dataset.stage;
            if (!stage) return;
            currentStage = stage;

            stageTabs.forEach(t => {
                t.className = (t === tab)
                    ? "btn-sketch-red px-2.5 py-1 text-xs stage-tab"
                    : "btn-sketch-paper px-2.5 py-1 text-xs stage-tab";
            });

            refreshPreviewImage();
        });
    });

    // --- 5. File Selection & Instant Pipeline Execution ---
    async function handleFileSelection(file) {
        if (!file.type.startsWith("image/")) {
            alert("กรุณาเลือกไฟล์รูปภาพเท่านั้น (JPG, PNG, BMP)");
            return;
        }

        // Display preview container
        if (previewName) previewName.textContent = file.name;
        if (previewSize) previewSize.textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
        if (previewContainer) {
            previewContainer.classList.remove("hidden");
            previewContainer.classList.add("block");
        }
        if (dropZone) dropZone.classList.add("hidden");
        if (previewRejectionBox) previewRejectionBox.classList.add("hidden");

        // Local instant thumbnail preview
        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewThumbnail) previewThumbnail.src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Show loading progress
        if (previewLoadingOverlay) {
            previewLoadingOverlay.classList.remove("hidden");
            if (previewLoadingText) previewLoadingText.textContent = "กำลังวิเคราะห์ภาพและตรวจจับรอยฝนดินสอ...";
        }
        if (btnProcess) btnProcess.disabled = true;

        try {
            isProcessing = true;
            // 1. Upload
            const formData = new FormData();
            formData.append("file", file);

            const uploadRes = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (!uploadRes.ok) {
                const errData = await uploadRes.json().catch(() => ({}));
                throw new Error(errData.detail || "การอัปโหลดไฟล์ล้มเหลว");
            }

            const uploadData = await uploadRes.json();
            currentSessionId = uploadData.image_id;

            // 2. Process with current parameters
            const tlow = inputTlow ? inputTlow.value : DEFAULT_TLOW;
            const thigh = inputThigh ? inputThigh.value : DEFAULT_THIGH;
            const delta = inputDelta ? inputDelta.value : DEFAULT_DELTA;

            const procRes = await fetch(`/api/process/${currentSessionId}?t_low=${tlow}&t_high=${thigh}&delta_min=${delta}`, {
                method: "POST"
            });

            if (!procRes.ok) {
                const errData = await procRes.json().catch(() => ({}));
                throw new Error(errData.detail || "การประมวลผลล้มเหลว");
            }

            const procData = await procRes.json();

            // Check if rejected
            if (procData.status === "REJECTED") {
                if (previewRejectionBox) {
                    previewRejectionBox.classList.remove("hidden");
                    if (previewRejectionMsg) previewRejectionMsg.textContent = procData.rejection_reason || "ภาพไม่ผ่านเกณฑ์การตรวจสอบ";
                }
                if (previewStatusDot) {
                    previewStatusDot.className = "w-2.5 h-2.5 rounded-full bg-red-500 flex-shrink-0";
                }
                currentStage = "original";
            } else {
                if (previewStatusDot) {
                    previewStatusDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 flex-shrink-0 animate-pulse";
                }
                currentStage = "overlay";
            }

            // Update stage tabs style
            stageTabs.forEach(t => {
                t.className = (t.dataset.stage === currentStage)
                    ? "btn-sketch-red px-2.5 py-1 text-xs stage-tab"
                    : "btn-sketch-paper px-2.5 py-1 text-xs stage-tab";
            });

            // Update live metrics
            if (procData.summary) {
                if (liveCountFilled) liveCountFilled.textContent = procData.summary.filled_count ?? 0;
                if (liveCountAmbiguous) liveCountAmbiguous.textContent = procData.summary.ambiguous_count ?? 0;
                if (liveCountBlank) liveCountBlank.textContent = procData.summary.blank_count ?? 0;
            }

            // Display the processed overlay image
            refreshPreviewImage();

            // Enable review button
            if (btnProcess) {
                btnProcess.disabled = false;
                if (btnProcessLabel) btnProcessLabel.innerHTML = 'ดูรายงานผลคะแนนและตารางตรวจคำตอบฉบับเต็ม &rarr;';
            }

        } catch (err) {
            alert("เกิดข้อผิดพลาด: " + err.message);
            if (btnProcess) btnProcess.disabled = false;
        } finally {
            isProcessing = false;
            if (previewLoadingOverlay) {
                previewLoadingOverlay.classList.add("hidden");
            }
        }
    }

    // --- 6. Input Event Listeners ---
    if (dropZone) {
        ["dragenter", "dragover"].forEach(name => {
            dropZone.addEventListener(name, (e) => {
                e.preventDefault();
                dropZone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(name => {
            dropZone.addEventListener(name, (e) => {
                e.preventDefault();
                dropZone.classList.remove("dragover");
            });
        });

        dropZone.addEventListener("drop", (e) => {
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    if (cameraInput) {
        cameraInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    if (btnRemove) {
        btnRemove.addEventListener("click", () => {
            currentSessionId = null;
            if (fileInput) fileInput.value = "";
            if (cameraInput) cameraInput.value = "";
            if (previewContainer) {
                previewContainer.classList.add("hidden");
                previewContainer.classList.remove("block");
            }
            if (dropZone) dropZone.classList.remove("hidden");
            if (btnProcess) btnProcess.disabled = true;
            if (liveCountFilled) liveCountFilled.textContent = "-";
            if (liveCountAmbiguous) liveCountAmbiguous.textContent = "-";
            if (liveCountBlank) liveCountBlank.textContent = "-";
        });
    }

    // --- 7. Direct Navigation to Full Result Page ---
    if (btnProcess) {
        btnProcess.addEventListener("click", () => {
            if (currentSessionId) {
                window.location.href = `/processing/${currentSessionId}`;
            }
        });
    }

    // Initial parameter state sync
    updateParameterState();
});
