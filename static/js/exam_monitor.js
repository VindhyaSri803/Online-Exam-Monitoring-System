/**
 * ExamGuard Candidate Exam Telemetry & Face Presence Monitor
 */

class ExamMonitor {
  constructor(config) {
    this.sessionId = config.sessionId;
    this.durationMinutes = config.durationMinutes || 30;
    this.monitoringInterval = config.monitoringInterval || 1500;
    this.mode = config.mode || "live"; // 'live' or 'simulated'
    
    this.stream = null;
    this.timerInterval = null;
    this.framePingInterval = null;
    this.secondsRemaining = this.durationMinutes * 60;
    
    this.isFacePresent = true;
    this.isSimulatedFacePresent = true;
    this.lastActivityPing = Date.now();

    this.initDOM();
    this.initTimer();
    this.initBrowserTelemetry();
    this.initNavigation();
    this.initMonitoringStream();
  }

  initDOM() {
    this.videoElem = document.getElementById("webcam-video");
    this.canvasElem = document.getElementById("webcam-canvas");
    this.statusIndicator = document.getElementById("face-status-indicator");
    this.timerDigits = document.getElementById("timer-digits");
    this.examForm = document.getElementById("exam-submission-form");
    this.simToggleBtn = document.getElementById("toggle-sim-face-btn");
  }

