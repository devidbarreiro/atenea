"""
Asistente RAG principal usando LangChain LCEL (LangChain Expression Language)
Compatible con LangChain 1.0+
"""

import logging
from typing import Dict, Optional, List
from django.conf import settings

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .document_loader import DocumentationLoader
from .vector_store import VectorStoreManager
from .prompts import SYSTEM_PROMPT, WELCOME_MESSAGE
from ..llm.factory import LLMFactory
from ..monitoring.langsmith_config import setup_langsmith

# Configurar LangSmith al importar
setup_langsmith()

logger = logging.getLogger(__name__)


class DocumentationAssistant:
    """Asistente RAG para consultar la documentación usando LCEL"""
    
    def __init__(
        self,
        llm_provider: str = None,
        llm_model: str = None,
        embedding_provider: str = None,
        embedding_model: str = None,
        top_k: int = None,
        reindex: bool = False
    ):
        """
        Inicializa el asistente de documentación
        
        Args:
            llm_provider: 'openai' o 'gemini'
            llm_model: Modelo específico del LLM
            embedding_provider: 'openai' o 'google'
            embedding_model: Modelo de embeddings
            top_k: Número de documentos a recuperar
            reindex: Si True, fuerza la re-indexación
        """
        # Configuración
        if llm_provider is None:
            llm_provider = getattr(settings, 'RAG_LLM_PROVIDER', None) or getattr(settings, 'DEFAULT_LLM_PROVIDER', 'openai')
        
        if llm_model is None:
            llm_model = getattr(settings, 'RAG_LLM_MODEL', None)
        
        if top_k is None:
            top_k = getattr(settings, 'RAG_TOP_K', 5)
        
        self.top_k = top_k
        
        # Crear LLM
        self.llm = LLMFactory.get_llm(
            provider=llm_provider,
            model_name=llm_model,
            temperature=0.7
        )
        
        # Cargar o crear índice
        self.vector_store_manager = VectorStoreManager(
            embedding_provider=embedding_provider,
            embedding_model=embedding_model
        )
        
        # Cargar documentos si es necesario
        vectorstore = self.vector_store_manager.load_index()
        
        if vectorstore is None or reindex:
            logger.info("Cargando documentos para crear/actualizar índice...")
            loader = DocumentationLoader()
            documents = loader.load_all_documents()
            chunks = loader.split_documents(documents)
            
            vectorstore = self.vector_store_manager.create_index(chunks, force=reindex)
        
        self.vectorstore = vectorstore
        
        # Crear retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.top_k}
        )
        
        # Configurar proyecto de LangSmith para RAG
        rag_project = getattr(settings, 'RAG_PROJECT_NAME', 'atenea-doc-assistant')
        import os
        langsmith_key = getattr(settings, 'LANGSMITH_API_KEY', None) or os.getenv('LANGSMITH_API_KEY')
        if langsmith_key:
            os.environ['LANGCHAIN_PROJECT'] = rag_project
        
        # Crear prompt template
        self.qa_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Pregunta: {question}")
        ])
        
        # Crear chain usando LCEL
        def format_context_and_question(inputs):
            """Formatea el contexto y la pregunta para el prompt"""
            if isinstance(inputs, dict):
                question = inputs.get("question", "")
            else:
                question = str(inputs)
            
            # Usar invoke en lugar de get_relevant_documents para LangChain 1.0+
            try:
                docs = self.retriever.invoke(question)
            except AttributeError:
                # Fallback para versiones anteriores
                docs = self.retriever.get_relevant_documents(question)
            
            context = self._format_docs(docs)
            return {
                "context": context,
                "question": question
            }
        
        self.chain = (
            RunnablePassthrough()
            | format_context_and_question
            | self.qa_prompt
            | self.llm
            | StrOutputParser()
        )
        
        logger.info(f"DocumentationAssistant inicializado (LLM: {llm_provider}, Top-K: {top_k})")
    
    def _format_docs(self, docs):
        """Formatea los documentos recuperados para el prompt"""
        return "\n\n".join([f"Documento: {doc.page_content}\nFuente: {doc.metadata.get('source', 'Desconocido')}" for doc in docs])
    
    def ask(self, question: str, chat_history: List = None) -> Dict:
        """
        Hace una pregunta al asistente
        
        Args:
            question: Pregunta del usuario
            chat_history: Historial de conversación (opcional, no usado en esta versión simple)
            
        Returns:
            Dict con 'answer' y 'sources'
        """
        try:
            # Obtener documentos primero para tener las fuentes
            try:
                docs = self.retriever.invoke(question)
            except AttributeError:
                docs = self.retriever.get_relevant_documents(question)
            
            sources = list(set([doc.metadata.get('source', 'Desconocido') for doc in docs]))
            
            # Ejecutar chain (pasa la pregunta como string)
            answer = self.chain.invoke(question)
            
            return {
                'answer': answer,
                'sources': sources,
                'question': question
            }
        
        except Exception as e:
            logger.error(f"Error al procesar pregunta: {e}", exc_info=True)
            return {
                'answer': f'Lo siento, ocurrió un error al procesar tu pregunta: {str(e)}',
                'sources': [],
                'question': question
            }
    
    def get_welcome_message(self) -> str:
        """Retorna el mensaje de bienvenida"""
        return WELCOME_MESSAGE
    
    def clear_history(self):
        """Limpia el historial de conversación (no aplica en esta versión simple)"""
        logger.info("clear_history llamado (no aplica en versión LCEL simple)")
