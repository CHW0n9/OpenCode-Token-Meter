class ApiClient {
    constructor() {
        this.mockMode = false;
    }

    _isPywebviewAvailable() {
        return typeof window.pywebview !== 'undefined' && window.pywebview.api;
    }

    async getStats(scope = 'today') {
        if (!this._isPywebviewAvailable()) {
            return { success: false, error: 'PyWebView not available' };
        }
        try {
            return await window.pywebview.api.get_stats(scope);
        } catch (error) {
            console.error('API Error (getStats):', error);
            return { success: false, error: error.message };
        }
    }

    async checkUpdates(lastTs) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.check_updates(lastTs);
        } catch (error) {
            console.error('API Error (checkUpdates):', error);
            return { success: false, error: error.message };
        }
    }

    async getSettings() {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_settings();
        } catch (error) {
            console.error('API Error (getSettings):', error);
            return { success: false, error: error.message };
        }
    }

    async saveSettings(settings) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.save_settings(settings);
        } catch (error) {
            console.error('API Error (saveSettings):', error);
            return { success: false, error: error.message };
        }
    }

    async getStatsByProvider(scope = 'today') {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_stats_by_provider(scope);
        } catch (error) {
            console.error('API Error (getStatsByProvider):', error);
            return { success: false, error: error.message };
        }
    }

    async getStatsByModel(scope = 'today') {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_stats_by_model(scope);
        } catch (error) {
            console.error('API Error (getStatsByModel):', error);
            return { success: false, error: error.message };
        }
    }

    async getDetails(scope = 'month', mode = 'provider') {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_details(scope, mode);
        } catch (error) {
            console.error('API Error (getDetails):', error);
            return { success: false, error: error.message };
        }
    }

    async exportCsv(scope = 'month') {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.export_csv(scope);
        } catch (error) {
            console.error('API Error (exportCsv):', error);
            return { success: false, error: error.message };
        }
    }

    async exportCsvRange(startTs, endTs) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.export_csv_range(startTs, endTs);
        } catch (error) {
            console.error('API Error (exportCsvRange):', error);
            return { success: false, error: error.message };
        }
    }

    async getPricingCatalog() {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_pricing_catalog();
        } catch (error) {
            console.error('API Error (getPricingCatalog):', error);
            return { success: false, error: error.message };
        }
    }

    async getStatsRange(startTs, endTs) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_stats_range(startTs, endTs);
        } catch (error) {
            console.error('API Error (getStatsRange):', error);
            return { success: false, error: error.message };
        }
    }

    async getStatsByProviderRange(startTs, endTs) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_stats_by_provider_range(startTs, endTs);
        } catch (error) {
            console.error('API Error (getStatsByProviderRange):', error);
            return { success: false, error: error.message };
        }
    }

    async getStatsByModelRange(startTs, endTs) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_stats_by_model_range(startTs, endTs);
        } catch (error) {
            console.error('API Error (getStatsByModelRange):', error);
            return { success: false, error: error.message };
        }
    }

    async getThresholdsProgress() {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_thresholds_progress();
        } catch (error) {
            console.error('API Error (getThresholdsProgress):', error);
            return { success: false, error: error.message };
        }
    }

    async getAgentStatus() {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.get_agent_status();
        } catch (error) {
            console.error('API Error (getAgentStatus):', error);
            return { success: false, error: error.message };
        }
    }

    async saveCsv(content, filename) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.save_csv(content, filename);
        } catch (error) {
            console.error('API Error (saveCsv):', error);
            return { success: false, error: error.message };
        }
    }

    async exportToClipboard(text) {
        if (!this._isPywebviewAvailable()) return { success: false, error: 'PyWebView not available' };
        try {
            return await window.pywebview.api.export_to_clipboard(text);
        } catch (error) {
            console.error('API Error (exportToClipboard):', error);
            return { success: false, error: error.message };
        }
    }

    _getMockStats() { }
}

// Initialize global API instance
window.api = new ApiClient();