  async initMonitoringStream() {
    if (this.mode === "simulated") {
      this.startSimulatedTelemetry();
      return;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 480 }, height: { ideal: 360 }, facingMode: "user" },
        audio: false
      });
      if (this.videoElem) {
        this.videoElem.srcObject = this.stream;
        this.videoElem.play();
      }
      this.startFrameCaptureLoop();
    } catch (err) {
      console.warn("Live camera access failed, switching to simulated telemetry mode:", err);
      this.mode = "simulated";
      const simCard = document.getElementById("sim-status-banner");
      if (simCard) simCard.style.display = "block";
      this.startSimulatedTelemetry();
    }
  }

  startFrameCaptureLoop() {
    if (this.framePingInterval) clearInterval(this.framePingInterval);

    this.framePingInterval = setInterval(async () => {
      if (!this.videoElem || this.videoElem.paused || this.videoElem.ended) return;

      const frameData = this.captureCurrentFrame();
      if (!frameData) return;

      try {
        const res = await fetch("/api/monitoring/face-frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: this.sessionId,
            frame: frameData,
            mode: "live"
          })
        });

        const data = await res.json();
        if (data.success) {
          this.updateFaceStatus(data.face_detected, data.boxes);
        }
      } catch (err) {
        console.error("Frame monitoring ping error:", err);
      }
    }, this.monitoringInterval);
  }

  captureCurrentFrame() {
    if (!this.videoElem || !this.canvasElem) return null;
    const ctx = this.canvasElem.getContext("2d");
    this.canvasElem.width = this.videoElem.videoWidth || 480;
    this.canvasElem.height = this.videoElem.videoHeight || 360;

    ctx.drawImage(this.videoElem, 0, 0, this.canvasElem.width, this.canvasElem.height);
    return this.canvasElem.toDataURL("image/jpeg", 0.7);
  }

  startSimulatedTelemetry() {
    this.updateFaceStatus(true, [{ x: 140, y: 80, w: 180, h: 220 }]);

    if (this.framePingInterval) clearInterval(this.framePingInterval);

    this.framePingInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/monitoring/face-frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: this.sessionId,
            mode: "simulated",
            simulated_face_detected: this.isSimulatedFacePresent
          })
        });
        const data = await res.json();
        if (data.success) {
          this.updateFaceStatus(this.isSimulatedFacePresent, data.boxes);
        }
      } catch (err) {
        console.error("Simulated telemetry error:", err);
      }
    }, this.monitoringInterval);
  }

  toggleSimulatedFacePresence() {
    this.isSimulatedFacePresent = !this.isSimulatedFacePresent;
    this.updateFaceStatus(this.isSimulatedFacePresent, this.isSimulatedFacePresent ? [{ x: 140, y: 80, w: 180, h: 220 }] : []);
    if (this.simToggleBtn) {
      this.simToggleBtn.innerText = this.isSimulatedFacePresent ? "Simulate Looking Away (Absent)" : "Simulate Returning (Present)";
    }
  }

  updateFaceStatus(detected, boxes) {
    this.isFacePresent = detected;
    if (this.statusIndicator) {
      if (detected) {
        this.statusIndicator.className = "face-status-indicator detected";
        this.statusIndicator.innerHTML = '<i class="bi bi-shield-check"></i> 🟢 Face Detected';
      } else {
        this.statusIndicator.className = "face-status-indicator absent";
        this.statusIndicator.innerHTML = '<i class="bi bi-shield-exclamation"></i> 🔴 Face Not Detected';
      }
    }

    // Draw bounding boxes on canvas if live video
    if (this.canvasElem && this.mode === "live") {
      const ctx = this.canvasElem.getContext("2d");
      ctx.clearRect(0, 0, this.canvasElem.width, this.canvasElem.height);
      if (detected && boxes && boxes.length > 0) {
        ctx.strokeStyle = "#10b981";
        ctx.lineWidth = 3;
        boxes.forEach(b => {
          ctx.strokeRect(b.x, b.y, b.w, b.h);
        });
      }
    }
  }

  initBrowserTelemetry() {
    // 1. Tab Switching (visibilityState)
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        this.sendTelemetryEvent("TAB_SWITCH", "Candidate switched away from examination browser tab.", 5.0);
      } else {
        this.sendTelemetryEvent("WINDOW_FOCUS", "Candidate returned to examination tab.", 0.0);
      }
    });

    // 2. Window Blur & Focus
    window.addEventListener("blur", () => {
      this.sendTelemetryEvent("WINDOW_BLUR", "Exam window lost operating system focus.", 3.0);
    });

    window.addEventListener("focus", () => {
      this.sendTelemetryEvent("WINDOW_FOCUS", "Exam window regained operating system focus.", 0.0);
    });

    // 3. Fullscreen Exit Detection
    document.addEventListener("fullscreenchange", () => {
      if (!document.fullscreenElement) {
        this.sendTelemetryEvent("FULLSCREEN_EXIT", "Candidate exited full screen exam mode.", 4.0);
      }
    });

    // 4. User Activity Heartbeat (Throttled)
    const recordActivity = () => {
      const now = Date.now();
      if (now - this.lastActivityPing > 45000) { // Ping every 45s
        this.lastActivityPing = now;
        this.sendTelemetryEvent("MOUSE_ACTIVITY", "Candidate active interaction recorded.", 0.0);
      }
    };

    window.addEventListener("mousemove", recordActivity);
    window.addEventListener("keydown", recordActivity);
  }

  async sendTelemetryEvent(eventType, description, duration = 0.0) {
    try {
      const screenshot = (eventType === "TAB_SWITCH" || eventType === "WINDOW_BLUR") ? this.captureCurrentFrame() : null;

      await fetch("/api/monitoring/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.sessionId,
          event_type: eventType,
          description: description,
          duration: duration,
          screenshot: screenshot
        })
      });
    } catch (err) {
      console.error("Failed to log telemetry event:", err);
    }
  }

  initTimer() {
    this.updateTimerDisplay();

    this.timerInterval = setInterval(() => {
      this.secondsRemaining--;
      this.updateTimerDisplay();

      if (this.secondsRemaining <= 0) {
        clearInterval(this.timerInterval);
        alert("Examination time has elapsed. Your answers are being submitted automatically.");
        if (this.examForm) {
          this.examForm.submit();
        }
      }
    }, 1000);
  }

  updateTimerDisplay() {
    if (!this.timerDigits) return;
    const mins = Math.floor(Math.max(0, this.secondsRemaining) / 60);
    const secs = Math.max(0, this.secondsRemaining) % 60;
    const displayStr = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

    this.timerDigits.innerText = displayStr;

    if (this.secondsRemaining < 120) {
      this.timerDigits.className = "timer-digits danger";
    } else if (this.secondsRemaining < 300) {
      this.timerDigits.className = "timer-digits warning";
    }
  }

  initNavigation() {
    const qCards = document.querySelectorAll(".question-card");
    const navBtns = document.querySelectorAll(".q-nav-btn");
    const prevBtn = document.getElementById("btn-prev-q");
    const nextBtn = document.getElementById("btn-next-q");
    let currentIdx = 0;

    const showQuestion = (idx) => {
      qCards.forEach((c, i) => {
        c.classList.toggle("active", i === idx);
      });
      navBtns.forEach((b, i) => {
        b.classList.toggle("active", i === idx);
      });

      if (prevBtn) prevBtn.disabled = idx === 0;
      if (nextBtn) nextBtn.disabled = idx === qCards.length - 1;
      currentIdx = idx;

      this.sendTelemetryEvent("QUESTION_NAVIGATE", `Navigated to question #${idx + 1}`, 0.0);
    };

    navBtns.forEach((btn, idx) => {
      btn.addEventListener("click", () => showQuestion(idx));
    });

    if (prevBtn) prevBtn.addEventListener("click", () => {
      if (currentIdx > 0) showQuestion(currentIdx - 1);
    });

    if (nextBtn) nextBtn.addEventListener("click", () => {
      if (currentIdx < qCards.length - 1) showQuestion(currentIdx + 1);
    });

    // Mark answered questions
    const radios = document.querySelectorAll(".option-radio");
    radios.forEach(radio => {
      radio.addEventListener("change", (e) => {
        const qId = e.target.name.replace("question_", "");
        const parentCard = e.target.closest(".question-card");
        const qIndex = parseInt(parentCard.dataset.questionIndex, 10);
        
        // Highlight option row
        parentCard.querySelectorAll(".option-item").forEach(item => {
          item.classList.remove("selected");
        });
        e.target.closest(".option-item").classList.add("selected");

        // Mark nav pill
        if (navBtns[qIndex]) {
          navBtns[qIndex].classList.add("answered");
        }

        this.sendTelemetryEvent("ANSWER_SELECTED", `Answer selected for question #${qIndex + 1}`, 0.0);
      });
    });
  }
}

// Global initialization helper
window.ExamMonitor = ExamMonitor;
