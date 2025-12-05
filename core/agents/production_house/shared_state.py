"""
Estado Compartido para Multi-Agente Production House
Todos los agentes trabajan sobre este estado compartido
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class SharedState:
    """
    Estado compartido entre todos los agentes de la productora.
    Se guarda en Script.processed_data durante el procesamiento.
    """
    
    # Metadata del script
    script_id: int
    script_text: str
    duration_min: float
    duration_seconds: int
    video_format: str  # 'social', 'educational', 'longform'
    video_type: str  # 'ultra', 'avatar', 'general'
    video_orientation: str = '16:9'  # '16:9' o '9:16'
    
    # Escenas generadas
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Continuidad cinematográfica
    continuity: Dict[str, Any] = field(default_factory=dict)
    
    # Validación y calidad
    validation: Dict[str, Any] = field(default_factory=dict)
    
    # Métricas y costos
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Historial de acciones (para debugging)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Logs de agentes
    agent_logs: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_history(self, agent_name: str, action: str, details: Dict[str, Any] = None):
        """Añade una entrada al historial"""
        self.history.append({
            'agent': agent_name,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        })
    
    def add_log(self, agent_name: str, message: str):
        """Añade un log de un agente"""
        if agent_name not in self.agent_logs:
            self.agent_logs[agent_name] = []
        self.agent_logs[agent_name].append(f"[{datetime.now().isoformat()}] {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el estado a diccionario para guardar en BD"""
        return {
            'script_id': self.script_id,
            'script_text': self.script_text,
            'metadata': {
                'duration_min': self.duration_min,
                'duration_seconds': self.duration_seconds,
                'video_format': self.video_format,
                'video_type': self.video_type,
                'video_orientation': self.video_orientation
            },
            'scenes': self.scenes,
            'continuity': self.continuity,
            'validation': self.validation,
            'metrics': self.metrics,
            'history': self.history,
            'agent_logs': self.agent_logs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedState':
        """Crea un estado desde un diccionario (desde BD)"""
        metadata = data.get('metadata', {})
        return cls(
            script_id=data.get('script_id'),
            script_text=data.get('script_text', ''),
            duration_min=metadata.get('duration_min', 0),
            duration_seconds=metadata.get('duration_seconds', 0),
            video_format=metadata.get('video_format', 'educational'),
            video_type=metadata.get('video_type', 'general'),
            video_orientation=metadata.get('video_orientation', '16:9'),
            scenes=data.get('scenes', []),
            continuity=data.get('continuity', {}),
            validation=data.get('validation', {}),
            metrics=data.get('metrics', {}),
            history=data.get('history', []),
            agent_logs=data.get('agent_logs', {})
        )
    
    def get_scene_by_id(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una escena por su ID"""
        for scene in self.scenes:
            if scene.get('id') == scene_id:
                return scene
        return None
    
    def update_scene(self, scene_id: str, updates: Dict[str, Any]):
        """Actualiza una escena específica"""
        for i, scene in enumerate(self.scenes):
            if scene.get('id') == scene_id:
                self.scenes[i].update(updates)
                return
        raise ValueError(f"Escena {scene_id} no encontrada")

