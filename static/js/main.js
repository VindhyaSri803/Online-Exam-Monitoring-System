/**
 * ExamGuard General UI & Admin Interactive Actions
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Synthetic Data Generation Action
  const genSyntheticBtn = document.getElementById("btn-generate-synthetic");
  if (genSyntheticBtn) {
    genSyntheticBtn.addEventListener("click", async () => {
      if (!confirm("Generate synthetic dataset (100+ candidates, 200+ sessions, 1000+ events)? This will populate analytics and clustering charts.")) return;

      genSyntheticBtn.disabled = true;
      genSyntheticBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Generating Dataset...';

      try {
        const res = await fetch("/api/admin/generate-synthetic-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidates: 110, sessions: 220 })
        });
        const data = await res.json();
        if (data.success) {
          alert(`Successfully generated synthetic cohort: ${data.candidates_added} candidates, ${data.sessions_added} sessions, ${data.events_created} events!`);
          window.location.reload();
        } else {
          alert(`Error generating dataset: ${data.error}`);
          genSyntheticBtn.disabled = false;
          genSyntheticBtn.innerHTML = '<i class="bi bi-database-add"></i> Generate Synthetic Dataset';
        }
      } catch (err) {
        alert("Failed to communicate with server.");
        genSyntheticBtn.disabled = false;
        genSyntheticBtn.innerHTML = '<i class="bi bi-database-add"></i> Generate Synthetic Dataset';
      }
    });
  }

  // 2. AI Integrity Report Generator Action
  const genReportBtn = document.getElementById("btn-generate-ai-report");
  if (genReportBtn) {
    genReportBtn.addEventListener("click", async () => {
      const sessionId = genReportBtn.dataset.sessionId;
      if (!sessionId) return;

      genReportBtn.disabled = true;
      genReportBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Generating AI Audit Report...';

      try {
        const res = await fetch(`/api/admin/generate-report/${sessionId}`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
          const reportBox = document.getElementById("ai-report-content");
          if (reportBox) {
            reportBox.innerText = data.report.report_text;
            reportBox.style.display = "block";
          }
          const modelBadge = document.getElementById("report-model-badge");
          if (modelBadge) {
            modelBadge.innerText = data.report.model_used;
          }
          alert("AI Integrity Audit Report generated successfully.");
          window.location.reload();
        } else {
          alert(`Failed to generate report: ${data.error}`);
          genReportBtn.disabled = false;
          genReportBtn.innerHTML = '<i class="bi bi-robot"></i> Generate AI Audit Report';
        }
      } catch (err) {
        alert("Error connecting to AI service.");
        genReportBtn.disabled = false;
        genReportBtn.innerHTML = '<i class="bi bi-robot"></i> Generate AI Audit Report';
      }
    });
  }

  // 3. Incident Status Updater
  const statusSelect = document.getElementById("incident-status-select");
  if (statusSelect) {
    statusSelect.addEventListener("change", async (e) => {
      const sessionId = statusSelect.dataset.sessionId;
      const newStatus = e.target.value;

      try {
        const res = await fetch("/api/admin/update-incident-status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, status: newStatus })
        });
        const data = await res.json();
        if (data.success) {
          // Visual confirmation
          const badge = document.getElementById("incident-status-badge");
          if (badge) {
            badge.innerText = newStatus;
          }
        }
      } catch (err) {
        console.error("Status update error:", err);
      }
    });
  }

  // 4. Modal Helpers
  window.openModal = function(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add("show");
  };

  window.closeModal = function(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove("show");
  };

  // Close modals when clicking backdrop
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.classList.remove("show");
    });
  });
});
