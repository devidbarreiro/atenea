/**
 * Cliente WebSocket para notificaciones en tiempo real
 * Se integra con el sistema de toasts
 */

class NotificationManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 segundos
        this.settings = {
            sound_volume: 50,
            auto_close_time: {
                'generation_completed': 8,
                'generation_failed': 10,
                'generation_progress': 0, // No auto-close
                'info': 5,
            }
        };
    }
    
    // Obtener preferencia de sonido (desde localStorage o Alpine)
    isSoundEnabled() {
        // Primero verificar Alpine (si está inicializado)
        if (window.notificationPreferences?.soundEnabled) {
            return window.notificationPreferences.soundEnabled();
        }
        // Fallback a localStorage
        return localStorage.getItem('notificationSoundEnabled') !== 'false';
    }
    
    // Obtener preferencia de toasts
    areToastsEnabled() {
        // Primero verificar Alpine (si está inicializado)
        if (window.notificationPreferences?.toastsEnabled) {
            return window.notificationPreferences.toastsEnabled();
        }
        // Fallback a localStorage
        return localStorage.getItem('notificationToastsEnabled') !== 'false';
    }
    
    connect() {
        // Obtener protocolo (ws o wss)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket conectado para notificaciones');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onerror = (error) => {
                console.error('Error en WebSocket:', error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket desconectado');
                this.reconnect();
            };
            
        } catch (error) {
            console.error('Error conectando WebSocket:', error);
            this.reconnect();
        }
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reintentando conexión WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.warn('Máximo de reintentos alcanzado. Usando polling como fallback.');
            this.startPolling();
        }
    }
    
    handleMessage(data) {
        // Solo contador de pendientes (al reconectar) - no mostrar toasts
        if (data.type === 'pending_count') {
            window.dispatchEvent(new CustomEvent('update-notification-count', {
                detail: { count: data.count }
            }));
            return;
        }
        
        // Notificación en tiempo real - mostrar toast
        if (data.type === 'notification' || data.type === 'notification_message') {
            const notification = data.notification || data;
            
            // Determinar tipo de toast según tipo de notificación
            let toastType = 'info';
            if (notification.type === 'generation_completed') {
                toastType = 'success';
            } else if (notification.type === 'generation_failed') {
                toastType = 'error';
            } else if (notification.type === 'generation_progress') {
                toastType = 'progress';
            } else if (notification.type === 'generation_queued') {
                toastType = 'info';
            }
            
            // Reproducir sonido SOLO cuando se completa una generación y está habilitado
            if (notification.type === 'generation_completed' && this.isSoundEnabled()) {
                this.playNotificationSound();
            }
            
            // Disparar evento de toast (si están habilitados)
            if (this.areToastsEnabled()) {
                window.dispatchEvent(new CustomEvent('show-toast', {
                    detail: {
                        type: toastType,
                        title: notification.title,
                        message: notification.message,
                        action_url: notification.action_url,
                        action_label: notification.action_label,
                        auto_close: 5,
                        uuid: notification.uuid,
                    }
                }));
            }
            
            // Actualizar contador
            window.dispatchEvent(new CustomEvent('update-notification-count', {
                detail: { increment: true }
            }));
            
            // Refrescar paneles de notificaciones (tanto en dashboard como en creation)
            if (typeof htmx !== 'undefined') {
                document.body.dispatchEvent(new CustomEvent('refreshNotifications'));
            }
            
        } else if (data.type === 'progress_update') {
            const progress = data.progress;
            
            // Actualizar toast de progreso si existe
            if (window.toastManager && progress.item_uuid) {
                // Buscar toast por item_uuid en metadata
                const toastManagerInstance = document.querySelector('#toast-container')?._x_dataStack?.[0];
                if (toastManagerInstance) {
                    const toast = toastManagerInstance.toasts.find(t => 
                        t.metadata?.item_uuid === progress.item_uuid
                    );
                    if (toast) {
                        toastManagerInstance.updateProgressToast(toast.uuid, progress.progress);
                    }
                }
            }
        }
    }
    
    markAsRead(notificationUuid) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'mark_read',
                notification_uuid: notificationUuid
            }));
        }
    }
    
    markAllAsRead() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'mark_all_read'
            }));
        }
    }
    
    startPolling() {
        // Fallback: polling cada 30 segundos si WebSocket falla
        // Solo actualiza el contador, no muestra toasts (los toasts solo via WebSocket en tiempo real)
        const poll = () => {
            fetch('/notifications/count/')
                .then(response => response.json())
                .then(data => {
                    if (data.count !== undefined) {
                        window.dispatchEvent(new CustomEvent('update-notification-count', {
                            detail: { count: data.count }
                        }));
                    }
                })
                .catch(error => console.error('Error en polling:', error));
        };
        
        // Ejecutar cada 30 segundos
        setInterval(poll, 30000);
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    playNotificationSound() {
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = (this.settings.sound_volume || 50) / 100;
            audio.play().catch(e => {
                console.log('No se pudo reproducir sonido de notificación:', e);
            });
        } catch (e) {
            console.log('Error al reproducir sonido de notificación:', e);
        }
    }
}

// Función global para reproducir sonido (usada por el botón de test)
window.playNotificationSound = function() {
    try {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => {
            console.log('No se pudo reproducir sonido de notificación:', e);
        });
    } catch (e) {
        console.log('Error al reproducir sonido de notificación:', e);
    }
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Solo conectar si el usuario está autenticado
    if (document.body.dataset.userAuthenticated === 'true' || 
        document.querySelector('[data-user-id]')) {
        window.notificationManager = new NotificationManager();
        window.notificationManager.connect();
    }
});

