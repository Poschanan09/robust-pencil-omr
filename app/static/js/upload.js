// Upload & Scan Client-side Script (Robust Pencil OMR)
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const cameraInput = document.getElementById("camera-input");
    const previewContainer = document.getElementById("preview-container");
    const previewThumbnail = document.getElementById("preview-thumbnail");
    const previewName = document.getElementById("preview-name");
    const previewSize = document.getElementById("preview-size");
    const btnRemove = document.getElementById("btn-remove-file");
    const btnProcess = document.getElementById("btn-process");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressText = document.getElementById("progress-text");
    const progressPercent = document.getElementById("progress-percent");

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

    const DEFAULT_TLOW = "0.15";
    const DEFAULT_THIGH = "0.40";
    const DEFAULT_DELTA = "0.20";

    let selectedFile = null;

    // Parameter State Manager (Real-time Red / Green color toggling)
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

        // Individual Slider Number Colors
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

        // Reset Button & Text Response
        if (isAnyChanged) {
            // Active Custom State: Red text and underline
            if (btnResetParams) {
                btnResetParams.innerHTML = '<i class="fa-solid fa-rotate-left text-xs"></i> <span class="font-bold underline text-accent">รีเซ็ตเป็นค่าเดิม</span>';
                btnResetParams.className = "font-display font-bold text-xs flex items-center space-x-1.5 py-1 px-2.5 text-accent hover:text-red-800 transition-all cursor-pointer";
            }
            if (btnProcess) {
                const span = btnProcess.querySelector("span");
                if (span) span.textContent = `เริ่มประมวลผล (ปรับแต่ง: ${tlow} | ${thigh} | ${delta})`;
            }
        } else {
            // Default State: Soft Green
            if (btnResetParams) {
                btnResetParams.innerHTML = '<i class="fa-solid fa-check text-xs text-emerald-600"></i> <span class="text-emerald-700">ค่าเริ่มต้น</span>';
                btnResetParams.className = "font-display font-bold text-xs flex items-center space-x-1.5 py-1 px-2.5 text-emerald-700 transition-all cursor-pointer";
            }
            if (btnProcess) {
                const span = btnProcess.querySelector("span");
                if (span) span.textContent = "เริ่มประมวลผลและตรวจกระดาษคำตอบ";
            }
        }
    }

    // Attach slider listeners
    [inputTlow, inputThigh, inputDelta].forEach(slider => {
        if (slider) {
            slider.addEventListener("input", updateParameterState);
            slider.addEventListener("change", updateParameterState);
        }
    });

    // Reset Function attached globally and to button
    window.resetOMRParameters = function(e) {
        if (e && e.preventDefault) e.preventDefault();
        if (e && e.stopPropagation) e.stopPropagation();

        if (inputTlow) inputTlow.value = DEFAULT_TLOW;
        if (inputThigh) inputThigh.value = DEFAULT_THIGH;
        if (inputDelta) inputDelta.value = DEFAULT_DELTA;

        updateParameterState();

        if (btnResetParams) {
            btnResetParams.innerHTML = '<i class="fa-solid fa-check text-emerald-600 text-xs mr-1"></i> <span class="text-emerald-700 font-bold">รีเซ็ตเป็นค่าเดิมแล้ว</span>';
            setTimeout(() => {
                updateParameterState();
            }, 1200);
        }
    };

    if (btnResetParams) {
        btnResetParams.addEventListener("click", window.resetOMRParameters);
    }

    // Initial check
    updateParameterState();

    // Drag & Drop handlers
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

    // Large Preview Handler
    function handleFileSelection(file) {
        if (!file.type.startsWith("image/")) {
            alert("กรุณาเลือกไฟล์รูปภาพเท่านั้น (JPG, PNG, BMP)");
            return;
        }

        selectedFile = file;
        if (previewName) previewName.textContent = file.name;
        if (previewSize) previewSize.textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;

        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewThumbnail) previewThumbnail.src = e.target.result;
            if (previewContainer) {
                previewContainer.classList.remove("hidden");
                previewContainer.classList.add("block");
            }
            if (dropZone) dropZone.classList.add("hidden");
            if (btnProcess) btnProcess.disabled = false;

            // Smooth scroll to process button so user can proceed easily
            setTimeout(() => {
                if (btnProcess) btnProcess.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }, 100);
        };
        reader.readAsDataURL(file);
    }

    if (btnRemove) {
        btnRemove.addEventListener("click", () => {
            selectedFile = null;
            if (fileInput) fileInput.value = "";
            if (cameraInput) cameraInput.value = "";
            if (previewContainer) {
                previewContainer.classList.add("hidden");
                previewContainer.classList.remove("block");
            }
            if (dropZone) dropZone.classList.remove("hidden");
            if (btnProcess) btnProcess.disabled = true;
        });
    }

    // Submit & Process
    if (btnProcess) {
        btnProcess.addEventListener("click", async () => {
            if (!selectedFile) return;

            btnProcess.disabled = true;
            if (progressContainer) progressContainer.classList.remove("hidden");
            if (progressBar) progressBar.style.width = "25%";
            if (progressPercent) progressPercent.textContent = "25%";
            if (progressText) progressText.innerHTML = '<i class="fa-solid fa-cloud-arrow-up fa-bounce mr-1.5 text-blue-600"></i> กำลังอัปโหลดภาพขึ้นเซิร์ฟเวอร์...';

            try {
                // 1. Upload
                const formData = new FormData();
                formData.append("file", selectedFile);

                const uploadRes = await fetch("/api/upload", {
                    method: "POST",
                    body: formData
                });

                if (!uploadRes.ok) {
                    let errMsg = "การอัปโหลดไฟล์ล้มเหลว";
                    try {
                        const errData = await uploadRes.json();
                        errMsg = errData.detail || errMsg;
                    } catch (e) {
                        const raw = await uploadRes.text();
                        errMsg = raw || errMsg;
                    }
                    throw new Error(errMsg);
                }

                const uploadData = await uploadRes.json();
                const imageId = uploadData.image_id;

                if (progressBar) progressBar.style.width = "60%";
                if (progressPercent) progressPercent.textContent = "60%";
                if (progressText) progressText.innerHTML = '<i class="fa-solid fa-microchip fa-spin mr-1.5 text-blue-600"></i> กำลังรัน 7-Step Digital Image Processing...';

                // 2. Process with current slider thresholds
                const tLow = inputTlow ? inputTlow.value : "0.15";
                const tHigh = inputThigh ? inputThigh.value : "0.40";
                const deltaMin = inputDelta ? inputDelta.value : "0.20";

                const procRes = await fetch(`/api/process/${imageId}?t_low=${tLow}&t_high=${tHigh}&delta_min=${deltaMin}`, {
                    method: "POST"
                });

                if (!procRes.ok) {
                    let errMsg = "การประมวลผลล้มเหลว";
                    try {
                        const errData = await procRes.json();
                        errMsg = errData.detail || errMsg;
                    } catch (e) {
                        const raw = await procRes.text();
                        errMsg = raw || errMsg;
                    }
                    throw new Error(errMsg);
                }

                if (progressBar) progressBar.style.width = "100%";
                if (progressPercent) progressPercent.textContent = "100%";
                if (progressText) progressText.innerHTML = '<i class="fa-solid fa-check text-emerald-600 mr-1.5"></i> ประมวลผลเสร็จสิ้น กำลังเปิดรายงาน...';

                // 3. Redirect to Processing Result Page
                setTimeout(() => {
                    window.location.href = `/processing/${imageId}`;
                }, 600);

            } catch (err) {
                alert("เกิดข้อผิดพลาด: " + err.message);
                if (progressContainer) progressContainer.classList.add("hidden");
                btnProcess.disabled = false;
            }
        });
    }
});
