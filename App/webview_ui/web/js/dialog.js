/**
 * Custom Dialog Utility
 * Replaces system confirm() and alert() with styled UI dialogs
 */
class DialogManager {
    static async confirm(message, options = {}) {
        return new Promise((resolve) => {
            const title = options.title || 'Confirm';
            const confirmText = options.confirmText || 'OK';
            const cancelText = options.cancelText || 'Cancel';
            const dangerous = options.dangerous || false;

            const overlay = document.createElement('div');
            overlay.id = 'custom-dialog-overlay';
            overlay.className = 'fixed inset-0 bg-black/70 flex items-center justify-center z-50';

            overlay.innerHTML = `
                <div class="bg-black-800 rounded-xl p-6 border border-black-700 max-w-md w-full mx-4 shadow-2xl animate-fade-in">
                    <h3 class="text-lg font-semibold text-white mb-4">${this.escapeHtml(title)}</h3>
                    <p class="text-black-300 mb-6">${this.escapeHtml(message)}</p>
                    <div class="flex justify-end gap-3">
                        <button id="dialog-cancel-btn" class="px-4 py-2 text-sm font-medium text-black-400 hover:text-white bg-black-900 hover:bg-black-700 border border-black-700 rounded-lg transition-all">
                            ${this.escapeHtml(cancelText)}
                        </button>
                        <button id="dialog-confirm-btn" class="px-4 py-2 text-sm font-medium ${dangerous ? 'text-white bg-red-600 hover:bg-red-500' : 'text-black-950 bg-white hover:bg-black-200'} rounded-lg transition-all">
                            ${this.escapeHtml(confirmText)}
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);

            const confirmBtn = document.getElementById('dialog-confirm-btn');
            const cancelBtn = document.getElementById('dialog-cancel-btn');

            const cleanup = (result) => {
                overlay.remove();
                resolve(result);
            };

            confirmBtn.addEventListener('click', () => cleanup(true));
            cancelBtn.addEventListener('click', () => cleanup(false));

            // Allow Escape key to cancel
            const handleKeydown = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', handleKeydown);
                    cleanup(false);
                }
            };
            document.addEventListener('keydown', handleKeydown);

            // Focus confirm button
            confirmBtn.focus();
        });
    }

    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Make globally available
window.DialogManager = DialogManager;
