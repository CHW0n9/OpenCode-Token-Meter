/**
 * Font Scaling Manager
 * Manages global font scaling (50%, 75%, 100%, 125%) by updating CSS variables.
 */
class FontScaleManager {
    constructor() {
        this.currentScale = 1.0;
        this.allowedScales = [0.5, 0.75, 1.0, 1.25];
        this.init();
    }

    init() {
        // Load persistency if settingsManager is available
        if (window.settingsManager && window.settingsManager.settings && window.settingsManager.settings.font_scale) {
            this.setScale(window.settingsManager.settings.font_scale);
        } else {
            // Apply default from index.html (1.0)
            const rootStyle = getComputedStyle(document.documentElement);
            const scale = parseFloat(rootStyle.getPropertyValue('--font-scale')) || 1.0;
            this.currentScale = scale;
        }

        console.log(`[FontScaleManager] Initialized with scale: ${this.currentScale}`);
    }

    /**
     * Sets the global font scale.
     * @param {number} scale - One of 0.5, 0.75, 1.0, 1.25
     */
    setScale(scale) {
        if (!this.allowedScales.includes(scale)) {
            console.warn(`[FontScaleManager] Invalid scale: ${scale}. Use one of: ${this.allowedScales.join(', ')}`);
            return;
        }

        this.currentScale = scale;
        document.documentElement.style.setProperty('--font-scale', scale.toString());

        console.log(`[FontScaleManager] Scale set to ${scale * 100}%`);

        // Refresh charts if chartManager exists
        if (window.chartManager && typeof window.chartManager.updateCharts === 'function') {
            console.log('[FontScaleManager] Refreshing charts for new scale...');
            // Need to re-trigger charts because they use getScaledSize() which reads from computed style
            if (window.dashboard && typeof window.dashboard.renderCharts === 'function') {
                window.dashboard.renderCharts();
            }
        }
    }

    getScale() {
        return this.currentScale;
    }
}

// Initialize and expose to window
window.fontScaleManager = new FontScaleManager();

/**
 * Global helper for console use: window.setFontScale(0.75)
 */
window.setFontScale = (scale) => {
    window.fontScaleManager.setScale(scale);
};
