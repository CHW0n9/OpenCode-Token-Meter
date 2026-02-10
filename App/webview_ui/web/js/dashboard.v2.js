class Dashboard {
    constructor() {
        this.stats = null;
        this.currentScope = 'today';
        this.currentDistributionMetric = 'requests'; // Default to Requests
        this.currentTrendMetric = 'cost'; // Default to Cost
        this.currentDetailsView = 'all'; // 'all' | 'provider' | 'model'
        this.refreshTimer = null;
        this.refreshInterval = 5; // Fixed 5s
    }

    async init() {
        console.log('[Dashboard] init() called');

        // Initialize scope from settings (if available) or DOM default
        if (window.settingsManager && window.settingsManager.settings && window.settingsManager.settings.default_time_scope) {
            this.currentScope = window.settingsManager.settings.default_time_scope;
            // Update the dropdown to match
            const scopeSelect = document.getElementById('scope-select');
            if (scopeSelect) {
                scopeSelect.value = this.currentScope;
            }
        } else {
            const scopeSelect = document.getElementById('scope-select');
            if (scopeSelect) {
                this.currentScope = scopeSelect.value;
            }
        }

        // Listener for settings updates - attached immediately
        console.log('[Dashboard] Setting up settingsUpdated listener');
        window.addEventListener('settingsUpdated', async (event) => {
            console.log('[Dashboard] settingsUpdated event received!', event.detail);
            // Reload stats and thresholds to reflect new settings (currency, costs, thresholds)
            await this.loadStats();
            console.log('[Dashboard] Stats reloaded after settings update');

            // If we are in Details view, we need to refresh that too
            const detailsSection = document.getElementById('details-section');
            if (detailsSection && !detailsSection.classList.contains('hidden')) {
                console.log('Refreshing details view after settings update');
                await this.renderDetailsView();
            }
        });

        await this.loadStats();
        this.setupMetricListener();
        this.setupTrendMetricListener();
        await this.setupAutoRefresh();
    }

    // ... (auto refresh code remains same)

    setupMetricListener() {
        const select = document.getElementById('distribution-metric');
        if (select) {
            select.addEventListener('change', (e) => {
                this.currentDistributionMetric = e.target.value;
                this.updateDistributionChart();
            });
        }
    }

    setupTrendMetricListener() {
        const select = document.getElementById('trend-metric');
        if (select) {
            select.addEventListener('change', (e) => {
                this.currentTrendMetric = e.target.value;
                this.updateTrendChart();
            });
        }
    }

    async setupAutoRefresh() {
        // Clear existing timer
        if (this.refreshTimer) clearInterval(this.refreshTimer);

        // Smart Polling: Check every 1s for updates
        // This is lightweight. If update needed, we load stats.
        console.log(`[Dashboard] Starting smart polling (1s check)`);

        let lastTs = 0;

        // Initial sync of timestamp
        const initCheck = await window.api.checkUpdates(0);
        if (initCheck.success && initCheck.data) {
            lastTs = initCheck.data.ts;
        }

        this.refreshTimer = setInterval(async () => {
            try {
                const check = await window.api.checkUpdates(lastTs);
                if (check.success && check.data.needed) {
                    console.log('[Dashboard] Update detected, reloading stats...');
                    lastTs = check.data.ts;
                    await this.loadStats();
                }
            } catch (e) {
                console.error("Smart polling error:", e);
            }
        }, 1000);
    }

    async loadStats(scope = null) {
        if (scope) this.currentScope = scope;

        const result = await window.api.getStats(this.currentScope);

        if (result.success) {
            this.stats = result.data;
            this.render();
            this.updateLastRefresh();
            await this.loadThresholds();
        } else {
            console.error('Failed to load stats:', result.error);
            this.stats = null;
            this.renderEmpty();
            await this.loadThresholds();
        }
    }

    render() {
        if (!this.stats) return;

        this.renderCards();
        this.renderCharts();
        this.renderTable();
    }

    renderCards() {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        const s = this.stats;
        setVal('stat-input', window.formatCompactNumber(s.total_input_tokens));
        const totalOutput = s.total_output_tokens || 0;
        setVal('stat-output', window.formatCompactNumber(totalOutput));
        setVal('stat-requests', window.formatCompactNumber(s.request_count));
        setVal('stat-cost', this.formatCost2(s.total_cost));
    }

    renderEmpty() {
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setVal('stat-input', '--');
        setVal('stat-output', '--');
        setVal('stat-requests', '--');
        setVal('stat-cost', '$0.00');

        // Clear charts if they exist
        if (window.chartManager) {
            // Optional: reset charts to empty state if supported, or just leave them
        }

        this.renderTable();
    }


    renderCharts() {
        if (window.chartManager) {
            this.updateTrendChart();
            this.updateDistributionChart();
        }
    }

    updateTrendChart() {
        if (!window.chartManager || !this.stats || !this.stats.trend) return;

        // Prepare data based on metric
        const trendData = this.getTrendData(this.currentTrendMetric);
        window.chartManager.initTrendChart('trend-chart', trendData, this.currentTrendMetric);
    }

    getTrendData(metric) {
        // Trend data structure from backend: { labels: [], cost: [], input: [], output: [], reasoning: [], requests: [] }

        const t = this.stats.trend;
        if (!t) return { labels: [], values: [] };

        let values = [];
        switch (metric) {
            case 'cost': values = t.cost || []; break;
            case 'total_tokens':
                // Backend doesn't send total, so sum them up. 
                // Wait, t.input is array. We need to map.
                if (t.input && t.output) {
                    values = t.input.map((v, i) => v + (t.output[i] || 0) + (t.reasoning[i] || 0));
                }
                break;
            case 'input_tokens': values = t.input || []; break;
            case 'output_tokens':
                // Output tokens should include reasoning? Backend api.py: t.output + t.reasoning?
                // In api.py I see: data_output.append(s["output"]), data_reasoning.append(s["reasoning"])
                // So here we should sum them if we want "Output + Reasoning".
                if (t.output) {
                    values = t.output.map((v, i) => v + (t.reasoning[i] || 0));
                }
                break;
            case 'requests': values = t.requests || []; break;
            default: values = t.cost || [];
        }

        return {
            labels: t.labels || [],
            values: values
        };
    }

    updateDistributionChart() {
        if (!window.chartManager || !this.stats) return;

        const data = this.getDistributionData(this.currentDistributionMetric);
        window.chartManager.initDistributionChart('distribution-chart', data);
    }

    getDistributionData(metric) {
        if (!this.stats || !this.stats.providers) return { labels: [], values: [], meta: [] };

        let items = this.stats.providers.map(p => {
            let val = 0;
            const outputWithReasoning = (p.output || 0);

            switch (metric) {
                case 'cost': val = p.cost; break;
                case 'input_tokens': val = p.input; break;
                case 'output_tokens': val = outputWithReasoning; break;
                case 'total_tokens': val = p.input + outputWithReasoning; break;
                case 'requests': val = p.requests; break;
                default: val = p.cost;
            }
            return {
                provider: p.name,
                model: p.model,
                value: val,
                original: p
            };
        }).filter(item => item.value > 0);

        // Sort by Provider first (grouping), then by Value DESC
        items.sort((a, b) => {
            if (a.provider < b.provider) return -1;
            if (a.provider > b.provider) return 1;
            return b.value - a.value;
        });

        const total = items.reduce((sum, item) => sum + item.value, 0);

        const labels = items.map(i => i.model);
        const values = items.map(i => i.value);
        const meta = items.map(i => {
            let fmtVal = '';
            if (metric === 'cost') fmtVal = this.formatCurrency(i.value);
            else fmtVal = window.formatCompactNumber(i.value); // add ' Tok'?

            return {
                provider: i.provider,
                model: i.model,
                percentage: total > 0 ? ((i.value / total) * 100).toFixed(1) : 0,
                requests: i.original.requests,
                formattedValue: fmtVal
            };
        });

        return { labels, values, meta };
    }

    renderTable() {
        const tbody = document.getElementById('providers-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        let providers = [];
        if (this.stats && this.stats.providers) {
            providers = [...this.stats.providers];
        }

        if (providers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-8 text-center text-black-400">
                        No data available
                    </td>
                </tr>
            `;
            return;
        }

        // Rank by Request Count (DESC)
        // Grouped by Provider: Providers with more total requests come first.
        const providerTotals = {};
        providers.forEach(p => {
            providerTotals[p.name] = (providerTotals[p.name] || 0) + p.requests;
        });

        providers.sort((a, b) => {
            // Primary: Provider's total requests (DESC)
            const diff = providerTotals[b.name] - providerTotals[a.name];
            if (diff !== 0) return diff;

            // Secondary: Same provider, rank models by requests (DESC)
            if (a.name === b.name) {
                return b.requests - a.requests;
            }

            // Tertiary: Alphabetical provider if requests exact match
            return a.name.localeCompare(b.name);
        });

        let lastProvider = null;

        providers.forEach((p, index) => {
            // Insert empty line between different providers
            if (lastProvider !== null && p.name !== lastProvider) {
                const spacer = document.createElement('tr');
                spacer.className = 'h-4 bg-black-950/20'; // Spacer row
                spacer.innerHTML = '<td colspan="5"></td>';
                tbody.appendChild(spacer);
            }

            const tr = document.createElement('tr');
            tr.className = 'border-b border-black-700 hover:bg-black-800/50 transition-colors';

            const showProvider = p.name !== lastProvider;

            tr.innerHTML = `
                <td class="px-6 py-4 font-bold text-white">
                    ${showProvider ? this.escapeHtml(p.name) : ''}
                </td>
                <td class="px-6 py-4 text-white">
                    ${this.escapeHtml(p.model)}
                </td>
                <td class="px-6 py-4 text-black-300">
                    <span class="text-black-500">In:</span> ${window.formatCompactNumber(p.input)}
                    <span class="text-black-500 ml-2">Out:</span> ${window.formatCompactNumber(p.output)}
                </td>
                <td class="px-6 py-4 text-right text-black-300">
                    ${window.formatCompactNumber(p.requests)}
                </td>
                <td class="px-6 py-4 text-right font-medium text-white">
                    ${this.formatCurrency(p.cost)}
                </td>
            `;
            tbody.appendChild(tr);
            lastProvider = p.name;
        });
    }

    updateLastRefresh() {
        const el = document.getElementById('last-refresh');
        if (el) {
            const now = new Date();
            el.textContent = `Updated: ${now.toLocaleTimeString()}`;
        }
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    formatCurrency(num) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num);
    }

    formatCost2(num) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num);
    }



    async loadThresholds() {
        const result = await window.api.getThresholdsProgress();
        if (!result.success || !result.data) {
            this.setThresholdVisibility(false);
            return;
        }
        const data = result.data;
        this.setThresholdVisibility(!!data.enabled);
        if (!data.enabled) return;
        this.updateThresholdBars(data);
    }

    setThresholdVisibility(enabled) {
        const tokenCard = document.getElementById('card-token-threshold');
        const costCard = document.getElementById('card-cost-threshold');
        if (tokenCard) tokenCard.classList.toggle('hidden', !enabled);
        if (costCard) costCard.classList.toggle('hidden', !enabled);
    }

    updateThresholdBars(data) {
        this._setProgress('token-threshold-today', data.today?.token_pct, data.today?.tokens, data.today?.token_threshold, 'Tokens');
        this._setProgress('token-threshold-month', data.month?.token_pct, data.month?.tokens, data.month?.token_threshold, 'Tokens');
        this._setProgress('cost-threshold-today', data.today?.cost_pct, data.today?.cost, data.today?.cost_threshold, 'Cost');
        this._setProgress('cost-threshold-month', data.month?.cost_pct, data.month?.cost, data.month?.cost_threshold, 'Cost');
    }

    _setProgress(prefix, pct, current, threshold, type) {
        const label = document.getElementById(`${prefix}-pct`);
        const bar = document.getElementById(`${prefix}-bar`);
        const value = Number.isFinite(Number(pct)) ? Number(pct) : 0;
        const width = Math.min(100, Math.max(0, value));

        if (label) label.textContent = `${value}%`;

        if (bar) {
            bar.style.width = `${width}%`;

            // Color logic: <50% White, 50-80% Yellow, 80-100% Orange, >100% Red
            let colorClass = 'bg-white';
            if (value > 100) {
                colorClass = 'bg-red-500';
            } else if (value >= 80) {
                colorClass = 'bg-orange-500';
            } else if (value >= 50) {
                colorClass = 'bg-yellow-500';
            }

            // Update classes
            bar.className = `h-full rounded-full transition-all duration-500 ${colorClass}`;

            // Add tooltip using data-tooltip attribute for custom tooltip handler
            if (current !== undefined && threshold !== undefined) {
                let currentStr, thresholdStr;
                if (type === 'Cost') {
                    currentStr = this.formatCurrency(current);
                    thresholdStr = this.formatCurrency(threshold);
                } else {
                    currentStr = window.formatCompactNumber(current);
                    thresholdStr = window.formatCompactNumber(threshold);
                }
                const tooltipText = `${type}: ${currentStr} / ${thresholdStr} (${value}%)`;

                // Set on Bar Track (Parent of bar)
                bar.parentElement.removeAttribute('title'); // Ensure no native tooltip
                bar.parentElement.dataset.tooltip = tooltipText;

                // Set on Label Row (Parent of label span)
                if (label && label.parentElement) {
                    label.parentElement.removeAttribute('title');
                    label.parentElement.dataset.tooltip = tooltipText;
                }
            }
        }
    }

    // ========== DETAILS VIEW METHODS ==========

    async renderDetailsView(viewMode = null, scope = null, startTs = null, endTs = null) {
        console.log('renderDetailsView called with:', { viewMode, scope, startTs, endTs });
        if (viewMode) this.currentDetailsView = viewMode;
        if (scope) this.currentDetailsScope = scope;
        this.customStartTs = startTs;
        this.customEndTs = endTs;
        console.log('renderDetailsView - after assignment:', {
            currentDetailsView: this.currentDetailsView,
            currentDetailsScope: this.currentDetailsScope,
            customStartTs: this.customStartTs,
            customEndTs: this.customEndTs
        });

        // Update button states
        document.querySelectorAll('.details-view-btn').forEach(btn => {
            const mode = btn.dataset.mode;
            if (mode === this.currentDetailsView) {
                btn.classList.add('bg-black-700', 'text-white');
                btn.classList.remove('text-black-400');
            } else {
                btn.classList.remove('bg-black-700', 'text-white');
                btn.classList.add('text-black-400');
            }
        });

        // Render based on mode
        switch (this.currentDetailsView) {
            case 'all':
                await this.renderDetailsAll();
                break;
            case 'provider':
                await this.renderDetailsByProvider();
                break;
            case 'model':
                await this.renderDetailsByModel();
                break;
        }
    }

    async renderDetailsAll() {
        console.log('renderDetailsAll started');
        console.log('renderDetailsAll - currentDetailsScope:', this.currentDetailsScope);
        console.log('renderDetailsAll - customStartTs:', this.customStartTs, 'customEndTs:', this.customEndTs);
        const tbody = document.getElementById('details-table-body');
        if (!tbody) {
            console.error('details-table-body not found');
            return;
        }

        // If custom range is set, show only that range
        if (this.currentDetailsScope === 'custom' && this.customStartTs && this.customEndTs) {
            console.log('renderDetailsAll - Calling getStatsRange with:', this.customStartTs, this.customEndTs);
            const result = await window.api.getStatsRange(this.customStartTs, this.customEndTs);
            console.log('renderDetailsAll - getStatsRange result:', result);
            const startDate = new Date(this.customStartTs * 1000);
            const endDate = new Date(this.customEndTs * 1000);
            const label = `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;

            let rows = '';
            if (result.success && result.data) {
                const s = result.data;
                const totalOutput = (s.total_output_tokens || 0);
                rows = `
                    <tr class="hover:bg-black-700/30 transition-colors">
                        <td class="px-4 py-3 font-medium text-white">${label}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_input_tokens || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(totalOutput)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_cache_read_tokens || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_cache_write_tokens || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.message_count || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.request_count || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${this.formatCost2(s.total_cost || 0)}</td>
                    </tr>
                `;
            } else {
                console.error('renderDetailsAll - getStatsRange failed:', result.error);
                rows = `<tr><td class="px-4 py-3 font-medium text-white">${label}</td>${Array(7).fill('<td class="px-4 py-3 text-right text-black-400">N/A</td>').join('')}</tr>`;
            }
            tbody.innerHTML = rows;
            return;
        }

        const scopes = [
            { key: 'today', label: 'Today' },
            { key: 'week', label: 'Last 7 Days' },
            { key: 'month', label: 'This Month' },
            { key: 'all', label: 'All Time' }
        ];

        let rows = '';
        for (const scope of scopes) {
            console.log(`Fetching stats for ${scope.key}`);
            const result = await window.api.getStats(scope.key);
            console.log(`Stats result for ${scope.key}:`, result);
            if (!result.success || !result.data) {
                console.warn(`Failed to load stats for ${scope.key}:`, result.error);
                rows += `
                    <tr>
                        <td class="px-4 py-3 font-medium text-white">${scope.label}</td>
                        ${Array(7).fill('<td class="px-4 py-3 text-right text-black-400">N/A</td>').join('')}
                    </tr>
                `;
                continue;
            }

            const s = result.data;
            const totalOutput = (s.total_output_tokens || 0);

            rows += `
                <tr class="hover:bg-black-700/30 transition-colors">
                    <td class="px-4 py-3 font-medium text-white">${scope.label}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_input_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(totalOutput)}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_cache_read_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.total_cache_write_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.message_count || 0)}</td>
                    <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(s.request_count || 0)}</td>
                    <td class="px-4 py-3 text-right text-white">${this.formatCost2(s.total_cost || 0)}</td>
                </tr>
            `;
        }

        tbody.innerHTML = rows || '<tr><td colspan="8" class="px-6 py-8 text-center text-black-400">No data available</td></tr>';
    }

    async renderDetailsByProvider() {
        const tbody = document.getElementById('details-table-body');
        if (!tbody) return;

        // Get selected scope from unified time selector
        const currentScope = this.currentDetailsScope || 'month';

        let scopeLabel = '';
        if (currentScope === 'custom' && this.customStartTs && this.customEndTs) {
            const startDate = new Date(this.customStartTs * 1000);
            const endDate = new Date(this.customEndTs * 1000);
            scopeLabel = `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;
        } else {
            const scopeLabels = {
                'today': 'Today',
                'week': 'Last 7 Days',
                'month': 'This Month',
                'all': 'All Time'
            };
            scopeLabel = scopeLabels[currentScope] || currentScope;
        }

        let rows = '';

        // Use custom range APIs when scope is 'custom', otherwise use scope-based APIs
        let statsResult, providerResult;
        if (currentScope === 'custom' && this.customStartTs && this.customEndTs) {
            [statsResult, providerResult] = await Promise.all([
                window.api.getStatsRange(this.customStartTs, this.customEndTs),
                window.api.getStatsByProviderRange(this.customStartTs, this.customEndTs)
            ]);
        } else {
            [statsResult, providerResult] = await Promise.all([
                window.api.getStats(currentScope),
                window.api.getStatsByProvider(currentScope)
            ]);
        }

        // Scope header with totals (bold)
        if (statsResult.success && statsResult.data) {
            const s = statsResult.data;
            const totalOutput = (s.total_output_tokens || 0);
            rows += `
                <tr class="bg-black-900/50">
                    <td class="px-4 py-3 font-bold text-white text-base">${scopeLabel}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(s.total_input_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(totalOutput)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(s.total_cache_read_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(s.total_cache_write_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(s.message_count || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${window.formatCompactNumber(s.request_count || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white">${this.formatCost2(s.total_cost || 0)}</td>
                </tr>
            `;
        } else {
            rows += `<tr class="bg-black-900/50"><td class="px-4 py-3 font-bold text-white" colspan="8">${scopeLabel}</td></tr>`;
        }

        // Provider rows (indented) - Rank by Requests DESC
        if (providerResult.success && providerResult.data) {
            const providers = Object.entries(providerResult.data).sort((a, b) => (b[1].requests || 0) - (a[1].requests || 0));
            for (const [provider, stats] of providers) {
                const totalOutput = (stats.output || 0) + (stats.reasoning || 0);
                rows += `
                    <tr class="hover:bg-black-700/20 transition-colors">
                        <td class="px-4 py-3 pl-8 text-white">${this.escapeHtml(provider)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.input || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(totalOutput)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.cache_read || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.cache_write || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.messages || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.requests || 0)}</td>
                        <td class="px-4 py-3 text-right text-white">${this.formatCost2(stats.cost || 0)}</td>
                    </tr>
                `;
            }
        }

        tbody.innerHTML = rows || '<tr><td colspan="8" class="px-6 py-8 text-center text-black-400">No data available</td></tr>';
    }

    async renderDetailsByModel() {
        const tbody = document.getElementById('details-table-body');
        if (!tbody) return;

        // Get selected scope from unified time selector (same as renderDetailsByProvider)
        const currentScope = this.currentDetailsScope || 'month';

        let scopeLabel = '';
        if (currentScope === 'custom' && this.customStartTs && this.customEndTs) {
            const startDate = new Date(this.customStartTs * 1000);
            const endDate = new Date(this.customEndTs * 1000);
            scopeLabel = `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;
        } else {
            const scopeLabels = {
                'today': 'Today',
                'week': 'Last 7 Days',
                'month': 'This Month',
                'all': 'All Time'
            };
            scopeLabel = scopeLabels[currentScope] || currentScope;
        }

        let rows = '';

        // Use custom range APIs when scope is 'custom', otherwise use scope-based APIs
        let statsResult, modelResult;
        if (currentScope === 'custom' && this.customStartTs && this.customEndTs) {
            [statsResult, modelResult] = await Promise.all([
                window.api.getStatsRange(this.customStartTs, this.customEndTs),
                window.api.getStatsByModelRange(this.customStartTs, this.customEndTs)
            ]);
        } else {
            [statsResult, modelResult] = await Promise.all([
                window.api.getStats(currentScope),
                window.api.getStatsByModel(currentScope)
            ]);
        }

        // Scope header with totals (bold, larger)
        if (statsResult.success && statsResult.data) {
            const s = statsResult.data;
            const totalOutput = (s.total_output_tokens || 0);
            rows += `
                <tr class="bg-black-900/70">
                    <td class="px-4 py-3 font-bold text-white text-lg">${scopeLabel}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(s.total_input_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(totalOutput)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(s.total_cache_read_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(s.total_cache_write_tokens || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(s.message_count || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${window.formatCompactNumber(s.request_count || 0)}</td>
                    <td class="px-4 py-3 text-right font-bold text-white text-base">${this.formatCost2(s.total_cost || 0)}</td>
                </tr>
            `;
        } else {
            rows += `<tr class="bg-black-900/70"><td class="px-4 py-3 font-bold text-white text-lg" colspan="8">${scopeLabel}</td></tr>`;
        }

        // Provider & Model rows  (hierarchical: provider bold, model double-indented)
        if (modelResult.success && modelResult.data) {
            // First, calculate total requests per provider to rank providers
            const providerEntries = Object.entries(modelResult.data).map(([name, models]) => {
                const totalReq = Object.values(models).reduce((sum, m) => sum + (m.requests || 0), 0);
                return { name, models, totalReq };
            });

            // Rank providers by total requests DESC
            providerEntries.sort((a, b) => b.totalReq - a.totalReq);

            for (const { name: provider, models } of providerEntries) {
                // Provider subheader (bold, indented once)
                rows += `
                    <tr class="bg-black-900/30">
                        <td class="px-4 py-3 pl-6 font-bold text-white" colspan="8">${this.escapeHtml(provider)}</td>
                    </tr>
                `;

                // Model rows (double-indented) - Rank by requests DESC
                const modelEntries = Object.entries(models).sort((a, b) => (b[1].requests || 0) - (a[1].requests || 0));
                for (const [model, stats] of modelEntries) {
                    const totalOutput = (stats.output || 0) + (stats.reasoning || 0);
                    rows += `
                        <tr class="hover:bg-black-700/10 transition-colors">
                            <td class="px-4 py-3 pl-12 text-black-400 text-sm italic">${this.escapeHtml(model)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.input || 0)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(totalOutput)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.cache_read || 0)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.cache_write || 0)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.messages || 0)}</td>
                            <td class="px-4 py-3 text-right text-white">${window.formatCompactNumber(stats.requests || 0)}</td>
                            <td class="px-4 py-3 text-right text-white">${this.formatCost2(stats.cost || 0)}</td>
                        </tr>
                    `;
                }
            }
        }

        tbody.innerHTML = rows || '<tr><td colspan="8" class="px-6 py-8 text-center text-black-400">No data available</td></tr>';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

window.dashboard = new Dashboard();
