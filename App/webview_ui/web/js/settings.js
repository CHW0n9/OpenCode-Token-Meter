class SettingsManager {
    constructor() {
        this.settings = null;
        this.originalSettings = null;
        this.pricingCatalog = { default: {}, models: {} };
        this.isRendering = false; // // Flag to prevent save button trigger during render
        this.expandedProviders = new Set();
        this.addModelDraft = null;
        this.tokenUnitMultipliers = {
            '1': 1,
            'K': 1_000,
            'M': 1_000_000,
            'B': 1_000_000_000,
            '1K': 1_000,
            '1M': 1_000_000,
            '1B': 1_000_000_000,
        };
    }

    hasUnsavedChanges() {
        if (!this.settings || !this.originalSettings) return false;
        return JSON.stringify(this.settings) !== JSON.stringify(this.originalSettings);
    }

    async init() {
        await this.loadSettings();
        await this.loadPricingCatalog();
        this.setupEventListeners();
    }

    async loadSettings() {
        try {
            const result = await window.api.getSettings();
            if (result.success) {
                this.settings = JSON.parse(JSON.stringify(result.data));
                if (!this.settings.prices) this.settings.prices = { models: {} };
                if (!this.settings.prices.models) this.settings.prices.models = {};
                await this.updateVersionBadge();
                this.originalSettings = JSON.parse(JSON.stringify(this.settings));
                this.render();
            } else {
                console.error('Failed to load settings:', result.error);
                this.showError('Failed to load settings');
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showError('Error loading settings');
        }
    }

    async loadPricingCatalog() {
        try {
            const result = await window.api.getPricingCatalog();
            if (result.success && result.data) {
                this.pricingCatalog = result.data;
                this.renderModelPricingTable();
            }
        } catch (error) {
            console.error('Error loading pricing catalog:', error);
        }
    }

    async updateVersionBadge() {
        const versionBadge = document.getElementById('app-version-badge');
        if (!versionBadge) return;

        let version = this.settings?.version || '--';
        try {
            const result = await window.api.getVersion();
            if (result.success && result.data) {
                version = result.data;
            }
        } catch (_error) {
            // Keep settings fallback silently
        }

        versionBadge.textContent = `v${version}`;
        versionBadge.classList.remove('hidden');
    }

    hideVersionBadge() {
        const versionBadge = document.getElementById('app-version-badge');
        if (versionBadge) {
            versionBadge.classList.add('hidden');
        }
    }

    renderNumberInput(value, step, inputClass, extraAttrs = '') {
        const upChevron = `<svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 9.5L8 5l4.5 4.5"></path></svg>`;
        const downChevron = `<svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 6.5L8 11l4.5-4.5"></path></svg>`;
        const safeValue = value ?? 0;
        return `
            <div class="pricing-number-input relative inline-flex items-stretch justify-end w-24">
                <input type="number" step="${step}" class="${inputClass} pr-8" value="${safeValue}" ${extraAttrs}>
                <div class="absolute inset-y-0 right-[0.4rem] flex flex-col justify-center gap-px">
                    <button type="button" tabindex="-1" class="pricing-step-btn flex items-center justify-center text-white/70 hover:text-white transition-colors" data-step-dir="up">${upChevron}</button>
                    <button type="button" tabindex="-1" class="pricing-step-btn flex items-center justify-center text-white/70 hover:text-white transition-colors" data-step-dir="down">${downChevron}</button>
                </div>
            </div>
        `;
    }

    setupCustomSelects() {
        if (window.customSelectManager) {
            const ids = [
                'timezone-select',
                'default-scope-select',
            ];
            window.customSelectManager.initSelectIds(ids);
            window.customSelectManager.syncIds(ids);
        }
    }

    setupEventListeners() {
        // Save button
        const saveBtn = document.getElementById('settings-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }

        // Reset button
        const resetBtn = document.getElementById('settings-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetToDefaults());
        }

        // Add model button
        const addModelBtn = document.getElementById('add-model-btn');
        if (addModelBtn) {
            addModelBtn.addEventListener('click', () => this.showAddModelDialog());
        }

        // Thresholds enabled toggle
        const thresholdsEnabled = document.getElementById('thresholds-enabled');
        if (thresholdsEnabled) {
            thresholdsEnabled.addEventListener('change', (e) => {
                this.settings.thresholds.enabled = e.target.checked;
                this.showSaveButton();
            });
        }

        // Input field listeners
        this.bindTokenThresholdInput('daily-tokens', 'daily-tokens-unit', 'thresholds.daily_tokens');
        this.bindInput('daily-cost', 'thresholds.daily_cost', parseFloat);
        this.bindTokenThresholdInput('monthly-tokens', 'monthly-tokens-unit', 'thresholds.monthly_tokens');
        this.bindInput('monthly-cost', 'thresholds.monthly_cost', parseFloat);

        // Timezone selector
        const timezoneSelect = document.getElementById('timezone-select');
        if (timezoneSelect) {
            timezoneSelect.addEventListener('change', (e) => {
                this.settings.timezone = e.target.value;
                this.showSaveButton();
            });
        }

        // Default Time Scope selector
        const defaultScopeSelect = document.getElementById('default-scope-select');
        if (defaultScopeSelect) {
            defaultScopeSelect.addEventListener('change', (e) => {
                this.settings.default_time_scope = e.target.value;
                this.showSaveButton();
            });
        }

        this.setupCustomSelects();

        // Notifications toggle
        const notificationsEnabled = document.getElementById('notifications-enabled');
        if (notificationsEnabled) {
            notificationsEnabled.addEventListener('change', (e) => {
                this.settings.notifications_enabled = e.target.checked;
                this.showSaveButton();
            });
        }
    }

    bindInput(elementId, settingPath, parser = null) {
        const element = document.getElementById(elementId);
        if (!element) return;

        //Auto - format on input(simple approach: remove commas to validate / save, add commas for display on blur)
        element.addEventListener('input', (e) => {
            // Allow typing, but maybe don't force format while typing to avoid cursor jumping
            // Just update the internal value
            let value = e.target.value.replace(/,/g, '');
            if (parser && value !== '') {
                value = parser(value);
            }
            this.setNestedValue(this.settings, settingPath, value);
            this.showSaveButton();
        });

        element.addEventListener('blur', (e) => {
            let value = e.target.value.replace(/,/g, '');
            if (value !== '' && !isNaN(value)) {
                e.target.value = Number(value).toLocaleString();
            }
        });

        // Also format on focus? No, better to keep raw number or keep formatted? 
        // Standard UX: keep formatted, strip when parsing.
    }

    getTokenUnitMultiplier(unit) {
        return this.tokenUnitMultipliers[unit] || 1;
    }

    formatTokenDisplayValue(value) {
        if (value === undefined || value === null || value === '') return '';
        const numeric = Number(value);
        if (Number.isNaN(numeric)) return '';
        if (Number.isInteger(numeric)) return numeric.toLocaleString();
        return numeric.toLocaleString(undefined, { maximumFractionDigits: 3 });
    }

    splitTokenThreshold(rawValue) {
        const numeric = Number(rawValue);
        if (!Number.isFinite(numeric)) {
            return { value: '', unit: '1' };
        }
        if (numeric === 0) {
            return { value: 0, unit: '1' };
        }
        if (numeric < 0) {
            return { value: '', unit: '1' };
        }

        const absValue = Math.abs(numeric);
        if (absValue >= 1_000_000_000) {
            return { value: numeric / 1_000_000_000, unit: 'B' };
        }
        if (absValue >= 1_000_000) {
            return { value: numeric / 1_000_000, unit: 'M' };
        }
        if (absValue >= 1_000) {
            return { value: numeric / 1_000, unit: 'K' };
        }
        return { value: numeric, unit: '1' };
    }

    bindTokenThresholdInput(valueInputId, unitSelectId, settingPath) {
        const valueInput = document.getElementById(valueInputId);
        const unitSelect = document.getElementById(unitSelectId);
        if (!valueInput || !unitSelect) return;

        const updateFromUi = () => {
            const rawText = valueInput.value.replace(/,/g, '').trim();
            if (rawText === '') {
                this.setNestedValue(this.settings, settingPath, '');
                this.showSaveButton();
                return;
            }

            const numericValue = Number(rawText);
            if (Number.isNaN(numericValue)) {
                this.showSaveButton();
                return;
            }

            const multiplier = this.getTokenUnitMultiplier(unitSelect.value);
            const normalized = Math.round(numericValue * multiplier);
            this.setNestedValue(this.settings, settingPath, normalized);
            this.showSaveButton();
        };

        valueInput.addEventListener('input', updateFromUi);
        valueInput.addEventListener('blur', () => {
            const rawText = valueInput.value.replace(/,/g, '').trim();
            if (rawText === '') return;
            const numericValue = Number(rawText);
            if (!Number.isNaN(numericValue)) {
                valueInput.value = this.formatTokenDisplayValue(numericValue);
            }
        });

        unitSelect.addEventListener('change', () => {
            updateFromUi();
        });
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((current, key) => {
            if (!current[key]) current[key] = {};
            return current[key];
        }, obj);
        target[lastKey] = value;
    }

    render() {
        if (!this.settings) return;

        this.isRendering = true; // // Prevent save button from showing during render

        // Thresholds
        const thresholdsEnabled = document.getElementById('thresholds-enabled');
        if (thresholdsEnabled) {
            thresholdsEnabled.checked = this.settings.thresholds?.enabled || false;
        }

        const formatNumber = (num) => {
            if (num === undefined || num === null || num === '') return '';
            return Number(num).toLocaleString();
        };

        const dailyTokens = document.getElementById('daily-tokens');
        const dailyTokensUnit = document.getElementById('daily-tokens-unit');
        if (dailyTokens && dailyTokensUnit) {
            const normalized = this.splitTokenThreshold(this.settings.thresholds?.daily_tokens);
            dailyTokens.value = this.formatTokenDisplayValue(normalized.value);
            dailyTokensUnit.value = normalized.unit;
        }

        const dailyCost = document.getElementById('daily-cost');
        if (dailyCost) {
            dailyCost.value = formatNumber(this.settings.thresholds?.daily_cost);
        }

        const monthlyTokens = document.getElementById('monthly-tokens');
        const monthlyTokensUnit = document.getElementById('monthly-tokens-unit');
        if (monthlyTokens && monthlyTokensUnit) {
            const normalized = this.splitTokenThreshold(this.settings.thresholds?.monthly_tokens);
            monthlyTokens.value = this.formatTokenDisplayValue(normalized.value);
            monthlyTokensUnit.value = normalized.unit;
        }

        const monthlyCost = document.getElementById('monthly-cost');
        if (monthlyCost) {
            monthlyCost.value = formatNumber(this.settings.thresholds?.monthly_cost);
        }

        // Notifications
        const notificationsEnabled = document.getElementById('notifications-enabled');
        if (notificationsEnabled) {
            notificationsEnabled.checked = this.settings.notifications_enabled || false;
        }

        // Refresh interval - REMOVED (Fixed to 5s)

        // Timezone
        const timezoneSelect = document.getElementById('timezone-select');
        if (timezoneSelect) {
            timezoneSelect.value = this.settings.timezone || 'local';
        }

        // Default Time Scope
        const defaultScopeSelect = document.getElementById('default-scope-select');
        if (defaultScopeSelect) {
            defaultScopeSelect.value = this.settings.default_time_scope || 'week';
        }

        this.setupCustomSelects();

        // Model pricing table
        this.renderModelPricingTable();

        this.isRendering = false; // // Re-enable save button logic
        this.hideSaveButton(); // // Ensure save button is hidden after render
    }

    renderModelPricingTable() {
        const tbody = document.getElementById('model-pricing-table');
        if (!tbody) return;

        tbody.innerHTML = '';
        const defaultModels = this.pricingCatalog.models || {};
        const userModels = this.settings.prices?.models || {};

        // Prepare data list
        let allModels = [];

        //1. Default Models
        Object.keys(defaultModels).forEach(modelId => {
            const customPricing = userModels[modelId];
            allModels.push({
                id: modelId,
                provider: modelId.split('/')[0] || 'unknown',
                name: modelId.split('/').slice(1).join('/') || modelId,
                pricing: customPricing || defaultModels[modelId],
                isDefault: true,
                isCustomized: !!customPricing,
                isUserOnly: false
            });
        });

        //2. User / Custom Models
        Object.keys(userModels).forEach(modelId => {
            if (defaultModels[modelId]) return;
            allModels.push({
                id: modelId,
                provider: modelId.split('/')[0] || 'custom',
                name: modelId.split('/').slice(1).join('/') || modelId,
                pricing: userModels[modelId],
                isDefault: false,
                isCustomized: true,
                isUserOnly: true
            });
        });

        // Sort by Provider, then Name
        allModels.sort((a, b) => {
            if (a.provider !== b.provider) {
                return a.provider.localeCompare(b.provider);
            }
            return a.name.localeCompare(b.name);
        });

        if (allModels.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-black-400">
                        // No model pricing configured
                    </td>
                </tr>
            `;
            return;
        }

        const providerGroups = new Map();
        allModels.forEach(item => {
            if (!providerGroups.has(item.provider)) {
                providerGroups.set(item.provider, []);
            }
            providerGroups.get(item.provider).push(item);
        });

        const providers = Array.from(providerGroups.keys()).sort((a, b) => a.localeCompare(b));

        providers.forEach(provider => {
            const models = providerGroups.get(provider) || [];
            const isExpanded = this.expandedProviders.has(provider);
            const providerKey = encodeURIComponent(provider);

            const chevronIcon = `<svg class="w-4 h-4 text-black-400 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>`;

            const providerRow = document.createElement('tr');
            providerRow.className = 'bg-black-900/30 cursor-pointer group transition-colors';
            providerRow.setAttribute('data-provider-toggle', providerKey);
            providerRow.innerHTML = `
                <td colspan="6" class="px-4 py-2.5">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            ${chevronIcon}
                            <span class="font-bold text-white transition-colors">${this.escapeHtml(provider)}</span>
                        </div>
                        <span class="text-xs text-black-400">${models.length} models</span>
                    </div>
                </td>
            `;
            tbody.appendChild(providerRow);

            if (!isExpanded) return;

            models.forEach(item => {
                const confirmIcon = `<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
                const cancelIcon = `<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`;
                const resetIcon = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>`;
                const deleteIcon = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;

                const tr = document.createElement('tr');
                tr.className = 'group';

                const originalPricing = this.originalSettings.prices?.models?.[item.id] || this.pricingCatalog.models?.[item.id];
                const currentPricing = this.settings.prices.models[item.id] || item.pricing;

                let isModified = false;
                if (originalPricing) {
                    isModified = (
                        (parseFloat(currentPricing.input) || 0) !== (parseFloat(originalPricing.input) || 0) ||
                        (parseFloat(currentPricing.output) || 0) !== (parseFloat(originalPricing.output) || 0) ||
                        (parseFloat(currentPricing.caching) || 0) !== (parseFloat(originalPricing.caching) || 0) ||
                        (parseFloat(currentPricing.request) || 0) !== (parseFloat(originalPricing.request) || 0)
                    );
                }

                let modelNameHtml = this.escapeHtml(item.name);
                if (item.isUserOnly || (item.isCustomized && item.isDefault)) {
                    modelNameHtml = `<div class="flex items-center gap-2">
                         <span>${this.escapeHtml(item.name)}</span>
                         <span class="inline-flex items-center h-5 text-[10px] leading-none bg-black-700 text-black-300 px-1.5 rounded">Custom</span>
                       </div>`;
                }

                const inputClass = "bg-gray-800 border border-black-700 text-white text-base rounded-lg px-2 py-1.5 w-24 text-right focus:border-white focus:outline-none transition-colors";

                tr.innerHTML = `
                    <td class="px-[3.5rem] py-2.5 align-middle font-medium text-white">${modelNameHtml}</td>
                    <td class="px-4 py-2.5 align-middle text-right">
                        ${this.renderNumberInput(item.pricing.input || 0, '0.5', inputClass, `data-model="${this.escapeHtml(item.id)}" data-field="input"`)}
                    </td>
                    <td class="px-4 py-2.5 align-middle text-right">
                        ${this.renderNumberInput(item.pricing.output || 0, '0.5', inputClass, `data-model="${this.escapeHtml(item.id)}" data-field="output"`)}
                    </td>
                    <td class="px-4 py-2.5 align-middle text-right">
                        ${this.renderNumberInput(item.pricing.caching || 0, '0.05', inputClass, `data-model="${this.escapeHtml(item.id)}" data-field="caching"`)}
                    </td>
                    <td class="px-4 py-2.5 align-middle text-right">
                        ${this.renderNumberInput(item.pricing.request || 0, '0.04', inputClass, `data-model="${this.escapeHtml(item.id)}" data-field="request"`)}
                    </td>
                    <td class="px-4 py-2.5 align-middle text-center">
                        <div class="flex items-center justify-center gap-1" style="height: 2.1rem;">
                            ${isModified ? `
                                <button class="p-1.5 hover:bg-black-700 rounded transition-colors inline-save-btn inline-flex items-center justify-center leading-none" title="Save changes" data-model="${this.escapeHtml(item.id)}">${confirmIcon}</button>
                                <button class="p-1.5 hover:bg-black-700 rounded transition-colors inline-discard-btn inline-flex items-center justify-center leading-none" title="Discard changes" data-model="${this.escapeHtml(item.id)}">${cancelIcon}</button>
                            ` : ''}
                            
                            ${item.isDefault && item.isCustomized && !isModified ?
                        `<button class="text-black-400 hover:text-white transition-colors reset-model-btn p-2 rounded hover:bg-black-700 inline-flex items-center justify-center leading-none" title="Reset to default" data-model="${this.escapeHtml(item.id)}">${resetIcon}</button>`
                        : ''}
                            ${item.isUserOnly && !isModified ?
                        `<button class="text-black-400 hover:text-red-400 transition-colors delete-model-btn p-2 rounded hover:bg-black-700 inline-flex items-center justify-center leading-none" title="Delete" data-model="${this.escapeHtml(item.id)}">${deleteIcon}</button>`
                        : ''}
                        </div>
                    </td>
                `;

                tbody.appendChild(tr);
            });
        });

        if (this.addModelDraft) {
            this.showAddModelDialog();
        }

        // Re - bind listeners
        this.setupTableListeners(tbody);
    }

    setupTableListeners(tbody) {
        tbody.querySelectorAll('[data-provider-toggle]').forEach(row => {
            row.addEventListener('click', (e) => {
                const provider = decodeURIComponent(e.currentTarget.dataset.providerToggle || '');
                if (!provider) return;
                if (this.expandedProviders.has(provider)) {
                    this.expandedProviders.delete(provider);
                } else {
                    this.expandedProviders.add(provider);
                }
                this.renderModelPricingTable();
            });
        });

        // Add event listeners to inputs
        tbody.querySelectorAll('input[data-model]').forEach(input => {
            input.addEventListener('change', (e) => {
                const modelId = e.target.dataset.model;
                const field = e.target.dataset.field;
                const value = parseFloat(e.target.value) || 0;

                if (!this.settings.prices.models[modelId]) {
                    const defaults = this.pricingCatalog.models?.[modelId] || {};
                    this.settings.prices.models[modelId] = { ...defaults };
                }
                this.settings.prices.models[modelId][field] = value;

                // Show floating save button
                this.showSaveButton();
                // Re - render to show reset button if needed
                this.renderModelPricingTable();
            });
        });

        tbody.querySelectorAll('.pricing-step-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const wrapper = e.currentTarget.closest('div.relative');
                const input = wrapper ? wrapper.querySelector('input[data-model]') : null;
                if (!input) return;
                const step = parseFloat(input.step || '1') || 1;
                const direction = e.currentTarget.dataset.stepDir === 'down' ? -1 : 1;
                const current = parseFloat(input.value || '0') || 0;
                const decimals = (input.step.split('.')[1] || '').length;
                input.value = (current + (step * direction)).toFixed(decimals);
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });

        // Inline Save
        tbody.querySelectorAll('.inline-save-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.saveSettings();
            });
        });

        // Inline Discard
        tbody.querySelectorAll('.inline-discard-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modelId = e.currentTarget.dataset.model;
                this.discardModelChanges(modelId);
            });
        });

        // Add delete/reset listeners
        tbody.querySelectorAll('.delete-model-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modelId = e.currentTarget.dataset.model;
                this.deleteModel(modelId);
            });
        });
        tbody.querySelectorAll('.reset-model-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modelId = e.currentTarget.dataset.model;
                this.resetModel(modelId);
            });
        });
    }

    discardModelChanges(modelId) {
        const originalPricing = this.originalSettings.prices?.models?.[modelId];
        if (originalPricing) {
            this.settings.prices.models[modelId] = { ...originalPricing };
        } else {
            // If it wasn't in original, it was either default or just added
            if (this.pricingCatalog.models?.[modelId]) {
                delete this.settings.prices.models[modelId];
            } else {
                // Was likely a newly added custom model?
                // If it's not in originalSettings, and not in catalog, it shouldn't exist?
                // But if it was just added via "Add Model", it *would* be in settings but not original.
                // In that case, discard means delete it?
                delete this.settings.prices.models[modelId];
            }
        }
        this.renderModelPricingTable();
        this.showSaveButton();
    }

    showSaveButton() {
        // Don't show save button if we're currently rendering
        if (this.isRendering) return;

        const btn = document.getElementById('settings-save-btn');
        if (btn) {
            if (this.hasUnsavedChanges()) {
                btn.classList.remove('hidden');
            } else {
                btn.classList.add('hidden');
            }
        }
    }

    hideSaveButton() {
        const btn = document.getElementById('settings-save-btn');
        if (btn) btn.classList.add('hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async saveSettings() {
        try {
            // console.log('[Settings] Saving settings...');
            const result = await window.api.saveSettings(this.settings);
            // console.log('[Settings] Save result:', result);
            if (result.success) {
                this.showSuccess('Settings saved successfully');
                this.originalSettings = JSON.parse(JSON.stringify(this.settings));
                const btn = document.getElementById('settings-save-btn');
                if (btn) btn.classList.add('hidden');
                // console.log('[Settings] Dispatching settingsUpdated event');
                window.dispatchEvent(new CustomEvent('settingsUpdated', { detail: this.settings }));
                this.renderModelPricingTable(); // // Added to refresh inline buttons
            } else {
                this.showError('Failed to save settings: ' + result.error);
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showError('Error saving settings');
        }
    }

    async resetToDefaults() {
        const confirmed = await window.DialogManager.confirm(
            'Reset all settings to default values? This cannot be undone.',
            { title: 'Reset All Settings', confirmText: 'Reset All', dangerous: true }
        );
        if (!confirmed) return;

        try {
            const result = await window.api.reset_all_models_to_default();
            if (result.success) {
                await this.loadSettings();
                this.hideSaveButton();
                this.showSuccess('Settings reset to defaults');
            } else {
                this.showError('Failed to reset settings');
            }
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showError('Error resetting settings');
        }
    }

    showAddModelDialog() {
        const tbody = document.getElementById('model-pricing-table');
        if (!tbody) return;

        // Check if add row already exists
        if (document.getElementById('add-model-row')) {
            document.getElementById('new_provider_id').focus();
            return;
        }

        if (!this.addModelDraft) {
            this.addModelDraft = {
                provider: '',
                model: '',
                input: 0,
                output: 0,
                caching: 0,
                request: 0,
            };
        }

        const tr = document.createElement('tr');
        tr.id = 'add-model-row';
        tr.className = 'bg-black-800/80';

        const inputClass = "bg-black-900 border border-black-700 text-white text-base rounded-lg px-2 py-1.5 focus:border-white focus:outline-none transition-colors";
        const numberInputClass = "bg-black-900 border border-black-700 text-white text-base rounded-lg px-2 py-1.5 w-24 text-right focus:border-white focus:outline-none transition-colors";

        const confirmIcon = `<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
        const cancelIcon = `<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`;

        tr.innerHTML = `
            <td class="px-[3.5rem] py-2.5 align-middle">
                <div class="flex items-center gap-2">
                    <input type="text" id="new_provider_id" placeholder="Provider" class="${inputClass}" style="flex: 0 0 30%; width: 30%;" value="${this.escapeHtml(this.addModelDraft.provider)}">
                    <input type="text" id="new_model_id" placeholder="Model ID" class="${inputClass}" style="flex: 0 0 70%; width: 70%;" value="${this.escapeHtml(this.addModelDraft.model)}">
                </div>
            </td>
            <td class="px-4 py-2.5 align-middle text-right">
                ${this.renderNumberInput(this.addModelDraft.input, '0.01', numberInputClass, 'id="new_input_cost" placeholder="0.00"')}
            </td>
            <td class="px-4 py-2.5 align-middle text-right">
                ${this.renderNumberInput(this.addModelDraft.output, '0.01', numberInputClass, 'id="new_output_cost" placeholder="0.00"')}
            </td>
            <td class="px-4 py-2.5 align-middle text-right">
                ${this.renderNumberInput(this.addModelDraft.caching, '0.01', numberInputClass, 'id="new_cache_cost" placeholder="0.00"')}
            </td>
            <td class="px-4 py-2.5 align-middle text-right">
                ${this.renderNumberInput(this.addModelDraft.request, '0.0001', numberInputClass, 'id="new_request_cost" placeholder="0.00"')}
            </td>
            <td class="px-4 py-2.5 align-middle text-center">
                <div class="flex items-center justify-center gap-2" style="height: 2.1rem;">
                    <button id="confirm-add-btn" class="p-1 hover:bg-black-700 rounded transition-colors" title="Add Model">${confirmIcon}</button>
                    <button id="cancel-add-btn" class="p-1 hover:bg-black-700 rounded transition-colors" title="Cancel">${cancelIcon}</button>
                </div>
            </td>
        `;

        // Insert as first row
        tbody.insertBefore(tr, tbody.firstChild);

        // Focus only for first open
        if (!this.addModelDraft.provider && !this.addModelDraft.model) {
            document.getElementById('new_provider_id').focus();
        }

        const syncAddModelDraft = () => {
            this.addModelDraft = {
                provider: document.getElementById('new_provider_id')?.value?.trim() || '',
                model: document.getElementById('new_model_id')?.value?.trim() || '',
                input: parseFloat(document.getElementById('new_input_cost')?.value) || 0,
                output: parseFloat(document.getElementById('new_output_cost')?.value) || 0,
                caching: parseFloat(document.getElementById('new_cache_cost')?.value) || 0,
                request: parseFloat(document.getElementById('new_request_cost')?.value) || 0,
            };
        };

        ['new_provider_id', 'new_model_id', 'new_input_cost', 'new_output_cost', 'new_cache_cost', 'new_request_cost'].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', syncAddModelDraft);
            el.addEventListener('change', syncAddModelDraft);
        });

        // Listeners for this row
        document.getElementById('cancel-add-btn').addEventListener('click', () => {
            this.addModelDraft = null;
            tr.remove();
        });

        tr.querySelectorAll('.pricing-step-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const wrapper = e.currentTarget.closest('div.relative');
                const input = wrapper ? wrapper.querySelector('input[type="number"]') : null;
                if (!input) return;
                const step = parseFloat(input.step || '1') || 1;
                const direction = e.currentTarget.dataset.stepDir === 'down' ? -1 : 1;
                const current = parseFloat(input.value || '0') || 0;
                const decimals = (input.step.split('.')[1] || '').length;
                input.value = (current + (step * direction)).toFixed(decimals);
            });
        });

        document.getElementById('confirm-add-btn').addEventListener('click', () => {
            syncAddModelDraft();
            const provider = document.getElementById('new_provider_id').value.trim();
            const model = document.getElementById('new_model_id').value.trim();

            if (!provider || !model) {
                this.showError('Provider and Model ID are required');
                return;
            }

            const modelId = `${provider}/${model}`;
            if (this.settings.prices.models[modelId] || this.pricingCatalog.models[modelId]) {
                this.showError('Model ID already exists');
                return;
            }

            // Add to settings
            this.settings.prices.models[modelId] = {
                input: parseFloat(document.getElementById('new_input_cost').value) || 0,
                output: parseFloat(document.getElementById('new_output_cost').value) || 0,
                caching: parseFloat(document.getElementById('new_cache_cost').value) || 0,
                request: parseFloat(document.getElementById('new_request_cost').value) || 0,
                provider: provider
            };

            this.addModelDraft = null;

            // Auto - save when confirming model addition
            this.saveSettings();
            this.renderModelPricingTable();
            this.showSuccess(`Added ${modelId}`);
        });

        // Handle Enter key
        tr.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('confirm-add-btn').click();
            }
            if (e.key === 'Escape') {
                tr.remove();
            }
        });
    }

    async deleteModel(modelId) {
        const confirmed = await window.DialogManager.confirm(
            `Delete pricing for ${modelId}?`,
            { title: 'Delete Model', confirmText: 'Delete', dangerous: true }
        );
        if (!confirmed) return;

        if (this.settings.prices?.models?.[modelId]) {
            delete this.settings.prices.models[modelId];
            // Auto - save when deleting model
            await this.saveSettings();
            this.renderModelPricingTable();
        }
    }

    async resetModel(modelId) {
        const confirmed = await window.DialogManager.confirm(
            `Reset ${modelId} to default pricing?`,
            { title: 'Reset Model', confirmText: 'Reset' }
        );
        if (!confirmed) return;

        if (this.settings.prices?.models?.[modelId]) {
            delete this.settings.prices.models[modelId];
            // Auto - save when resetting model
            await this.saveSettings();
            this.renderModelPricingTable();
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
        const bgColor = type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600';

        toast.className = `fixed bottom-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

window.settingsManager = new SettingsManager();
