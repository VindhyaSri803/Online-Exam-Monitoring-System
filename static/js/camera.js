/**
 * ExamGuard Candidate Registration Camera Handler
 * Handles live webcam stream, snapshot capture, canvas drawing, and retake/confirm.
 */

let videoStream = null;

async function initRegistrationCamera() {
  const video = document.getElementById("reg-camera-video");
  const cameraContainer = document.getElementById("camera-container");
  const errorMsg = document.getElementById("camera-error-msg");

  if (!video) return;

  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false
    });
    video.srcObject = videoStream;
    video.play();
    if (errorMsg) errorMsg.style.display = "none";
  } catch (err) {
    console.warn("Camera access unavailable or denied:", err);
    if (errorMsg) {
      errorMsg.style.display = "block";
      errorMsg.innerText = "Webcam not available or permission denied. You can proceed using avatar simulation mode or upload an image.";
    }
  }
}

function captureRegistrationPhoto() {
  const video = document.getElementById("reg-camera-video");
  const canvas = document.getElementById("reg-camera-canvas");
  const previewImg = document.getElementById("photo-preview-img");
  const photoInput = document.getElementById("photo_data_input");
  const captureControls = document.getElementById("capture-controls");
  const previewControls = document.getElementById("preview-controls");
  const videoWrapper = document.getElementById("camera-video-wrapper");

  if (!video || !canvas) return;

  const context = canvas.getContext("2d");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;

  // Mirror effect to match preview
  context.translate(canvas.width, 0);
  context.scale(-1, 1);
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

  if (photoInput) photoInput.value = dataUrl;
  if (previewImg) {
    previewImg.src = dataUrl;
    previewImg.style.display = "block";
  }
  if (videoWrapper) videoWrapper.style.display = "none";
  if (captureControls) captureControls.style.display = "none";
  if (previewControls) previewControls.style.display = "flex";
}

function retakeRegistrationPhoto() {
  const previewImg = document.getElementById("photo-preview-img");
  const photoInput = document.getElementById("photo_data_input");
  const captureControls = document.getElementById("capture-controls");
  const previewControls = document.getElementById("preview-controls");
  const videoWrapper = document.getElementById("camera-video-wrapper");

  if (photoInput) photoInput.value = "";
  if (previewImg) previewImg.style.display = "none";
  if (videoWrapper) videoWrapper.style.display = "block";
  if (captureControls) captureControls.style.display = "flex";
  if (previewControls) previewControls.style.display = "none";
}

// Auto initialize when DOM loaded
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("reg-camera-video")) {
    initRegistrationCamera();
  }
});
