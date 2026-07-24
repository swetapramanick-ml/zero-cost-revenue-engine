document.addEventListener("DOMContentLoaded", () => {
    // State management
    let activeLeadId = null;
    let leadsList = [];
    let activeFilter = "all";
    let activeTab = "tab-email";
    
    // UI Elements - Navigation
    const btnNavDashboard = document.getElementById("btn-nav-dashboard");
    const btnNavSettings = document.getElementById("btn-nav-settings");
    const dashboardView = document.getElementById("dashboard-view");
    const settingsView = document.getElementById("settings-view");

    // UI Elements - Ingestion & Filter
    const ingestForm = document.getElementById("ingest-form");
    const statusFilters = document.getElementById("status-filters");
    const leadSearch = document.getElementById("lead-search");
    const leadsListContainer = document.getElementById("leads-list-container");

    // UI Elements - Detail View
    const workspaceEmpty = document.getElementById("workspace-empty-state");
    const workspaceActive = document.getElementById("workspace-active-content");
    const leadCompanyName = document.getElementById("lead-company-name");
    const leadDomainUrl = document.getElementById("lead-domain-url");
    const leadStatusBadge = document.getElementById("lead-status-badge");
    const tabHeaders = document.querySelector(".tab-header");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // Detail - Email Tab
    const emailTo = document.getElementById("email-to");
    const emailSubject = document.getElementById("email-subject");
    const emailBody = document.getElementById("email-body");
    const btnSaveDraft = document.getElementById("btn-save-draft");
    const btnReAi = document.getElementById("btn-re-ai");
    const btnReject = document.getElementById("btn-reject");
    const btnApprove = document.getElementById("btn-approve");

    // Detail - Insights & Meta
    const leadPainPoints = document.getElementById("lead-pain-points");
    const metaTitle = document.getElementById("meta-title");
    const metaDescription = document.getElementById("meta-description");
    const metaHeaders = document.getElementById("meta-headers");
    const metaEmails = document.getElementById("meta-emails");

    // Settings
    const settingsForm = document.getElementById("settings-form");
    const settingGeminiKey = document.getElementById("setting-gemini-key");
    const settingSmtpHost = document.getElementById("setting-smtp-host");
    const settingSmtpPort = document.getElementById("setting-smtp-port");
    const settingSmtpUser = document.getElementById("setting-smtp-user");
    const settingSmtpPass = document.getElementById("setting-smtp-pass");
    const settingSmtpFrom = document.getElementById("setting-smtp-from");
    const settingSmtpName = document.getElementById("setting-smtp-name");

    // Dashboard Stats
    const statTotal = document.getElementById("stat-total");
    const statPending = document.getElementById("stat-pending");
    const statCompleted = document.getElementById("stat-completed");

    // Toast Container
    const toastContainer = document.getElementById("toast-container");

    const API_BASE = (window.location.hostname === "127.0.0.1" && window.location.port === "5500") ? "http://127.0.0.1:8000" : "";
    const originalFetch = window.fetch.bind(window);
    window.fetch = (resource, options) => {
        if (typeof resource === "string" && resource.startsWith("/api/")) {
            resource = `${API_BASE}${resource}`;
        }
        return originalFetch(resource, options);
    };

    // --- Core Navigation ---
    btnNavDashboard.addEventListener("click", (e) => {
        e.preventDefault();
        btnNavDashboard.classList.add("active");
        btnNavSettings.classList.remove("active");
        dashboardView.classList.remove("hidden");
        settingsView.classList.add("hidden");
        loadLeads();
    });

    btnNavSettings.addEventListener("click", (e) => {
        e.preventDefault();
        btnNavSettings.classList.add("active");
        btnNavDashboard.classList.remove("active");
        settingsView.classList.remove("hidden");
        dashboardView.classList.add("hidden");
        loadSettings();
    });

    // --- Tab System ---
    tabHeaders.addEventListener("click", (e) => {
        const targetBtn = e.target.closest(".tab-btn");
        if (!targetBtn) return;
        
        // Deactivate all
        document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
        tabPanes.forEach(pane => pane.classList.remove("active"));

        // Activate clicked
        targetBtn.classList.add("active");
        activeTab = targetBtn.dataset.tab;
        document.getElementById(activeTab).classList.add("active");
    });

    // --- Toast Alerts ---
    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let iconName = "check-circle";
        let iconClass = "toast-icon-success";
        
        if (type === "error") {
            iconName = "alert-circle";
            iconClass = "toast-icon-error";
        } else if (type === "info") {
            iconName = "info";
            iconClass = "toast-icon-info";
        }

        toast.innerHTML = `
            <i data-lucide="${iconName}" class="${iconClass}"></i>
            <span>${message}</span>
        `;
        toastContainer.appendChild(toast);
        lucide.createIcons();

        // Remove after 4s
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-10px) scale(0.9)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- Load Leads & Pipeline ---
    async function loadLeads() {
        try {
            const response = await fetch("/api/leads");
            if (!response.ok) throw new Error("Failed to fetch leads");
            leadsList = await response.json();
            renderLeadsList();
            updateStats();
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // Update stats widgets
    async function updateStats() {
        try {
            const response = await fetch("/api/stats");
            if (!response.ok) return;
            const stats = await response.json();
            
            // Total is sum of all status values
            const total = Object.values(stats).reduce((a, b) => a + b, 0);
            statTotal.textContent = total;
            statPending.textContent = stats["Pending_Review"] || 0;
            statCompleted.textContent = stats["Completed"] || 0;
        } catch (err) {
            console.error("Failed to load stats", err);
        }
    }

    // Render Lead Cards
    function renderLeadsList() {
        const searchQuery = leadSearch.value.toLowerCase().trim();
        
        // Filter leads based on active tab and search query
        const filteredLeads = leadsList.filter(lead => {
            const matchesSearch = lead.company_name.toLowerCase().includes(searchQuery) || 
                                  lead.domain.toLowerCase().includes(searchQuery);
            
            if (activeFilter === "all") {
                return matchesSearch;
            } else {
                return lead.status === activeFilter && matchesSearch;
            }
        });

        if (filteredLeads.length === 0) {
            leadsListContainer.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="search" class="large-icon"></i>
                    <p>No matching leads found.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        leadsListContainer.innerHTML = filteredLeads.map(lead => {
            const isActive = lead.id === activeLeadId ? "active" : "";
            
            // Create status badge mapping
            let badgeClass = "badge-discovered";
            let statusText = lead.status.replace("_", " ");
            
            switch (lead.status) {
                case "Enriched": badgeClass = "badge-enriched"; break;
                case "Pending_Review": badgeClass = "badge-pending_review"; statusText = "Pending"; break;
                case "Completed": badgeClass = "badge-completed"; statusText = "Sent"; break;
                case "Failed": badgeClass = "badge-failed"; break;
                case "Rejected": badgeClass = "badge-rejected"; break;
            }

            return `
                <div class="lead-card ${isActive}" data-id="${lead.id}">
                    <div class="lead-info">
                        <span class="lead-name">${lead.company_name}</span>
                        <span class="lead-domain">${lead.domain}</span>
                    </div>
                    <span class="badge ${badgeClass}">${statusText}</span>
                </div>
            `;
        }).join("");

        // Add Event Listeners to cards
        document.querySelectorAll(".lead-card").forEach(card => {
            card.addEventListener("click", () => {
                const id = parseInt(card.dataset.id);
                selectLead(id);
            });
        });
    }

    // Click filter pills
    statusFilters.addEventListener("click", (e) => {
        if (!e.target.classList.contains("pill")) return;
        
        document.querySelectorAll("#status-filters .pill").forEach(pill => pill.classList.remove("active"));
        e.target.classList.add("active");
        activeFilter = e.target.dataset.status;
        renderLeadsList();
    });

    // Search query listener
    leadSearch.addEventListener("input", renderLeadsList);

    // --- Lead Detail View Ingestion ---
    async function selectLead(id) {
        activeLeadId = id;
        
        // Highlight in list
        document.querySelectorAll(".lead-card").forEach(card => {
            card.classList.toggle("active", parseInt(card.dataset.id) === id);
        });

        // Show loading in detail panel
        workspaceEmpty.classList.add("hidden");
        workspaceActive.classList.remove("hidden");
        
        try {
            const response = await fetch(`/api/leads/${id}`);
            if (!response.ok) throw new Error("Failed to load lead details");
            const lead = await response.json();
            
            // Render basic text elements
            leadCompanyName.textContent = lead.company_name;
            leadDomainUrl.textContent = lead.domain;
            
            // Handle status badge
            leadStatusBadge.className = "badge";
            let statusText = lead.status.replace("_", " ");
            switch(lead.status) {
                case "Discovered": leadStatusBadge.classList.add("badge-discovered"); break;
                case "Enriched": leadStatusBadge.classList.add("badge-enriched"); break;
                case "Pending_Review": leadStatusBadge.classList.add("badge-pending_review"); statusText = "Pending"; break;
                case "Completed": leadStatusBadge.classList.add("badge-completed"); statusText = "Sent"; break;
                case "Failed": leadStatusBadge.classList.add("badge-failed"); break;
                case "Rejected": leadStatusBadge.classList.add("badge-rejected"); break;
            }
            leadStatusBadge.textContent = statusText;

            // Load editable form elements
            emailTo.value = lead.recipient_email || "";
            emailSubject.value = lead.personalized_subject || "";
            emailBody.value = lead.personalized_body || "";

            // Parse metadata
            let meta = {};
            try {
                meta = JSON.parse(lead.extracted_metadata || "{}");
            } catch(e) {}

            metaTitle.textContent = meta.title || "Not extracted yet.";
            metaDescription.textContent = meta.description || "Not extracted yet.";
            
            // Display headings
            if (meta.headings && meta.headings.length > 0) {
                metaHeaders.innerHTML = meta.headings.map(h => `<div class="meta-value-box">${h}</div>`).join("");
            } else {
                metaHeaders.innerHTML = `<div class="text-muted">No headers extracted.</div>`;
            }

            // Display scraped emails
            if (meta.emails_found && meta.emails_found.length > 0) {
                metaEmails.innerHTML = meta.emails_found.map(em => `<div class="meta-value-box">${em}</div>`).join("");
            } else {
                metaEmails.innerHTML = `<div class="text-muted">No additional emails found on website.</div>`;
            }

            // Parse pain points
            let painPoints = [];
            try {
                painPoints = JSON.parse(lead.pain_points || "[]");
            } catch(e) {}

            if (painPoints.length > 0) {
                leadPainPoints.innerHTML = painPoints.map(pp => `<li>${pp}</li>`).join("");
            } else {
                leadPainPoints.innerHTML = `<li class="text-muted" style="border-left-color: var(--text-muted); background: none;">No AI pain points generated yet.</li>`;
            }

            // Adjust disabled/enabled buttons based on state
            const isFinished = lead.status === "Completed" || lead.status === "Rejected";
            btnApprove.disabled = isFinished;
            btnReject.disabled = isFinished;
            btnSaveDraft.disabled = isFinished;
            btnReAi.disabled = isFinished || !lead.extracted_metadata;

        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // --- Save email changes ---
    btnSaveDraft.addEventListener("click", async () => {
        if (!activeLeadId) return;
        
        try {
            const response = await fetch(`/api/leads/${activeLeadId}/update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    recipient_email: emailTo.value,
                    personalized_subject: emailSubject.value,
                    personalized_body: emailBody.value
                })
            });
            
            if (!response.ok) throw new Error("Failed to save changes");
            showToast("Draft changes saved successfully.");
            loadLeads();
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    // --- Regenerate AI ---
    btnReAi.addEventListener("click", async () => {
        if (!activeLeadId) return;
        
        btnReAi.disabled = true;
        btnReAi.innerHTML = `<i data-lucide="refresh-cw" class="animate-spin"></i> Processing...`;
        lucide.createIcons();
        showToast("Generating fresh AI email copy...", "info");
        
        try {
            const response = await fetch(`/api/leads/${activeLeadId}/personalize`, { method: "POST" });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to regenerate AI output");
            }
            showToast("AI Email regenerated successfully.");
            await loadLeads();
            await selectLead(activeLeadId);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnReAi.disabled = false;
            btnReAi.innerHTML = `<i data-lucide="refresh-cw"></i> Regenerate AI`;
            lucide.createIcons();
        }
    });

    // --- Reject Lead ---
    btnReject.addEventListener("click", async () => {
        if (!activeLeadId) return;
        
        try {
            const response = await fetch(`/api/leads/${activeLeadId}/reject`, { method: "POST" });
            if (!response.ok) throw new Error("Failed to reject lead");
            
            showToast("Lead rejected.", "info");
            await loadLeads();
            await selectLead(activeLeadId);
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    // --- Approve & Send Email ---
    btnApprove.addEventListener("click", async () => {
        if (!activeLeadId) return;
        
        // Save drafts first to make sure modifications go out
        try {
            const saveRes = await fetch(`/api/leads/${activeLeadId}/update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    recipient_email: emailTo.value,
                    personalized_subject: emailSubject.value,
                    personalized_body: emailBody.value
                })
            });
            if (!saveRes.ok) throw new Error("Failed to save draft edits before dispatch");
        } catch (e) {
            showToast(e.message, "error");
            return;
        }

        btnApprove.disabled = true;
        btnApprove.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Dispatched...`;
        lucide.createIcons();
        showToast("Connecting to SMTP server & dispatching email...", "info");
        
        try {
            const response = await fetch(`/api/leads/${activeLeadId}/approve`, { method: "POST" });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Email delivery failed");
            }
            showToast("Email dispatched successfully! Landed in inbox.", "success");
            await loadLeads();
            await selectLead(activeLeadId);
        } catch (err) {
            showToast(err.message, "error");
            // Reload details to show error message
            await loadLeads();
            await selectLead(activeLeadId);
        } finally {
            btnApprove.disabled = false;
            btnApprove.innerHTML = `<i data-lucide="send"></i> Approve & Send Email`;
            lucide.createIcons();
        }
    });

    // --- Ingest Lead Form submission ---
    ingestForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const companyName = document.getElementById("target-name").value.trim();
        const domain = document.getElementById("target-domain").value.trim();
        const btnIngest = document.getElementById("btn-ingest");
        
        btnIngest.disabled = true;
        btnIngest.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Enriched...`;
        lucide.createIcons();
        showToast(`Ingesting and enriching ${companyName}...`, "info");
        
        try {
            const response = await fetch("/api/leads/ingest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ company_name: companyName, domain: domain })
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to ingest lead");
            }
            
            const lead = await response.json();
            showToast(`${companyName} successfully added to database. Pipeline started!`);
            ingestForm.reset();
            
            await loadLeads();
            // Automatically select the newly added lead
            if (lead.id) {
                selectLead(lead.id);
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnIngest.disabled = false;
            btnIngest.innerHTML = `<i data-lucide="play" class="btn-icon"></i><span>Process</span>`;
            lucide.createIcons();
        }
    });

    // --- Load Settings ---
    async function loadSettings() {
        try {
            const response = await fetch("/api/settings");
            if (!response.ok) throw new Error("Failed to fetch settings");
            const data = await response.json();
            
            settingGeminiKey.value = data.GEMINI_API_KEY || "";
            settingSmtpHost.value = data.SMTP_HOST || "";
            settingSmtpPort.value = data.SMTP_PORT || "";
            settingSmtpUser.value = data.SMTP_USER || "";
            settingSmtpPass.value = data.SMTP_PASSWORD || "";
            settingSmtpFrom.value = data.SMTP_FROM_EMAIL || "";
            settingSmtpName.value = data.SMTP_FROM_NAME || "";
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // --- Save Settings ---
    settingsForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btnSave = document.getElementById("btn-save-settings");
        btnSave.disabled = true;
        
        const settingsPayload = {
            GEMINI_API_KEY: settingGeminiKey.value,
            SMTP_HOST: settingSmtpHost.value,
            SMTP_PORT: settingSmtpPort.value,
            SMTP_USER: settingSmtpUser.value,
            SMTP_PASSWORD: settingSmtpPass.value,
            SMTP_FROM_EMAIL: settingSmtpFrom.value,
            SMTP_FROM_NAME: settingSmtpName.value
        };

        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settingsPayload)
            });
            if (!response.ok) throw new Error("Failed to save settings");
            showToast("System configurations updated successfully.");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            btnSave.disabled = false;
        }
    });

    // --- Polling for Real-Time State updates ---
    setInterval(async () => {
        // Poll leads list
        try {
            const response = await fetch("/api/leads");
            if (!response.ok) return;
            const updatedLeads = await response.json();
            
            // Check if status changed for any lead, specifically the active lead
            let activeChanged = false;
            if (activeLeadId) {
                const oldActive = leadsList.find(l => l.id === activeLeadId);
                const newActive = updatedLeads.find(l => l.id === activeLeadId);
                if (oldActive && newActive && oldActive.status !== newActive.status) {
                    activeChanged = true;
                }
            }

            leadsList = updatedLeads;
            renderLeadsList();
            updateStats();
            
            if (activeChanged) {
                selectLead(activeLeadId);
                showToast("Lead state updated by background enrichment pipeline.", "info");
            }
        } catch (e) {
            console.error("Polling error", e);
        }
    }, 4000);

    // Initial setup
    loadLeads();
    lucide.createIcons();
});
