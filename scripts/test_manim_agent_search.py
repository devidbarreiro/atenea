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

from core.agents.manim_agent import ManimVideoAgent

def test_search_and_generate():
    # User ID 1 for testing
    agent = ManimVideoAgent(user_id=1)
    
    # Prompt vago que requiere búsqueda
    prompt = "tasa de natalidad en España en los últimos 5 años"
    
    print(f"\n--- Testing ManimVideoAgent with Search ---")
    print(f"Prompt: {prompt}")
    
    print("\nRunning agent...")
    try:
        # Usar process() 
        result = agent.process({'input': prompt})
        
        print("\nResult:")
        print(result)
        
        if result.get('status') == 'success':
            print("\n✅ Agent executed successfully!")
        else:
            print(f"\n❌ Agent failed: {result.get('message')}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_and_generate()
