// Upload & Auto-Calibrated OMR Preview Script
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
    const liveCalibBadge = document.getElementById("live-calib-badge");
    
    // Live counts
    const liveCountFilled = document.getElementById("live-count-filled");
    const liveCountAmbiguous = document.getElementById("live-count-ambiguous");
    const liveCountBlank = document.getElementById("live-count-blank");
    
    // Stage Switcher Tabs
    const stageTabs = document.querySelectorAll(".stage-tab");
    
    // Submit
    const btnProcess = document.getElementById("btn-process");
    const btnProcessLabel = document.getElementById("btn-process-label");

    let currentSessionId = null;
    let currentStage = "overlay";
    let isProcessing = false;

    // --- 1. Stage Tab Switching ---
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
                    ? "btn-sketch-red px-2.5 py-1 text-xs stage-tab cursor-pointer"
                    : "btn-sketch-paper px-2.5 py-1 text-xs stage-tab cursor-pointer";
            });

            refreshPreviewImage();
        });
    });

    // --- 2. File Selection & Auto-Calibrated Pipeline Execution ---
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

        // Temporary local thumbnail preview
        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewThumbnail) previewThumbnail.src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Show loading progress
        if (previewLoadingOverlay) {
            previewLoadingOverlay.classList.remove("hidden");
            if (previewLoadingText) previewLoadingText.textContent = "กำลังวิเคราะห์ภาพและคำนวณผล OMR อัตโนมัติ...";
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

            // 2. Process with Auto-Calibration
            const procRes = await fetch(`/api/process/${currentSessionId}`, {
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
                    ? "btn-sketch-red px-2.5 py-1 text-xs stage-tab cursor-pointer"
                    : "btn-sketch-paper px-2.5 py-1 text-xs stage-tab cursor-pointer";
            });

            // Update live metrics
            if (procData.summary) {
                if (liveCountFilled) liveCountFilled.textContent = procData.summary.filled_count ?? 0;
                if (liveCountAmbiguous) liveCountAmbiguous.textContent = procData.summary.ambiguous_count ?? 0;
                if (liveCountBlank) liveCountBlank.textContent = procData.summary.blank_count ?? 0;
                
                const thresh = procData.summary.thresholds_used;
                if (thresh && liveCalibBadge) {
                    liveCalibBadge.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles mr-1.5 text-emerald-600"></i> วิเคราะห์ความไวอัตโนมัติ (เริ่มนับ ${thresh.t_low} | ฝนชัด ${thresh.t_high})`;
                }
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

    // --- 3. Input Event Listeners ---
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

    // --- 4. Direct Navigation to Full Result Page ---
    if (btnProcess) {
        btnProcess.addEventListener("click", () => {
            if (currentSessionId) {
                window.location.href = `/processing/${currentSessionId}`;
            }
        });
    }
});
