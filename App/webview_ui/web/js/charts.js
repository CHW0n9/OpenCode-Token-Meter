class ChartManager {
    constructor() {
        this.trendChart = null;
        this.distributionChart = null;

        // Monochrome/Grayscale chart colors
        this.monochromeColors = [
            '#e2e8f0', // slate-200
            '#94a3b8', // slate-400
            '#64748b', // slate-500
            '#475569', // slate-600
            '#334155', // slate-700
            '#1e293b', // slate-800
            '#0f172a', // slate-900
            '#f8fafc', // slate-50
        ];
    }

    // Helper to get scaled font size (mimics rem)
    getScaledSize(rem) {
        const rootSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
        return rem * rootSize;
    }

    initTrendChart(canvasId, data, metric = 'cost') {
        if (!window.Chart) return;
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        if (this.trendChart && typeof this.trendChart.destroy === 'function') {
            this.trendChart.destroy();
        }

        const ctx = canvas.getContext('2d');


        // Handle no data case: draw a flat line at Y=0
        // Allow data if we have values array, even if all 0 
        const hasData = data && data.values && data.values.length > 0;
        const labels = hasData ? data.labels : [''];
        const values = hasData ? data.values : [0];

        // Format helpers based on metric
        let labelPrefix = '';
        let labelSuffix = '';
        let tooltipCallback = null;
        let axisCallback = null;

        if (metric === 'cost') {
            labelPrefix = '$';
            tooltipCallback = (val) => `$${Number(val).toFixed(4)}`;
            axisCallback = (val) => '$' + val;
        } else {
            // Tokens or Requests
            labelPrefix = '';
            tooltipCallback = (val) => window.formatCompactNumber(val);
            axisCallback = (val) => window.formatCompactNumber(val);
        }

        // Gradient for the line fill - white/gray
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.2)');
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: metric.replace('_', ' ').toUpperCase(),
                    data: values,
                    borderColor: '#e2e8f0', // slate-200 (white-ish)
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4, // Smooth curve
                    pointBackgroundColor: '#0f172a', // slate-900 (dark bg)
                    pointBorderColor: '#e2e8f0', // slate-200
                    pointHoverBackgroundColor: '#e2e8f0',
                    pointHoverBorderColor: '#0f172a',
                    pointRadius: hasData ? 3 : 0,
                    pointHoverRadius: hasData ? 5 : 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: false },
                    tooltip: {
                        enabled: hasData,
                        backgroundColor: '#262626',
                        titleColor: '#888888',
                        bodyColor: '#ffffff',
                        borderColor: '#525252',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 4,
                        displayColors: false, // Don't show the color box
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed?.y ?? 0;
                                return tooltipCallback(value);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(51, 65, 85, 0.2)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#ffffff', // white
                            font: { size: this.getScaledSize(0.8) } // Level S/Base equivalent
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        suggestedMax: hasData ? undefined : 1,
                        grid: {
                            color: 'rgba(51, 65, 85, 0.2)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#ffffff', // white
                            font: { size: this.getScaledSize(0.8) }, // Level S/Base equivalent
                            callback: function (value) {
                                return axisCallback(value);
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                }
            }
        });
    }

    initDistributionChart(canvasId, data) {
        if (!window.Chart) return;
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (this.distributionChart && typeof this.distributionChart.destroy === 'function') {
            this.distributionChart.destroy();
        }

        const hasData = data && data.values && data.values.length > 0;

        // Process data to insert gaps between providers
        let processedLabels = [];
        let processedValues = [];
        let processedColors = [];
        let processedMeta = [];
        let processedBorderWidths = [];
        let processedBorderColors = [];

        if (hasData) {
            const totalValue = data.values.reduce((a, b) => a + b, 0);
            const gapValue = totalValue * 0.03; // // 3% gap (larger explosion)

            let lastProvider = null;

            // Assume input data is sorted by provider implicitly or we iterate linearly
            // If strictly needed, we should sort by provider first, but let's respect input order
            // and just separate when provider changes.

            // First pass: count providers and slices per provider to assign hues correctly
            const providerInfo = {};
            data.meta.forEach(m => {
                if (!providerInfo[m.provider]) providerInfo[m.provider] = 0;
                providerInfo[m.provider]++;
            });

            const providerHues = [210, 160, 45, 270, 340, 190, 25]; // // Blue, Green, Amber, Purple, Pink, Cyan, Orange
            let currentProviderIndex = -1;
            let slicesInCurrentProvider = 0;

            data.values.forEach((val, i) => {
                const meta = data.meta[i];

                // If provider changes (and not the first item), insert a gap
                if (lastProvider && meta.provider !== lastProvider) {
                    processedLabels.push('Gap');
                    processedValues.push(gapValue);
                    processedColors.push('rgba(0,0,0,0)'); // // Transparent
                    processedMeta.push(null); // // No meta for gap
                    processedBorderWidths.push(0);
                    processedBorderColors.push('rgba(0,0,0,0)');
                    slicesInCurrentProvider = 0;
                }

                if (meta.provider !== lastProvider) {
                    currentProviderIndex++;
                }

                processedLabels.push(data.labels[i]);
                processedValues.push(val);

                // Unified Color Logic
                const sliceCount = providerInfo[meta.provider];
                const step = sliceCount > 1 ? (20 / (sliceCount)) : 0;
                let lightness = 50 - (slicesInCurrentProvider * step); // // 50% down to 30%

                let hue = providerHues[currentProviderIndex % providerHues.length];
                let sat = 90; // // Default reduced saturation

                // Fixed Brand Colors
                const pName = meta.provider.toUpperCase();
                if (pName.includes('GOOGLE')) hue = 5; // // Red
                else if (pName.includes('OPENCODE')) {
                    hue = 0;
                    sat = 0; // Grayscale
                }
                else if (pName.includes('NVIDIA')) hue = 140; // Green (Nvidia Green is 150ish)
                else if (pName.includes('ANTHROPIC')) hue = 25; // Orange
                else if (pName.includes('GITHUB')) hue = 220; // Navy Blue

                processedColors.push(`hsla(${hue}, ${sat}%, ${lightness}%, 1.0)`);

                processedMeta.push(meta);
                processedBorderWidths.push(0);
                processedBorderColors.push('rgba(0,0,0,0)');

                lastProvider = meta.provider;
                slicesInCurrentProvider++;
            });

            // Check for wrap-around gap (Last vs First)
            const firstProvider = data.meta[0].provider;
            if (lastProvider && lastProvider !== firstProvider) {
                processedLabels.push('Gap');
                processedValues.push(gapValue);
                processedColors.push('rgba(0,0,0,0)');
                processedMeta.push(null);
                processedBorderWidths.push(0);
                processedBorderColors.push('rgba(0,0,0,0)');
            }
        } else {
            processedLabels = ['No Data'];
            processedValues = [1];
            processedColors = ['#1e293b'];
            processedMeta = [null];
            processedBorderWidths = [0];
            processedBorderColors = ['#1a1a1a'];
        }

        const chartData = {
            labels: processedLabels,
            datasets: [{
                data: processedValues,
                backgroundColor: processedColors,
                borderWidth: processedBorderWidths,
                borderColor: processedBorderColors,
                hoverOffset: (ctx) => {
                    // Disable hover offset for gaps
                    const val = ctx.dataset.data[ctx.dataIndex];
                    const isGap = ctx.chart.data.labels[ctx.dataIndex] === 'Gap';
                    return isGap ? 0 : 15;
                }
            }]
        };
        chartData.meta = processedMeta;

        // Plugin to Draw Outer Provider Labels
        const providerLabels = {
            id: 'providerLabels',
            afterDraw: (chart) => {
                const { ctx, data } = chart;
                const meta = chart.getDatasetMeta(0);
                const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
                const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

                // Identify start/end angles for each provider group
                const providerSlices = {};

                meta.data.forEach((arc, index) => {
                    const m = data.meta[index];
                    if (!m) return; // // Skip gaps
                    // data.meta matches indices of chart data? Yes, chartData.meta = processedMeta.

                    if (!providerSlices[m.provider]) {
                        providerSlices[m.provider] = {
                            startAngle: arc.startAngle,
                            endAngle: arc.endAngle,
                            count: 1
                        };
                    } else {
                        // Update end angle to continuous max
                        // Handle wrap around? Chart.js usually provides continuous angles relative to start.
                        // We assume simple case: later slices have greater angles.
                        providerSlices[m.provider].endAngle = arc.endAngle;
                        providerSlices[m.provider].count++;
                    }
                });

                ctx.save();
                ctx.font = `900 ${this.getScaledSize(0.8)}px Lato, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#888888'; // black-400-ish

                Object.keys(providerSlices).forEach(provider => {
                    const group = providerSlices[provider];
                    // Skip label for very small groups?
                    if (Math.abs(group.endAngle - group.startAngle) < 0.1) return;

                    let angle = (group.startAngle + group.endAngle) / 2;
                    // Push out by 15px from outer radius
                    const labelRadius = meta.data[0].outerRadius + 15;

                    const x = centerX + Math.cos(angle) * labelRadius;
                    const y = centerY + Math.sin(angle) * labelRadius;

                    // Simple collision avoidance: if angle is within range?
                    // Just draw for now.
                    ctx.fillText(provider.toUpperCase(), x, y);
                });
                ctx.restore();
            }
        };

        // Custom plugin to draw labels on the segments
        const labelPlugin = {
            id: 'segmentLabels',
            // Use'afterDatasetsDraw' so that Tooltips (drawn later) appear ON TOP of these labels
            afterDatasetsDraw: (chart) => {
                const { ctx: chartCtx, data: chartData } = chart;
                const centerX = chart.getDatasetMeta(0).data[0]?.x || 0;
                const centerY = chart.getDatasetMeta(0).data[0]?.y || 0;

                // Get active element index to hide its static label (since tooltip will show details)
                const tooltip = chart.tooltip;
                const activeElements = tooltip && tooltip.getActiveElements();
                const activeIndex = activeElements && activeElements.length ? activeElements[0].index : -1;

                if (!hasData) {
                    chartCtx.save();
                    chartCtx.textAlign = 'center';
                    chartCtx.textBaseline = 'middle';
                    chartCtx.font = `${this.getScaledSize(1.0)}px Lato, sans-serif`;
                    chartCtx.fillStyle = '#888888';
                    chartCtx.fillText('No Data', centerX, centerY);
                    chartCtx.restore();
                    return;
                }

                chart.getDatasetMeta(0).data.forEach((datapoint, index) => {
                    // Don't draw label if this segment is being hovered (tooltip is shown)
                    if (index === activeIndex) return;

                    const meta = chartData.meta[index];
                    if (!meta || !meta.show_label) return;

                    // Hide labels for small segments to prevent overlap
                    if (meta.percentage < 5) return;

                    const { x, y } = datapoint.tooltipPosition();

                    chartCtx.save();
                    chartCtx.textAlign = 'center';
                    chartCtx.textBaseline = 'middle';
                    const fontSize = this.getScaledSize(0.8);
                    chartCtx.font = `900 ${fontSize}px Lato, sans-serif`;

                    // Prepare lines - Simplify to Model + % (Provider is in tooltip)
                    const modelName = meta.model.length > 20 ? meta.model.substring(0, 18) + '..' : meta.model;
                    const lines = [modelName, `${meta.percentage}%`];
                    const lineHeight = fontSize + 4;
                    const padding = 6;

                    // Calculate box dimensions
                    let maxWidth = 0;
                    lines.forEach(line => {
                        const width = chartCtx.measureText(line).width;
                        if (width > maxWidth) maxWidth = width;
                    });

                    const boxWidth = maxWidth + (padding * 2);
                    const boxHeight = (lines.length * lineHeight) + (padding * 2);
                    const boxX = x - (boxWidth / 2);
                    const boxY = y - (boxHeight / 2);

                    chartCtx.fillStyle = 'rgba(10, 10, 10, 0.7)'; // black-950
                    chartCtx.beginPath();
                    chartCtx.roundRect(boxX, boxY, boxWidth, boxHeight, 4);
                    chartCtx.fill();

                    // Draw text
                    chartCtx.fillStyle = '#ffffff';

                    const startY = boxY + padding + (lineHeight / 2);
                    lines.forEach((line, i) => {
                        chartCtx.fillText(line, x, startY + (i * lineHeight));
                    });

                    chartCtx.restore();
                });
            }
        };

        this.distributionChart = new Chart(ctx, {
            type: 'doughnut',
            data: chartData,
            plugins: [labelPlugin, providerLabels],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                radius: '75%', // Smaller and thinner to allow label space
                layout: {
                    padding: 10
                },
                elements: {
                    // Global element options removed, handled in dataset
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: hasData,
                        filter: function (tooltipItem) {
                            return tooltipItem.chart.data.labels[tooltipItem.dataIndex] !== 'Gap';
                        },
                        backgroundColor: '#262626',
                        titleColor: '#888888', // Provider (subtle)
                        titleFont: { size: this.getScaledSize(0.8), weight: 'normal' },
                        bodyColor: '#ffffff', // Model (bright)
                        bodyFont: { size: this.getScaledSize(0.85), weight: 'bold' },
                        borderColor: '#525252',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 6,
                        displayColors: false,
                        callbacks: {
                            title: function (context) {
                                if (!context || !context.length) return '';
                                const item = context[0];
                                const meta = item.chart.data.meta[item.dataIndex];
                                return meta ? meta.provider.toUpperCase() : '';
                            },
                            label: function (context) {
                                const meta = context.chart.data.meta[context.dataIndex];
                                if (!meta) return '';
                                // Use formatted value if available (for different metrics), else default to requests
                                const valStr = meta.formattedValue || (window.formatCompactNumber(meta.requests) + ' req');
                                return `${meta.model}: ${valStr} (${meta.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    updateCharts(trendData, distData) {
        // Re-initialize charts to properly apply all options
        if (trendData) {
            this.initTrendChart('trend-chart', trendData);
        }
        if (distData) {
            this.initDistributionChart('distribution-chart', distData);
        }
    }
}

window.chartManager = new ChartManager();
