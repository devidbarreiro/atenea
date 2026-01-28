"""
Comando de management para re-indexar la documentación RAG
"""

from django.core.management.base import BaseCommand
from core.rag.assistant import DocumentationAssistant
from core.rag.vector_store import VectorStoreManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-indexa la documentación para el asistente RAG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la re-indexación incluso si el índice existe',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('🔄 Re-indexando documentación RAG...'))
        
        try:
            # Eliminar índice anterior si existe
            vector_store_manager = VectorStoreManager()
            deleted = vector_store_manager.delete_index()
            
            if deleted:
                self.stdout.write(self.style.SUCCESS('✓ Índice anterior eliminado'))
            else:
                self.stdout.write(self.style.WARNING('⚠ No había índice anterior'))
            
            # Crear nuevo índice
            self.stdout.write('📚 Cargando documentos desde docs/public/api...')
            assistant = DocumentationAssistant(reindex=True)
            
            self.stdout.write(self.style.SUCCESS('✅ Documentación re-indexada exitosamente'))
            self.stdout.write(f'   Ubicación: {vector_store_manager.index_path}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al re-indexar: {str(e)}'))
            logger.error(f"Error al re-indexar: {e}", exc_info=True)
            raise

