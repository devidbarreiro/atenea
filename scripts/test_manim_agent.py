"""
Script de prueba para el ManimVideoAgent
"""
import os
import django
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Setup Django
sys.path.append('c:/Proyectos/atenea')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
django.setup()

from core.agents import ManimVideoAgent
from django.contrib.auth.models import User

def test_manim_agent():
    print("--- Testing ManimVideoAgent ---")
    
    # Get a user (superuser usually ID 1)
    try:
        user = User.objects.first()
        if not user:
            print("Error: No users found in DB")
            return
        print(f"Using user: {user.username} (ID: {user.id})")
    except Exception as e:
        print(f"Error getting user: {e}")
        return

    agent = ManimVideoAgent(user_id=user.id)
    
    # Test Prompt
    prompt = "Crea un gráfico de barras moderno mostrando las visitas de la semana: Lunes 120, Martes 150, Miércoles 180, Jueves 200, Viernes 250"
    print(f"\nPrompt: {prompt}")
    
    print("\nRunning agent...")
    try:
        result = agent.process({'input': prompt})
        print("\nResult:")
        print(result)
        
        if result['status'] == 'success':
            print("\n✅ Agent executed successfully!")
        else:
            print(f"\n❌ Agent execution failed: {result.get('message')}")
            
    except Exception as e:
        print(f"\n❌ Exception during execution: {e}")

if __name__ == "__main__":
    test_manim_agent()
