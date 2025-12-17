# Errores Reportados y Priorización - Semana 15/12

## Contexto

**Objetivo de la semana**: Estabilizar y hacer robusto lo que existe. No nuevas funcionalidades ni modelos de datos. Enfoque en que funcione lo actual y no falle.

**Testing**: Ruth realizará pruebas intensivas mientras se corrigen los errores.

**Filosofía**: Preferir llegar con lo corregido que funcione y esté probado, antes que todo o nada.

---

## Errores Reportados por Miguel

### GENERAL
- Sería interesante poder ver las creaciones recientes o los proyectos y las bibliotecas también en formato lista.

### MANIM QUOTE
- ✅ Funciona bien, pero necesita mejoras:
  - Modificar animación de entrada (escalado desde esquina inferior izquierda)
  - Poder decidir tiempo en pantalla o párrafo concreto
  - Salida al corte, sin animación
  - Mejorar composición de diseño y tipografías

### CREACIÓN DE IMÁGENES
- Al no seleccionar modelo y crear con prompt, se queda pensando continuamente
- No permite poner la resolución deseada o re-escalar en calidad
- Seedream no funciona (da error)
- Error "Proyecto no encontrado" al volver después de descargar imagen
- Flux Context no funciona (no genera imagen)
- Soul standard tampoco funciona
- Problemas al generar varias imágenes seguidas (segunda no se ve)

### STOCK VIDEOS
- No se pueden previsualizar vídeos de Freepik (play no funciona)
- Botón "ver" en Freepik abre ventana de Atenea en lugar de ir a la plataforma
- En Pexels el botón "ver" sí funciona, pero previsualización tampoco se ve
- Faltan datos técnicos: resoluciones, fps, codec

### STOCK AUDIO
- Previsualización funciona, pero falta forma de onda para navegar
- Botón "ver" abre ventana de Atenea en lugar de ir a la plataforma

### GUIONES
- Generar guion no funciona (texto + duración = nada)
- Error al procesar varios guiones (tanto locución como guion técnico)

### CREACIÓN DE VÍDEOS
- Al cambiar de avatar 2 a 4 en HeyGen, desaparecen IDs de voz y avatar (hay que copiarlos de nuevo)
- Icono "Mejorar vídeo" no funciona
- Crear vídeo con Avatar 4 no funciona
- Crear vídeo con Avatar 2 tampoco funciona
- En Vuela, botón "Scenes" no funciona (no muestra nada)

### AGENTE DE VÍDEO
- Los segundos que dice que va a usar no coinciden con la longitud del texto
- Solo podemos elegir la voz, pero nos cambia la voz (no es la elegida)
- No se puede rehacer el vídeo una vez creado
- Mientras procesa el guion, si navegas a otro sitio desaparece todo (pérdida de estado)
- En escenas no deja elegir avatar dentro de HeyGen (a veces da error)
- Error al cambiar escena a STOCK: `'NoneType' object has no attribute 'id'`
- Si quitas texto de una escena y guardas, no funciona
- "Empezar con IA" no funciona (vuelve a abrir la página)

### AUDIO
- ✅ Va super rápido, está genial
- No muestra créditos consumidos hasta salir de la pestaña
- Filtro de español en voces de HeyGen muestra voces que no son de España

### RECURSOS
- Los recursos no funcionan

---

## Priorización Decidida

### Prioridad 1: DESHABILITAR (Elementos que no funcionan)
**Objetivo**: Ocultar funcionalidades rotas para evitar frustración del usuario

- ✅ Deshabilitar icono "Mejorar Vídeo" → PRÓXIMAMENTE
- ⏳ Deshabilitar botón "Scenes" en Vuela.ai → PRÓXIMAMENTE
- ✅ Deshabilitar "Generar Guiones" (Sidebar) → PRÓXIMAMENTE
- ✅ Deshabilitar sección "Recursos" → PRÓXIMAMENTE

**Estado**: 3/4 completados (falta localizar "Scenes" de Vuela y "Mejorar Vídeo")

---

### Prioridad 2: CORREGIR HEYGEN (Problemas críticos)
**Objetivo**: Estabilizar el servicio de vídeo más usado

- Corregir selección de voz (no respeta la voz elegida)
- Guardar estado del agente de vídeo (parámetros, guion) al navegar entre pestañas
- Implementar funcionalidad para rehacer vídeo
- Corregir selección de avatar en escenas
- Corregir error al cambiar escena a STOCK (`'NoneType' object has no attribute 'id'`)
- Corregir guardado de escena sin texto
- Incluir partes faltantes en agente de vídeo

**Estado**: Pendiente

---

### Prioridad 3: CACHES EN INPUTS
**Objetivo**: Mejorar UX evitando pérdida de datos al navegar

- Implementar cache de IDs de voz y avatar en HeyGen (mantener al cambiar de avatar)
- Implementar cache de prompt al navegar entre /video e /imagen

**Estado**: Pendiente

---

### Prioridad 4: VISTA DE LISTA
**Objetivo**: Mejora de UX solicitada

- Implementar vista de lista para creaciones recientes
- Implementar vista de lista para proyectos
- Implementar vista de lista para bibliotecas

**Estado**: Pendiente

---

## Notas

- Los errores marcados con ✅ funcionan bien o son mejoras menores (no críticas)
- El resto de errores reportados quedan para después de estabilizar lo crítico
- Enfoque: primero estabilizar, luego mejorar

---

## Próximos Pasos

1. Completar deshabilitación de elementos rotos
2. Corregir problemas críticos de HeyGen
3. Implementar caches para mejorar UX
4. Añadir vista de lista
5. Testing intensivo con Ruth

**Meta**: Llegar al viernes con lo corregido que funcione y esté probado.

