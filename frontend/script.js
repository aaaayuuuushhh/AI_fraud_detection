// --- GLOBAL FRAUDSHIELD UTILITIES ---

function showNotification(message, type) {
    let container = document.getElementById("notification-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "notification-container";
        container.className = "notification-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `sms-popup ${type}`; // type: success, error, warning

    const icons = {
        success: '✅',
        error: '🚫',
        warning: '⚠️',
        info: 'ℹ️'
    };

    toast.innerHTML = `
        <div class="notif-icon-circle">${icons[type] || '📩'}</div>
        <div class="notif-content">
            <div class="notif-header">
                <span class="notif-title">System Alert</span>
                <span class="notif-time">Just now</span>
            </div>
            <div class="notif-body">${message}</div>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 500);
    }, 5000);
}

// Global polling for ledger updates on dashboard
async function fetchGlobalHistory() {
    const tableBody = document.getElementById("transaction-history-body");
    if (!tableBody) return;

    try {
        const response = await fetch("/api/get_history");
        const history = await response.json();
        // This is primarily used by the dashboard which has its own render logic, 
        // but we keep this as a fallback if needed.
    } catch (e) {
        console.error("Ledger sync failed:", e);
    }
}

// Sidebar highlights
document.addEventListener('DOMContentLoaded', () => {
    // UI logic for sidebar active states or animations
});
