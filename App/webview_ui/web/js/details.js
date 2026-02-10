class DetailsManager {
    constructor() {
        this.currentViewMode = 'all'; // // Start with 'all' view
        this.currentScope = 'month'; // // Default scope
        this.customStartTs = null;
        this.customEndTs = null;
    }

    init() {
        // Initialize scope from settings (if available)
        if (window.settingsManager && window.settingsManager.settings && window.settingsManager.settings.default_time_scope) {
            this.currentScope = window.settingsManager.settings.default_time_scope;
        }

        // Update DOM to match current scope
        const timeSelect = document.getElementById('details-time-select');
        if (timeSelect) {
            timeSelect.value = this.currentScope;
        }

        this.setupEventListeners();
        this.initializeCustomRange();

        // Initial load
        this.loadDetails();
    }

    initializeCustomRange() {
        // Set default custom range to last 24 hours
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

        const startInput = document.getElementById('custom-start-date');
        const endInput = document.getElementById('custom-end-date');

        if (startInput) {
            startInput.value = this.toLocalISOString(yesterday);
        }
        if (endInput) {
            endInput.value = this.toLocalISOString(now);
        }
    }

    toLocalISOString(date) {
        // Format: YYYY - MM - DDTHH: mm: ss(for datetime - local input)
        const pad = n => n.toString().padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;

    }

    getSelectedScope() {
        const timeSelect = document.getElementById('details-time-select');
        return timeSelect ? timeSelect.value : 'month';

    }

    getCustomRange() {
        const startInput = document.getElementById('custom-start-date');
        const endInput = document.getElementById('custom-end-date');

        if (!startInput || !startInput.value) {
            return null;
        }

        const startDate = new Date(startInput.value);
        const endDate = endInput && endInput.value ? new Date(endInput.value) : new Date();

        return {
            startTs: Math.floor(startDate.getTime() / 1000),
            endTs: Math.floor(endDate.getTime() / 1000)
        };
    }

    loadDetails() {
        // console.log('[DetailsManager] loadDetails called');
        // console.log('[DetailsManager] window.dashboard:', window.dashboard);
        if (!window.dashboard) {
            console.error('[DetailsManager] window.dashboard is not available!');
            return;
        }

        const scope = this.getSelectedScope();
        // console.log('[DetailsManager] scope:', scope);

        if (scope === 'custom') {
            const range = this.getCustomRange();
            // console.log('[DetailsManager] custom range:', range);
            if (range) {
                // console.log('[DetailsManager] Calling renderDetailsView with custom range');
                window.dashboard.renderDetailsView(this.currentViewMode, 'custom', range.startTs, range.endTs);
            } else {
                console.error('[DetailsManager] Custom range is null!');
            }
        } else {
            // console.log('[DetailsManager] Calling renderDetailsView with scope:', scope);
            window.dashboard.renderDetailsView(this.currentViewMode, scope);
        }
    }

    switchViewMode(mode) {
        this.currentViewMode = mode;

        // Update button states
        document.querySelectorAll('.details-view-btn').forEach(btn => {
            if (btn.dataset.mode === mode) {
                btn.classList.add('bg-black-700', 'text-white');
                btn.classList.remove('text-black-400');
            } else {
                btn.classList.remove('bg-black-700', 'text-white');
                btn.classList.add('text-black-400');
            }
        });

        this.loadDetails();
    }

    setupEventListeners() {
        // View mode buttons
        document.querySelectorAll('.details-view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.currentTarget.dataset.mode;
                this.switchViewMode(mode);
            });
        });

        // Unified Time selector
        const timeSelect = document.getElementById('details-time-select');
        if (timeSelect) {
            timeSelect.addEventListener('change', (e) => {
                const customInputs = document.getElementById('custom-range-inputs');
                const confirmBtn = document.getElementById('custom-range-confirm-btn');
                if (e.target.value === 'custom') {
                    customInputs.classList.remove('hidden');
                    this.initializeCustomRange();
                    // Show confirm button immediately when switching to custom
                    if (confirmBtn) confirmBtn.classList.remove('hidden');
                } else {
                    customInputs.classList.add('hidden');
                    if (confirmBtn) confirmBtn.classList.add('hidden');
                    this.loadDetails(); // // Only auto-load for non-custom options
                }
            });
        }

        // Custom date change listeners - show confirm button when date changes
        const startInput = document.getElementById('custom-start-date');
        const endInput = document.getElementById('custom-end-date');
        const confirmBtn = document.getElementById('custom-range-confirm-btn');

        if (startInput) {
            startInput.addEventListener('change', () => {
                if (confirmBtn) confirmBtn.classList.remove('hidden');
            });
        }
        if (endInput) {
            endInput.addEventListener('change', () => {
                if (confirmBtn) confirmBtn.classList.remove('hidden');
            });
        }

        // Confirm button click - apply custom range and hide button
        if (confirmBtn) {
            // console.log('[DetailsManager] Setting up confirm button listener');
            confirmBtn.addEventListener('click', () => {
                // console.log('[DetailsManager] Confirm button clicked!');
                confirmBtn.classList.add('hidden');
                this.loadDetails();
            });
        } else {
            console.error('[DetailsManager] Confirm button not found!');
        }

        // Export Raw Data button
        const exportRawBtn = document.getElementById('export-raw-btn');
        if (exportRawBtn) {
            exportRawBtn.addEventListener('click', () => this.exportRawData());
        }

        // Export Stats button (exports visible table)
        const exportStatsBtn = document.getElementById('export-stats-btn');
        if (exportStatsBtn) {
            exportStatsBtn.addEventListener('click', () => this.exportCurrentView());
        }
    }

    async exportCurrentView() {
        // Export the visible table as CSV
        const tbody = document.getElementById('details-table-body');
        if (!tbody) {
            this.showError('No table to export');
            return;
        }

        // Get table headers
        const thead = document.querySelector('#details-view table thead tr');
        const headers = Array.from(thead.querySelectorAll('th')).map(th => th.textContent.trim());

        // Get table rows
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const csvRows = [headers.join(',')];

        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            const rowData = cells.map(td => {
                let text = td.textContent.trim();
                // Escape quotes and wrap in quotes if contains comma
                if (text.includes(',') || text.includes('"')) {
                    text = '"' + text.replace(/"/g, '""') + '"';
                }
                return text;
            });
            if (rowData.length > 0) {
                csvRows.push(rowData.join(','));
            }
        });

        const csvContent = csvRows.join('\n');
        const fileName = `statistics_${this.currentViewMode}_${new Date().toISOString().slice(0, 10)}.csv`;

        try {
            const result = await window.api.saveCsv(csvContent, fileName);
            if (result && result.success) {
                this.showSuccess(`CSV saved to: ${result.data}`);
            } else if (result && result.error && result.error !== "Save cancelled") {
                this.showError(`Export failed: ${result.error}`);
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showError('An error occurred during export');
        }
    }

    async exportRawData() {
        const scope = this.getSelectedScope();
        let startTs, endTs;

        if (scope === 'custom') {
            const range = this.getCustomRange();
            if (!range) {
                this.showError('Please select a start date');
                return;
            }
            startTs = range.startTs;
            endTs = range.endTs;
        } else {
            // Calculate timestamps for predefined ranges
            const now = new Date();
            const startDate = new Date();

            if (scope === 'today') {
                startDate.setHours(0, 0, 0, 0);
            } else if (scope === 'week') {
                startDate.setDate(now.getDate() - 7);
                startDate.setHours(0, 0, 0, 0);
            } else if (scope === 'month') {
                startDate.setDate(1);
                startDate.setHours(0, 0, 0, 0);
            } else if (scope === 'all') {
                startDate.setTime(0); // // Beginning of time
            }

            startTs = Math.floor(startDate.getTime() / 1000);
            endTs = Math.floor(now.getTime() / 1000);
        }

        if (endTs < startTs) {
            this.showError('End date must be after start date');
            return;
        }

        try {
            const result = await window.api.exportCsvRange(startTs, endTs);
            if (result.success && result.data) {
                this.showSuccess(`CSV exported: ${result.data}`);
            } else {
                this.showError('Export failed: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showError('Export failed');
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-white text-black-950 border border-black-100' : type === 'error' ? 'bg-black-700 text-white' : 'bg-black-800 text-white';

        toast.className = `fixed bottom-4 right-4 ${bgColor} px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

window.detailsManager = new DetailsManager();
