# Planificación Semana 15/12

## Prioridades

1. **Deshabilitar** (elementos que no funcionan)
2. **Corregir HeyGen** (problemas críticos)
3. **Caches** (inputs que se pierden)
4. **Listas/Cuadrícula** (vista de proyectos y bibliotecas)

---

## 1. DESHABILITAR ELEMENTOS

### 1.1 Icono "Mejorar Vídeo"
- **Estado**: No funciona
- **Acción**: Deshabilitar y poner "PRÓXIMAMENTE"

### 1.2 Botón "Scenes" en Vuela.ai
- **Estado**: No funciona, no muestra nada al generar vídeo
- **Acción**: Deshabilitar y poner "PRÓXIMAMENTE"

### 1.3 Generar Guiones (Sidebar)
- **Estado**: No funciona
  - Generar guion no funciona (texto + duración = nada)
  - Error al procesar varios guiones
  - Error tanto con guion solo de locución como con guion técnico con explicación de escenas
- **Acción**: Deshabilitar botón y poner "PRÓXIMAMENTE"

### 1.4 Recursos
- **Estado**: No funcionan
- **Acción**: Deshabilitar (PRÓXIMAMENTE)

---

## 2. CORREGIR HEYGEN

### 2.1 Agente de Vídeo - Problemas Generales
- **Voz incorrecta**: Actualmente solo podemos elegir la voz, pero nos cambia la voz, no es la voz que hemos elegido
- **Rehacer vídeo**: Necesitamos poder rehacer el vídeo y corregir cosas que hayan podido salir mal una vez creado
- **Pérdida de estado**: Mientras procesa el guion no puedo ir a otro sitio porque me desaparece todo y al volver a la pestaña no se quedan los parámetros ni el guion ni nada de lo que había escrito

### 2.2 Escenas en HeyGen
- **Avatar no seleccionable**: En las escenas no me deja elegir avatar dentro de HeyGen y a veces da error
- **Error al cambiar a STOCK**: Cuando intento cambiar una escena a STOCK da error: `Error: 'NoneType' object has no attribute 'id'`
- **Guardar sin texto**: Si quito texto de una escena y le doy a guardar no funciona

### 2.3 Funcionalidades Faltantes
- Deberíamos poder incluir dentro del agente de vídeo las partes de [pendiente especificar qué partes]

---

## 3. CACHES EN INPUTS

### 3.1 HeyGen - IDs de Voz y Avatar
- **Problema**: Cuando voy a sacar un vídeo en HeyGen y ya he copiado el ID de la voz y del avatar, si cambio de avatar 2 a 4 me desaparece todo y tengo que volver a copiarlo y pegarlo

### 3.2 Navegación entre /video e /imagen
- **Problema**: Cuando se mueve entre /video /imagen pierdo los inputs del campo prompt

---

## 4. LISTAS/CUADRÍCULA - PROYECTOS Y BIBLIOTECAS

### 4.1 Vista de Lista
- **Requisito**: Sería interesante poder ver las creaciones recientes o los proyectos y las bibliotecas también en formato lista
- **Acción**: Implementar vista de lista además de la vista de cuadrícula actual

---

## 5. MANIM QUOTE

### 5.1 Animación de Entrada
- **Cambio requerido**: Modificar la animación de entrada por otra que sería de escalado desde la esquina inferior izquierda

### 5.2 Control de Tiempo
- **Requisito**: Poder decidir el tiempo que se queda en pantalla o el párrafo concreto que tiene que cubrir

### 5.3 Animación de Salida
- **Cambio requerido**: La salida debe ser al corte, sin animación

---

## 6. CREACIÓN DE IMÁGENES

### 6.1 Resolución
- **Problema**: Al crear una imagen no me deja poner la resolución a la que quiero crearla
- **Solución**: Se necesitaría algo para re-escalarla en calidad en el caso de que fuera necesario

### 6.2 Error al Volver al Proyecto
- **Problema**: Al darte atrás después de descargar una imagen no encuentra el proyecto
- **Error**: `Error: Proyecto no encontrado` cuando intento volver a generar una imagen

---

## 7. CREACIÓN DE VÍDEOS

### 7.1 Icono "Mejorar Vídeo"
- Ver sección 1.1 (DESHABILITAR)

### 7.2 Botón "Scenes" en Vuela.ai
- Ver sección 1.2 (DESHABILITAR)

---

## 8. AUDIO

### 8.1 Rendimiento
- **Estado**: ✅ Va super rápido, está genéral

### 8.2 Créditos
- **Problema**: No te dice los créditos que te ha quitado hasta que sales de la pestaña de audio y vas a otra
- **Solución**: Mostrar créditos consumidos inmediatamente después de la generación

### 8.3 Filtro de Español en HeyGen
- **Problema**: El filtro de español cuando selecciono una voz de HeyGen me saca voces que son de fuera
- **Solución**: Corregir el filtro para que solo muestre voces realmente en español

---

## Resumen de Tareas por Prioridad

### Prioridad 1: Deshabilitar
- [ ] Deshabilitar icono "Mejorar Vídeo" → PRÓXIMAMENTE
- [ ] Deshabilitar botón "Scenes" en Vuela.ai → PRÓXIMAMENTE
- [ ] Deshabilitar "Generar Guiones" (Sidebar) → PRÓXIMAMENTE
- [ ] Deshabilitar sección "Recursos" (PRÓXIMAMENTE)

### Prioridad 2: Corregir HeyGen
- [ ] Corregir selección de voz (no cambia la voz elegida)
- [ ] Implementar funcionalidad para rehacer vídeo
- [ ] Guardar estado del agente de vídeo (parámetros, guion) al navegar
- [ ] Corregir selección de avatar en escenas
- [ ] Corregir error al cambiar escena a STOCK (`'NoneType' object has no attribute 'id'`)
- [ ] Corregir guardado de escena sin texto
- [ ] Incluir partes faltantes en agente de vídeo

### Prioridad 3: Caches
- [ ] Implementar cache de IDs de voz y avatar en HeyGen
- [ ] Implementar cache de prompt al navegar entre /video e /imagen

### Prioridad 4: Listas/Cuadrícula
- [ ] Implementar vista de lista para creaciones recientes
- [ ] Implementar vista de lista para proyectos
- [ ] Implementar vista de lista para bibliotecas

### Otras Tareas
- [ ] Modificar animación de entrada Manim Quote (escalado desde esquina inferior izquierda)
- [ ] Añadir control de tiempo/párrafo en Manim Quote
- [ ] Cambiar animación de salida Manim Quote (al corte, sin animación)
- [ ] Añadir selector de resolución en creación de imágenes
- [ ] Implementar re-escalado de imágenes en calidad
- [ ] Corregir error "Proyecto no encontrado" al volver después de descargar imagen
- [ ] Mostrar créditos consumidos inmediatamente en Audio
- [ ] Corregir filtro de español en voces de HeyGen

