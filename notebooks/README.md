# Notebooks de Desarrollo

Este directorio contiene notebooks de Jupyter para experimentación y desarrollo.

## ⚡ Quick Start (2 minutos)

¿Tienes prisa? Ve a **[QUICK_START.md](QUICK_START.md)** para empezar en 2 minutos.

## 🚀 Inicio Rápido Completo

### 1. Instalar Jupyter (si no está instalado)

```bash
pip install jupyter jupyterlab
```

O si prefieres solo Jupyter Notebook:

```bash
pip install jupyter
```

### 2. Iniciar Jupyter

```bash
# Jupyter Notebook (clásico)
jupyter notebook

# O JupyterLab (más moderno)
jupyter lab
```

### 3. Configurar Django en un Notebook

En cualquier notebook, ejecuta al inicio:

```python
# Opción 1: Usar el script de setup
%run setup_django.py

# Opción 2: Importar directamente
from notebooks.setup_django import setup_django
setup_django()
```

### 4. Usar Django en el Notebook

Una vez configurado, puedes importar modelos y servicios:

```python
from core.models import Script, Scene, Project
from core.agents.script_agent import ScriptAgent
from core.llm.factory import LLMFactory
from core.services_agent import ScriptAgentService

# Crear un LLM
llm = LLMFactory.get_llm(provider='openai', temperature=0.7)

# Usar el agente
agent = ScriptAgent(llm_provider='openai')
result = agent.process_script(
    script_text="Tu guión aquí",
    duration_min=2
)
```

## 📁 Estructura

```
notebooks/
├── setup_django.py          # Script de configuración de Django
├── marcos/                  # Notebooks personales de Marcos
│   └── README.md
├── ruth/                    # Notebooks personales de Ruth
│   └── README.md
├── challenges/              # Retos y desafíos del equipo
│   ├── research_agent/      # Reto Research & Draft Agent
│   │   ├── 01_setup.ipynb  # Setup inicial
│   │   └── README.md
│   └── README.md
└── README.md                # Este archivo
```

## 👥 Carpetas Personales

Cada desarrollador tiene su propia carpeta para experimentos y pruebas:
- `marcos/` - Notebooks de Marcos
- `ruth/` - Notebooks de Ruth

Crea tus notebooks en tu carpeta personal para experimentar libremente.

## 🎯 Retos y Desafíos

Los retos compartidos están en `challenges/`:

### Research & Draft Agent

Ver `challenges/research_agent/README.md` para el reto completo de LangGraph.

## 💡 Consejos

1. **Siempre ejecuta el setup primero**: Django necesita configurarse antes de usar modelos
2. **Usa variables de entorno**: Las API keys deben estar en `.env`
3. **Guarda tus experimentos**: Los notebooks son perfectos para iterar rápidamente
4. **Comparte resultados**: Los notebooks permiten documentar el proceso completo

## 🔧 Troubleshooting

### Error: "Django settings not configured"

Asegúrate de ejecutar `setup_django.py` al inicio del notebook.

### Error: "No module named 'core'"

Verifica que estás ejecutando el notebook desde el directorio raíz del proyecto, o que el path está configurado correctamente.

### Error: "API key not found"

Asegúrate de tener un archivo `.env` en la raíz del proyecto con las API keys necesarias.

## 📚 Recursos

- [Jupyter Notebook Docs](https://jupyter-notebook.readthedocs.io/)
- [JupyterLab Docs](https://jupyterlab.readthedocs.io/)
- [Django + Jupyter Guide](https://docs.djangoproject.com/en/stable/howto/jupyter/)

