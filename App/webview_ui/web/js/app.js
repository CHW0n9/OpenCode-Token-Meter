class App {
    constructor() {
        this.currentView = 'dashboard';
    }

    init() {
        console.log('App initializing...');
        this.setupEventListeners();

        // Initialize dashboard
        if (window.dashboard) {
            window.dashboard.init();
        }

        if (window.settingsManager) {
            window.settingsManager.init();
        }

        if (window.detailsManager) {
            window.detailsManager.init();
        }

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

    switchView(viewId) {
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
                tab.classList.add('text-white', 'bg-black-700', 'border-white/20');
                tab.classList.remove('text-black-400');
            } else {
                tab.classList.remove('text-white', 'bg-black-700', 'border-white/20');
                tab.classList.add('text-black-400');
            }
        });

        this.currentView = viewId;
    }
}

// Initialize when DOM is ready
// We check for pywebviewready but also fallback to DOMContentLoaded for browser dev
const initApp = () => {
    if (window.appInitialized) return;
    window.appInitialized = true;
    
    const app = new App();
    app.init();
};

window.addEventListener('pywebviewready', initApp);
window.addEventListener('DOMContentLoaded', () => {
    // If pywebview doesn't load within 100ms (dev mode), init anyway
    setTimeout(() => {
        if (!window.pywebview) {
            console.log('Running in browser mode (no pywebview)');
            initApp();
        }
    }, 100);
});
