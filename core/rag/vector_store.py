"""
Gestión del vector store usando FAISS con LangChain
"""

import os
import logging
from pathlib import Path
from typing import Optional
from django.conf import settings

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Gestiona el vector store FAISS para la documentación"""
    
    def __init__(self, embedding_provider: str = None, embedding_model: str = None):
        """
        Inicializa el gestor del vector store
        
        Args:
            embedding_provider: 'openai' o 'google'
            embedding_model: Modelo de embeddings a usar
        """
        if embedding_provider is None:
            embedding_provider = getattr(settings, 'RAG_EMBEDDING_PROVIDER', 'openai')
        
        if embedding_model is None:
            embedding_model = getattr(settings, 'RAG_EMBEDDING_MODEL', 'text-embedding-3-small')
        
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.embeddings = self._create_embeddings()
        
        # Path para guardar el índice
        store_path = getattr(settings, 'RAG_VECTOR_STORE_PATH', '.rag_store')
        self.base_dir = Path(settings.BASE_DIR)
        self.store_path = self.base_dir / store_path
        self.index_path = self.store_path / 'faiss_index'
    
    def _create_embeddings(self):
        """Crea el objeto de embeddings según el proveedor"""
        if self.embedding_provider == 'openai':
            api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError('OPENAI_API_KEY no está configurada')
            
            return OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=api_key
            )
        
        elif self.embedding_provider == 'google':
            api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError('GEMINI_API_KEY no está configurada')
            
            return GoogleGenerativeAIEmbeddings(
                model=self.embedding_model,
                google_api_key=api_key
            )
        
        else:
            raise ValueError(f"Proveedor de embeddings no soportado: {self.embedding_provider}")
    
    def create_index(self, documents: list, force: bool = False) -> FAISS:
        """
        Crea un nuevo índice FAISS desde documentos
        
        Args:
            documents: Lista de documentos de LangChain
            force: Si True, recrea el índice aunque exista
            
        Returns:
            Instancia de FAISS
        """
        if self.index_path.exists() and not force:
            logger.info(f"El índice ya existe en {self.index_path}. Usa force=True para recrearlo.")
            return self.load_index()
        
        logger.info(f"Creando índice FAISS con {len(documents)} documentos...")
        
        # Crear índice
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        
        # Guardar
        self.store_path.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(self.index_path))
        
        logger.info(f"Índice guardado en {self.index_path}")
        return vectorstore
    
    def load_index(self) -> Optional[FAISS]:
        """
        Carga el índice existente
        
        Returns:
            Instancia de FAISS o None si no existe
        """
        if not self.index_path.exists():
            logger.warning(f"El índice no existe en {self.index_path}")
            return None
        
        try:
            logger.info(f"Cargando índice desde {self.index_path}")
            vectorstore = FAISS.load_local(
                str(self.index_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("Índice cargado exitosamente")
            return vectorstore
        except Exception as e:
            logger.error(f"Error al cargar el índice: {e}")
            return None
    
    def get_or_create_index(self, documents: list = None) -> FAISS:
        """
        Obtiene el índice existente o lo crea si no existe
        
        Args:
            documents: Documentos para crear el índice si no existe
            
        Returns:
            Instancia de FAISS
        """
        vectorstore = self.load_index()
        
        if vectorstore is None:
            if documents is None:
                raise ValueError("No hay índice existente y no se proporcionaron documentos para crearlo")
            vectorstore = self.create_index(documents)
        
        return vectorstore

