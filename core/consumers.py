"""
WebSocket consumers para notificaciones en tiempo real
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer para notificaciones en tiempo real"""
    
    async def connect(self):
        """Conectar usuario al grupo de notificaciones"""
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Grupo por usuario: notifications_user_{user_id}
        self.group_name = f'notifications_user_{self.user.id}'
        
        # Unirse al grupo (solo si channel_layer está configurado)
        if self.channel_layer:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Enviar notificaciones pendientes al reconectar
        await self.send_pending_notifications()
        
        logger.info(f"Usuario {self.user.id} conectado a notificaciones")
    
    async def disconnect(self, close_code):
        """Desconectar usuario del grupo"""
        if hasattr(self, 'group_name') and self.channel_layer:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        if hasattr(self, 'user') and self.user.is_authenticated:
            logger.info(f"Usuario {self.user.id} desconectado de notificaciones")
    
    async def receive(self, text_data):
        """Recibir mensajes del cliente"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                # Marcar notificación como leída
                notification_uuid = data.get('notification_uuid')
                if notification_uuid:
                    await self.mark_notification_read(notification_uuid)
            
            elif message_type == 'mark_all_read':
                # Marcar todas como leídas
                await self.mark_all_notifications_read()
            
        except json.JSONDecodeError:
            logger.error("Error decodificando mensaje WebSocket")
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    async def notification_message(self, event):
        """Enviar notificación al cliente"""
        notification_data = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))
    
    async def progress_update(self, event):
        """Enviar actualización de progreso al cliente"""
        progress_data = event['progress']
        
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'progress': progress_data
        }))
    
    async def send_pending_notifications(self):
        """Enviar solo el contador de notificaciones pendientes al reconectar (sin crear toasts)"""
        count = await self.get_unread_count()
        
        # Solo enviar el contador, no las notificaciones completas
        # Las notificaciones completas solo se envían en tiempo real cuando llegan nuevas
        await self.send(text_data=json.dumps({
            'type': 'pending_count',
            'count': count
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Obtener notificaciones no leídas del usuario"""
        notifications = Notification.objects.filter(
            user=self.user,
            read=False
        ).order_by('-created_at')[:10]  # Últimas 10 no leídas
        
        return [
            {
                'uuid': str(n.uuid),
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'action_url': n.action_url,
                'action_label': n.action_label,
                'created_at': n.created_at.isoformat(),
                'metadata': n.metadata,
            }
            for n in notifications
        ]
    
    @database_sync_to_async
    def get_unread_count(self):
        """Obtener conteo de notificaciones no leídas"""
        return Notification.objects.filter(user=self.user, read=False).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_uuid):
        """Marcar notificación como leída"""
        try:
            notification = Notification.objects.get(
                uuid=notification_uuid,
                user=self.user
            )
            notification.mark_as_read()
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notification_uuid} no encontrada")
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Marcar todas las notificaciones como leídas"""
        from django.utils import timezone
        Notification.objects.filter(
            user=self.user,
            read=False
        ).update(read=True, read_at=timezone.now())
    
    @classmethod
    def send_notification_to_user_sync(cls, user_id, notification):
        """
        Enviar notificación a un usuario específico vía WebSocket (versión síncrona)
        
        Args:
            user_id: ID del usuario
            notification: Objeto Notification
        """
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        # Verificar que channel_layer está configurado (puede ser None en desarrollo)
        if not channel_layer:
            logger.debug(f"Channel layer no configurado, notificación {notification.uuid} no enviada via WebSocket")
            return
        
        group_name = f'notifications_user_{user_id}'
        
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'notification_message',
                    'notification': {
                        'uuid': str(notification.uuid),
                        'type': notification.type,
                        'title': notification.title,
                        'message': notification.message,
                        'action_url': notification.action_url,
                        'action_label': notification.action_label,
                        'created_at': notification.created_at.isoformat(),
                        'metadata': notification.metadata,
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Error enviando notificación via WebSocket: {e}")

