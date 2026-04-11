class CustomSelectManager {
    constructor() {
        this.initialized = new Set();
        this.globalHandlersBound = false;
    }

    handleGlobalScroll(event) {
        if (event.target && event.target.closest && event.target.closest('.custom-select-menu')) {
            return;
        }
        this.closeAll();
    }

    initAll() {
        document.querySelectorAll('select[data-custom-select]').forEach((select) => {
            this.initSelect(select);
        });
    }

    initSelectIds(ids) {
        ids.forEach((id) => this.initSelect(id));
    }

    initSelect(selectOrId) {
        const select = typeof selectOrId === 'string'
            ? document.getElementById(selectOrId)
            : selectOrId;
        if (!select || !select.id) return;

        select.classList.add('custom-select-native');
        select.setAttribute('data-custom-select', 'true');

        let root = document.getElementById(`${select.id}-custom`)
            || select.parentElement.querySelector(`.custom-select-root[data-select-id="${select.id}"]`);

        if (!root) {
            root = document.createElement('div');
            select.insertAdjacentElement('afterend', root);
        }

        root.id = `${select.id}-custom`;
        root.dataset.selectId = select.id;
        root.className = `custom-select-root relative${select.classList.contains('w-full') ? ' w-full' : ''}`;

        let trigger = root.querySelector('.custom-select-trigger');
        if (!trigger) {
            trigger = document.createElement('div');
            trigger.tabIndex = 0;
            trigger.setAttribute('role', 'button');
            trigger.setAttribute('aria-haspopup', 'listbox');
            trigger.setAttribute('aria-expanded', 'false');
            root.appendChild(trigger);
        }
        trigger.className = `custom-select-trigger w-full flex items-center justify-between gap-3 transition-colors ${this.getPresentationClass(select)}`;

        let menu = root.querySelector('.custom-select-menu');
        if (menu) {
            menu.remove();
        }

        menu = document.querySelector(`.custom-select-menu[data-select-id="${select.id}"]`);
        if (!menu) {
            menu = document.createElement('div');
            menu.className = 'custom-select-menu hidden z-50 bg-black-900 border border-black-700 rounded-lg shadow-2xl overflow-hidden';
            menu.setAttribute('role', 'listbox');
            menu.dataset.selectId = select.id;
            document.body.appendChild(menu);
        }

        this.renderSelect(select, trigger, menu, !this.initialized.has(select.id));

        if (!this.initialized.has(select.id)) {
            const toggleMenu = (event) => {
                event.preventDefault();
                const isOpen = !menu.classList.contains('hidden');
                this.closeAll();
                if (!isOpen) {
                    this.positionMenu(trigger, root, menu);
                    root.dataset.open = 'true';
                    trigger.classList.add('border-white');
                    trigger.setAttribute('aria-expanded', 'true');
                    menu.classList.remove('hidden');
                }
            };

            trigger.addEventListener('click', toggleMenu);
            trigger.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    toggleMenu(event);
                }
            });

            select.addEventListener('change', () => {
                this.sync(select.id);
            });

            this.initialized.add(select.id);
        }

        if (!this.globalHandlersBound) {
            document.addEventListener('click', (event) => {
                if (!event.target.closest('.custom-select-root') && !event.target.closest('.custom-select-menu')) {
                    this.closeAll();
                }
            });
            window.addEventListener('resize', () => this.closeAll());
            window.addEventListener('scroll', (event) => this.handleGlobalScroll(event), true);
            this.globalHandlersBound = true;
        }
    }

    renderSelect(select, trigger, menu, initialRender = false) {
        this.renderTrigger(select, trigger);

        if (initialRender || !menu.dataset.initialized) {
            this.buildMenu(select, menu);
            menu.dataset.initialized = 'true';
        }

        this.updateSelectedState(select, menu);

        if (initialRender && !menu.dataset.widthLocked) {
            this.applyWidth(select, trigger);
            menu.dataset.widthLocked = 'true';
        }
    }

    renderTrigger(select, trigger) {
        const chevron = '<svg class="custom-select-chevron w-4 h-4 text-black-400 shrink-0 transition-transform" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 6.5L8 11l4.5-4.5"></path></svg>';
        const selectedOption = select.options[select.selectedIndex];
        const selectedDisplay = this.getOptionDisplay(select, selectedOption);
        trigger.innerHTML = `
            <div class="min-w-0 flex items-center justify-between gap-3 flex-1">
                <span class="truncate">${this.escapeHtml(selectedDisplay.label)}</span>
                ${selectedDisplay.meta ? `<span class="custom-select-meta shrink-0 text-[11px] tracking-[0.12em] text-black-400">${this.escapeHtml(selectedDisplay.meta)}</span>` : ''}
            </div>
            ${chevron}
        `;
    }

    buildMenu(select, menu) {
        let menuHtml = '<div class="custom-select-options max-h-64 overflow-y-auto py-1">';
        Array.from(select.children).forEach((child) => {
            if (child.tagName === 'OPTGROUP') {
                menuHtml += `<div class="px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-black-500">${this.escapeHtml(child.label)}</div>`;
                Array.from(child.children).forEach((option) => {
                    menuHtml += this.renderOption(select, option, select.value);
                });
            } else if (child.tagName === 'OPTION') {
                menuHtml += this.renderOption(select, child, select.value);
            }
        });
        menuHtml += '</div>';
        menu.innerHTML = menuHtml;

        const scrollContainer = menu.querySelector('.custom-select-options');
        if (scrollContainer && !scrollContainer.dataset.wheelBound) {
            scrollContainer.dataset.wheelBound = 'true';
            scrollContainer.addEventListener('wheel', (event) => {
                event.stopPropagation();
            }, { passive: true });
        }

        menu.querySelectorAll('[data-option-value]').forEach((optionEl) => {
            const choose = () => {
                select.value = optionEl.dataset.optionValue;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                this.closeAll();
            };
            optionEl.addEventListener('click', choose);
            optionEl.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    choose();
                }
            });
        });
    }

    updateSelectedState(select, menu) {
        menu.querySelectorAll('[data-option-value]').forEach((optionEl) => {
            const isSelected = optionEl.dataset.optionValue === select.value;
            optionEl.classList.toggle('text-white', isSelected);
            optionEl.classList.toggle('bg-black-800', isSelected);
            optionEl.classList.toggle('text-black-300', !isSelected);
        });
    }

    renderOption(select, option, currentValue) {
        const display = this.getOptionDisplay(select, option);
        const selectedClass = option.value === currentValue ? 'text-white bg-black-800' : 'text-black-300';
        const indentClass = option.parentElement && option.parentElement.tagName === 'OPTGROUP'
            ? 'custom-select-option-indented'
            : '';
        return `
            <div role="option" tabindex="0" class="custom-select-option w-full text-left px-3 py-2 text-sm transition-colors ${selectedClass} ${indentClass}" data-option-value="${this.escapeHtml(option.value)}">
                <div class="flex items-center justify-between gap-3">
                    <span class="truncate">${this.escapeHtml(display.label)}</span>
                    ${display.meta ? `<span class="custom-select-meta shrink-0 text-[11px] tracking-[0.12em] text-black-500">${this.escapeHtml(display.meta)}</span>` : ''}
                </div>
            </div>
        `;
    }

    getOptionDisplay(select, option) {
        if (!option) {
            return { label: '', meta: '' };
        }

        const label = (option.dataset.label || option.textContent || '').trim();
        let meta = (option.dataset.meta || '').trim();

        if (!meta && select && select.id === 'timezone-select') {
            meta = this.getTimezoneOffsetLabel(option.value);
        }

        return { label, meta };
    }

    getTimezoneOffsetLabel(timezone) {
        if (!timezone) return '';
        if (timezone === 'local') return 'AUTO';
        if (timezone.toUpperCase() === 'UTC') return 'GMT+0';

        try {
            const formatter = new Intl.DateTimeFormat('en-US', {
                timeZone: timezone,
                timeZoneName: 'shortOffset',
            });
            const part = formatter.formatToParts(new Date()).find((item) => item.type === 'timeZoneName');
            if (!part || !part.value) return '';
            return part.value.replace('GMT', 'GMT');
        } catch (_error) {
            return '';
        }
    }

    applyWidth(select, trigger) {
        const root = trigger.closest('.custom-select-root');
        if (!root) return;

        if (select.classList.contains('w-full')) {
            root.style.width = '100%';
            return;
        }

        const labels = Array.from(select.options).map((option) => {
            const display = this.getOptionDisplay(select, option);
            return display.meta ? `${display.label} ${display.meta}` : display.label;
        });
        const longest = labels.reduce((max, label) => label.length > max.length ? label : max, '');

        const probe = document.createElement('span');
        const styles = getComputedStyle(trigger);
        probe.style.position = 'absolute';
        probe.style.visibility = 'hidden';
        probe.style.whiteSpace = 'pre';
        probe.style.font = styles.font;
        probe.style.letterSpacing = styles.letterSpacing;
        probe.textContent = longest;
        document.body.appendChild(probe);
        const textWidth = probe.getBoundingClientRect().width;
        probe.remove();

        root.style.width = `${Math.ceil(textWidth + 84)}px`;
    }

    positionMenu(trigger, root, menu) {
        const triggerRect = trigger.getBoundingClientRect();
        const rootRect = root.getBoundingClientRect();
        const menuWidth = Math.max(triggerRect.width, rootRect.width);

        const wasHidden = menu.classList.contains('hidden');
        if (wasHidden) {
            menu.classList.remove('hidden');
            menu.style.visibility = 'hidden';
        }

        menu.style.width = `${Math.ceil(menuWidth)}px`;
        menu.style.left = `${Math.round(triggerRect.left)}px`;

        const menuHeight = menu.getBoundingClientRect().height;
        const viewportHeight = window.innerHeight;
        const gap = 8;
        const openUpward = triggerRect.bottom + gap + menuHeight > viewportHeight && triggerRect.top - gap - menuHeight > 24;
        const top = openUpward
            ? Math.max(12, triggerRect.top - menuHeight - gap)
            : Math.min(viewportHeight - menuHeight - 12, triggerRect.bottom + gap);

        menu.style.top = `${Math.round(top)}px`;

        if (wasHidden) {
            menu.classList.add('hidden');
            menu.style.visibility = '';
        }
    }

    getPresentationClass(select) {
        return select.className
            .replace(/custom-select-native/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    sync(selectId) {
        const select = document.getElementById(selectId);
        if (!select) return;

        const root = document.getElementById(`${select.id}-custom`);
        if (!root) return;

        const trigger = root.querySelector('.custom-select-trigger');
        const menu = document.querySelector(`.custom-select-menu[data-select-id="${select.id}"]`);
        if (!trigger || !menu) return;

        this.renderSelect(select, trigger, menu);
    }

    syncIds(ids) {
        ids.forEach((id) => this.sync(id));
    }

    closeAll() {
        document.querySelectorAll('.custom-select-root').forEach((root) => {
            root.dataset.open = 'false';
            const trigger = root.querySelector('.custom-select-trigger');
            if (trigger) {
                trigger.classList.remove('border-white');
                trigger.setAttribute('aria-expanded', 'false');
            }
        });

        document.querySelectorAll('.custom-select-menu[data-select-id]').forEach((menu) => {
            menu.classList.add('hidden');
            menu.style.visibility = '';
        });
    }

    escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

window.customSelectManager = new CustomSelectManager();
