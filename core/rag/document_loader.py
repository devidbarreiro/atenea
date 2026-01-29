"""
Carga documentos Markdown desde /docs usando LangChain
"""

import os
import logging
from pathlib import Path
from typing import List
from django.conf import settings

from langchain_community.document_loaders import TextLoader
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentationLoader:
    """Carga y procesa documentos Markdown de la documentación"""
    
    def __init__(self, docs_path: str = None, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Inicializa el loader de documentación
        
        Args:
            docs_path: Ruta a la carpeta docs (relativa a BASE_DIR)
            chunk_size: Tamaño de los chunks en caracteres
            chunk_overlap: Overlap entre chunks
        """
        if docs_path is None:
            docs_path = getattr(settings, 'RAG_DOCS_PATH', 'docs/public/api')
        
        # Limpiar el path de comentarios o espacios extra
        if isinstance(docs_path, str):
            docs_path = docs_path.split('#')[0].strip()
        
        self.base_dir = Path(settings.BASE_DIR)
        self.docs_path = self.base_dir / docs_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_all_documents(self) -> List:
        """
        Carga todos los archivos .md de la carpeta docs
        
        Returns:
            Lista de documentos de LangChain
        """
        documents = []
        
        if not self.docs_path.exists():
            logger.error(f"La carpeta de documentación no existe: {self.docs_path}")
            return documents
        
        # Recorrer recursivamente todos los .md
        md_files = list(self.docs_path.rglob("*.md"))
        
        logger.info(f"Encontrados {len(md_files)} archivos Markdown en {self.docs_path}")
        
        for md_file in md_files:
            try:
                # Cargar archivo como texto
                loader = TextLoader(str(md_file), encoding='utf-8')
                file_docs = loader.load()
                
                # Agregar metadata
                for doc in file_docs:
                    # Ruta relativa desde docs/
                    rel_path = md_file.relative_to(self.docs_path)
                    doc.metadata.update({
                        'source': str(rel_path),
                        'file_path': str(md_file),
                        'file_name': md_file.name,
                    })
                
                documents.extend(file_docs)
                
            except Exception as e:
                logger.warning(f"Error al cargar {md_file}: {e}")
                continue
        
        logger.info(f"Cargados {len(documents)} documentos")
        return documents
    
    def split_documents(self, documents: List) -> List:
        """
        Divide documentos en chunks
        
        Args:
            documents: Lista de documentos de LangChain
            
        Returns:
            Lista de chunks
        """
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Documentos divididos en {len(chunks)} chunks")
        return chunks

