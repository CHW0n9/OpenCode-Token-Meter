// Global Number Formatting Utility
window.formatCompactNumber = (num, decimals = 2) => {
    if (num === null || num === undefined) return '--';
    const n = Number(num);
    if (Number.isNaN(n)) return '--';
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(decimals)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(decimals)}K`;

    // For small numbers, show decimals if non-integer, otherwise no decimals
    if (Number.isInteger(n)) return n.toLocaleString();
    return n.toFixed(decimals);
};

class App {
    constructor() {
        this.currentView = 'dashboard';
    }

    async init() {
        console.log('App initializing...');
        this.setupEventListeners();

        // 1. Initialize Settings FIRST (Critical for defaults)
        if (window.settingsManager) {
            console.log('Initializing SettingsManager...');
            await window.settingsManager.init();
        }

        // 2. Initialize Dashboard
        if (window.dashboard) {
            // Dashboard init will now see loaded settings
            console.log('Initializing Dashboard...');
            window.dashboard.init();
        }

        // 3. Initialize Details
        if (window.detailsManager) {
            console.log('Initializing DetailsManager...');
            window.detailsManager.init();
        }

        // Start Agent Status Polling
        this.startAgentStatusPolling();

        // Initialize Custom Tooltip
        this.initCustomTooltip();

        const urlParams = new URLSearchParams(window.location.search);
        const initialPage = urlParams.get('page') || 'dashboard';
        this.switchView(initialPage);
    }

    setupEventListeners() {
        // Navigation Tabs
        const tabs = document.querySelectorAll('.nav-tab');
        console.log(`Setting up listeners for ${tabs.length} tabs`);

        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const viewId = e.currentTarget.dataset.view;
                console.log(`Tab clicked: ${viewId}`);
                this.switchView(viewId);
            });
        });

        // Scope Select (Today, Week, Month)
        const scopeSelect = document.getElementById('scope-select');
        if (scopeSelect) {
            scopeSelect.addEventListener('change', (e) => {
                if (window.dashboard) {
                    window.dashboard.loadStats(e.target.value);
                }
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                if (window.dashboard) {
                    refreshBtn.classList.add('animate-spin');
                    window.dashboard.loadStats().then(() => {
                        setTimeout(() => refreshBtn.classList.remove('animate-spin'), 500);
                    });
                }
            });
        }
    }



    initCustomTooltip() {
        const tooltip = document.getElementById('custom-tooltip');
        if (!tooltip) return;

        document.body.addEventListener('mouseover', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                tooltip.textContent = target.dataset.tooltip;
                tooltip.classList.remove('hidden');
            }
        });

        document.body.addEventListener('mousemove', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                // Position tooltip above cursor
                // e.clientX/Y are viewports coords
                tooltip.style.left = `${e.clientX}px`;
                tooltip.style.top = `${e.clientY}px`;
            } else {
                tooltip.classList.add('hidden');
            }
        });

        document.body.addEventListener('mouseout', (e) => {
            // Check if moving to a child element? No, mouseout bubbles.
            // But we use closest() in mouseover.
            // If target is no longer the tooltip element.
            const target = e.target.closest('[data-tooltip]');
            if (target) {
                // We might be moving out of the element.
                // But wait, mouseout fires when entering child too.
                // safe check: if relatedTarget is not inside current target.
                if (!target.contains(e.relatedTarget)) {
                    tooltip.classList.add('hidden');
                }
            }
        });
    }

    startAgentStatusPolling() {
        const updateStatus = async () => {
            if (!window.api) return;
            const result = await window.api.getAgentStatus();

            const container = document.getElementById('agent-status-container');
            const dot = document.getElementById('agent-status-dot');
            const text = document.getElementById('agent-status-text');

            if (!container || !dot || !text) return;

            if (result.success && result.data && result.data.active) {
                // Active: Green dot, "Agent Active"
                dot.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
                text.textContent = 'Agent Active';
                // Container: Neutral (Black/Gray)
                container.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full border border-black-700 bg-black-800 transition-colors';
                // Text: White/Gray (Neutral)
                text.className = "text-gray-300 text-xs font-medium";
            } else {
                // Inactive: Gray/Red dot, "Agent Offline"
                dot.className = 'w-2 h-2 rounded-full bg-gray-500';
                text.textContent = 'Agent Offline';
                // Container: Neutral
                container.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full border border-black-700 bg-black-800 transition-colors';
                // Text: Neutral
                text.className = "text-gray-400 text-xs font-medium";
            }
        };

        // Initial check
        updateStatus();

        // Poll every 5 seconds
        setInterval(updateStatus, 5000);
    }

    switchView(viewId) {
        // Check for unsaved settings when leaving Settings page
        if (this.currentView === 'settings' && viewId !== 'settings' && window.settingsManager) {
            if (window.settingsManager.hasUnsavedChanges()) {
                this.showUnsavedSettingsDialog(viewId);
                return; // Don't switch view yet
            }
        }

        this._performViewSwitch(viewId);
    }

    showUnsavedSettingsDialog(targetViewId) {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'unsaved-settings-modal';
        overlay.className = 'fixed inset-0 bg-black/70 flex items-center justify-center z-50';
        overlay.innerHTML = `
            <div class="bg-black-800 rounded-xl p-6 border border-black-700 max-w-md w-full mx-4 shadow-2xl">
                <h3 class="text-lg font-semibold text-white mb-4">Unsaved Changes</h3>
                <p class="text-black-300 mb-6">You have unsaved settings. Would you like to save them before leaving?</p>
                <div class="flex justify-end gap-3">
                    <button id="unsaved-discard" class="px-4 py-2 text-sm font-medium text-black-400 hover:text-white bg-black-900 hover:bg-black-700 border border-black-700 rounded-lg transition-all">
                        Discard
                    </button>
                    <button id="unsaved-cancel" class="px-4 py-2 text-sm font-medium text-black-400 hover:text-white bg-black-900 hover:bg-black-700 border border-black-700 rounded-lg transition-all">
                        Cancel
                    </button>
                    <button id="unsaved-save" class="px-4 py-2 text-sm font-medium text-black-950 bg-white hover:bg-black-200 rounded-lg transition-all">
                        Save
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Event handlers
        document.getElementById('unsaved-discard').addEventListener('click', () => {
            overlay.remove();
            window.settingsManager.loadSettings(); // Reset to original
            this._performViewSwitch(targetViewId);
        });

        document.getElementById('unsaved-cancel').addEventListener('click', () => {
            overlay.remove();
        });

        document.getElementById('unsaved-save').addEventListener('click', async () => {
            await window.settingsManager.saveSettings();
            overlay.remove();
            this._performViewSwitch(targetViewId);
        });
    }

    _performViewSwitch(viewId) {
        // Hide all views
        document.querySelectorAll('.view-section').forEach(el => {
            el.classList.add('hidden');
            el.classList.remove('animate-fade-in');
        });

        // Show selected view
        const view = document.getElementById(`${viewId}-view`);
        if (view) {
            view.classList.remove('hidden');
            view.classList.add('animate-fade-in');
        }

        // Update tab states
        document.querySelectorAll('.nav-tab').forEach(tab => {
            if (tab.dataset.view === viewId) {
                tab.classList.add('text-white', 'bg-black-700');
                tab.classList.remove('text-black-400');
            } else {
                tab.classList.remove('text-white', 'bg-black-700');
                tab.classList.add('text-black-400');
            }
        });

        this.currentView = viewId;

        // Trigger view-specific initialization
        if (viewId === 'settings' && window.settingsManager) {
            window.settingsManager.loadSettings();
        }

        // Defer details loading to click or explicit refresh
        // if (viewId === 'details' && window.detailsManager) {
        //    window.detailsManager.loadDetails();
        // }
    }
}

// Initialize when DOM is ready
// We check for pywebviewready but also fallback to DOMContentLoaded for browser dev
const initApp = async () => {
    if (window.appInitialized) return;
    window.appInitialized = true;

    const app = new App();
    await app.init();
};

window.addEventListener('pywebviewready', () => {
    initApp();
});

window.addEventListener('DOMContentLoaded', () => {
    // If pywebview doesn't load within 100ms (dev mode), init anyway
    setTimeout(() => {
        if (!window.pywebview) {
            console.log('Running in browser mode (no pywebview)');
            initApp();
        }
    }, 1000);
});
