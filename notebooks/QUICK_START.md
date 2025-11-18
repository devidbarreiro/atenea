# 🚀 Quick Start - Notebooks

Guía rápida para empezar a trabajar con notebooks en 2 minutos.

## 1. Instalar Jupyter

```bash
pip install jupyter
```

## 2. Iniciar Jupyter

```bash
jupyter notebook
# o
jupyter lab
```

## 3. Crear tu primer notebook

### Opción A: Usar el template

1. Abre `notebooks/template_basico.ipynb`
2. Copia el contenido a un nuevo notebook en tu carpeta (`marcos/` o `ruth/`)
3. Ejecuta las celdas

### Opción B: Crear desde cero

1. Crea un nuevo notebook en tu carpeta
2. Primera celda:
   ```python
   %run ../setup_django.py
   ```
3. Segunda celda:
   ```python
   from langgraph.graph import StateGraph, END
   # ... tu código aquí
   ```

## 4. Estructura recomendada

```
notebooks/
├── marcos/                    # Tu carpeta personal
│   └── mi_experimento.ipynb  # Tus notebooks aquí
├── ruth/                      # Carpeta de Ruth
│   └── su_experimento.ipynb
└── challenges/                # Retos compartidos
    └── research_agent/        # Reto actual
```

## 💡 Tips

- **Siempre ejecuta setup primero**: `%run ../setup_django.py` (o `../../setup_django.py` desde challenges)
- **Guarda frecuentemente**: Los notebooks permiten experimentar sin miedo
- **Comparte resultados**: Los notebooks documentan todo el proceso
- **Usa el template**: `template_basico.ipynb` tiene todo lo necesario para empezar

## 🎯 Próximos pasos

1. ✅ Setup básico funcionando
2. 📚 Leer `challenges/research_agent/README.md` para el reto
3. 🔬 Experimentar con LangGraph
4. 🚀 Compartir resultados con el equipo

---

**¿Problemas?** Ver `README.md` para troubleshooting completo.

