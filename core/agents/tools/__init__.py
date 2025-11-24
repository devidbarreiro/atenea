"""
Herramientas para agentes LangChain
"""

from .duration_validator import validate_duration, validate_all_scenes_durations
from .word_counter import count_words, validate_text_length_for_duration
from .json_validator import validate_json_structure, parse_json_string
from .platform_selector import suggest_platform, validate_platform_avatar_consistency
from .auto_corrector import auto_correct_scene, auto_correct_all_scenes

# Creation tools (para CreationAgent)
from .create_image_tool import create_image_tool

__all__ = [
    # Validation tools
    'validate_duration',
    'validate_all_scenes_durations',
    'count_words',
    'validate_text_length_for_duration',
    'validate_json_structure',
    'parse_json_string',
    'suggest_platform',
    'validate_platform_avatar_consistency',
    'auto_correct_scene',
    'auto_correct_all_scenes',
    # Creation tools
    'create_image_tool',
]

