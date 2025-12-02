/**
 * Sistema de Toasts - Compatible con HTMX + Alpine.js + Tailwind
 * Similar a shadcn/ui pero sin React
 */

// Cola de toasts pendientes (para los que llegan antes de que Alpine inicialice)
window._pendingToasts = [];

// Listener global que se activa inmediatamente
window.addEventListener('show-toast', (e) => {
    console.log('[Toast] Evento recibido (global):', e.detail);
    if (window._toastManagerInstance) {
        // Si el manager ya está inicializado, mostrar directamente
        window._toastManagerInstance.showToast(e.detail);
    } else {
        // Si no, guardar en cola
        console.log('[Toast] Manager no inicializado, guardando en cola');
        window._pendingToasts.push(e.detail);
    }
});

function toastManager() {
    return {
        toasts: [],
        maxToasts: 5,
        
        init() {
            console.log('[Toast] Manager inicializado');
            
            // Guardar referencia global
            window._toastManagerInstance = this;
            
            // Escuchar cierre de toast
            window.addEventListener('toast-closed', (e) => {
                this.removeToast(e.detail);
            });
            
            // Procesar toasts pendientes
            if (window._pendingToasts && window._pendingToasts.length > 0) {
                console.log('[Toast] Procesando', window._pendingToasts.length, 'toasts pendientes');
                window._pendingToasts.forEach(data => this.showToast(data));
                window._pendingToasts = [];
            }
            
            // Convertir Django messages a toasts
            this.convertDjangoMessages();
        },
        
        showToast(data) {
            console.log('showToast called with:', data);
            const toast = {
                uuid: data.uuid || this.generateUUID(),
                type: data.type || 'info',
                title: data.title || '',
                message: data.message || '',
                action_url: data.action_url || null,
                action_label: data.action_label || null,
                auto_close: data.auto_close !== undefined ? data.auto_close : 5,
                progress: data.progress || null,
            };
            
            console.log('Toast object created:', toast);
            
            // Agregar al inicio del array (aparece arriba)
            this.toasts.unshift(toast);
            
            console.log('Total toasts:', this.toasts.length);
            
            // Limitar número de toasts visibles
            if (this.toasts.length > this.maxToasts) {
                this.toasts.pop();
            }
            
            // Auto-close si está configurado y no es de progreso
            if (toast.auto_close > 0 && toast.type !== 'progress') {
                setTimeout(() => {
                    this.removeToast(toast.uuid);
                }, toast.auto_close * 1000);
            }
            
                   // Reproducir sonido solo si está explícitamente habilitado
                   // El sonido se maneja desde notifications.js para generation_completed
                   // No reproducir aquí para evitar duplicados
        },
        
        removeToast(uuid) {
            this.toasts = this.toasts.filter(t => t.uuid !== uuid);
        },
        
        updateProgressToast(uuid, progress) {
            const toast = this.toasts.find(t => t.uuid === uuid);
            if (toast) {
                toast.progress = progress;
                // Forzar actualización de Alpine
                this.toasts = [...this.toasts];
            }
        },
        
        convertDjangoMessages() {
            // Convertir mensajes Django existentes a toasts
            // Buscar en el contenedor oculto de mensajes legacy
            const djangoMessages = document.querySelectorAll('.message');
            djangoMessages.forEach(msg => {
                const type = msg.classList.contains('bg-green-50') ? 'success' :
                            msg.classList.contains('bg-red-50') ? 'error' :
                            msg.classList.contains('bg-yellow-50') ? 'warning' : 'info';
                const message = msg.textContent.trim();
                
                if (message) {
                    // Determinar título según el tipo y contenido
                    let title = '';
                    if (type === 'success') {
                        if (message.includes('encolado') || message.includes('enviado')) {
                            title = 'Proceso encolado';
                        } else {
                            title = 'Éxito';
                        }
                    } else if (type === 'error') {
                        title = 'Error';
                    } else if (type === 'warning') {
                        title = 'Advertencia';
                    } else {
                        title = 'Información';
                    }
                    
                    this.showToast({
                        type: type,
                        title: title,
                        message: message,
                        auto_close: type === 'error' ? 10 : type === 'warning' ? 8 : 5,
                    });
                    
                    // Remover mensaje Django original después de un momento
                    setTimeout(() => {
                        msg.style.transition = 'opacity 0.3s ease';
                        msg.style.opacity = '0';
                        setTimeout(() => msg.remove(), 300);
                    }, 100);
                }
            });
        },
        
        playSound() {
            try {
                const audio = new Audio('/static/sounds/notification.mp3');
                audio.volume = (window.notificationManager?.settings?.sound_volume || 50) / 100;
                audio.play().catch(e => console.log('No se pudo reproducir sonido:', e));
            } catch (e) {
                console.log('Error al reproducir sonido:', e);
            }
        },
        
        generateUUID() {
            return 'toast-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
        }
    }
}

// Hacer disponible globalmente para actualizaciones de progreso
window.toastManager = toastManager;

