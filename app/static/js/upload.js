// Upload & Scan Client-side Script
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

    // Sliders
    const inputTlow = document.getElementById("input-tlow");
    const inputThigh = document.getElementById("input-thigh");
    const inputDelta = document.getElementById("input-delta");
    const valTlow = document.getElementById("val-tlow");
    const valThigh = document.getElementById("val-thigh");
    const valDelta = document.getElementById("val-delta");

    let selectedFile = null;

    // Synchronize slider text
    if (inputTlow) inputTlow.addEventListener("input", (e) => valTlow.textContent = e.target.value);
    if (inputThigh) inputThigh.addEventListener("input", (e) => valThigh.textContent = e.target.value);
    if (inputDelta) inputDelta.addEventListener("input", (e) => valDelta.textContent = e.target.value);

    // Reset parameters to default values
    const btnResetParams = document.getElementById("btn-reset-params");
    if (btnResetParams) {
        btnResetParams.addEventListener("click", () => {
            if (inputTlow) {
                inputTlow.value = "0.15";
                valTlow.textContent = "0.15";
            }
            if (inputThigh) {
                inputThigh.value = "0.40";
                valThigh.textContent = "0.40";
            }
            if (inputDelta) {
                inputDelta.value = "0.20";
                valDelta.textContent = "0.20";
            }
        });
    }

    // Drag & Drop handlers
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

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    cameraInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    function handleFileSelection(file) {
        if (!file.type.startsWith("image/")) {
            alert("กรุณาเลือกไฟล์รูปภาพเท่านั้น (JPG, PNG, BMP)");
            return;
        }

        selectedFile = file;
        previewName.textContent = file.name;
        previewSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + " MB";

        const reader = new FileReader();
        reader.onload = (e) => {
            previewThumbnail.src = e.target.result;
            previewContainer.classList.remove("hidden");
            previewContainer.classList.add("flex");
            btnProcess.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    btnRemove.addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        cameraInput.value = "";
        previewContainer.classList.add("hidden");
        previewContainer.classList.remove("flex");
        btnProcess.disabled = true;
    });

    // Submit & Process
    btnProcess.addEventListener("click", async () => {
        if (!selectedFile) return;

        btnProcess.disabled = true;
        progressContainer.classList.remove("hidden");
        progressBar.style.width = "25%";
        progressPercent.textContent = "25%";
        progressText.innerHTML = '<i class="fa-solid fa-cloud-arrow-up fa-bounce mr-1 text-blue-600"></i> กำลังอัปโหลดภาพขึ้นเซิร์ฟเวอร์...';

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

            progressBar.style.width = "60%";
            progressPercent.textContent = "60%";
            progressText.innerHTML = '<i class="fa-solid fa-microchip fa-spin mr-1 text-blue-600"></i> กำลังรัน 7-Step Digital Image Processing...';

            // 2. Process
            const tLow = inputTlow.value;
            const tHigh = inputThigh.value;
            const deltaMin = inputDelta.value;

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

            const procData = await procRes.json();

            progressBar.style.width = "100%";
            progressPercent.textContent = "100%";
            progressText.innerHTML = '<i class="fa-solid fa-check text-emerald-600 mr-1"></i> ประมวลผลเสร็จสิ้น กำลังเปิดรายงาน...';

            // 3. Redirect to Processing Result Page
            setTimeout(() => {
                window.location.href = `/processing/${imageId}`;
            }, 600);

        } catch (err) {
            alert("เกิดข้อผิดพลาด: " + err.message);
            progressContainer.classList.add("hidden");
            btnProcess.disabled = false;
        }
    });
});
