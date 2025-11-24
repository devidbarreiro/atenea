# Guía de Renderizado de Contenido en el Chat

## 📚 Librerías Disponibles en `base.html`

### Librerías Incluidas

1. **Tailwind CSS** (CDN)
   - Framework CSS utility-first
   - Disponible globalmente
   - Usar clases Tailwind para estilos

2. **Alpine.js** (v3.13.5)
   - Framework JavaScript reactivo
   - Usado para interactividad del chat
   - `x-data`, `x-show`, `x-for`, etc.

3. **Marked.js** (v12.0.0)
   - Renderizado de Markdown
   - Disponible como `marked.parse(text)`
   - Usado para formatear respuestas del agente

4. **HTMX** (v1.9.10)
   - Interactividad sin JavaScript complejo
   - No necesario para el chat (usamos Alpine.js)

## 🎨 Patrones de Renderizado

### 1. Imágenes

**HTML básico:**
```html
<img src="{{ signed_url }}" 
     alt="{{ title }}" 
     class="max-w-full max-h-[400px] object-contain rounded-lg shadow-2xl">
```

**Estados:**
- ✅ `completed`: Muestra imagen con `signed_url`
- ⏳ `processing`: Spinner + mensaje "Generando imagen..."
- ❌ `error`: Mensaje de error
- ⏸️ `pending`: Mensaje "Imagen pendiente"

**Ejemplo en chat:**
```javascript
if (status === 'completed' && preview_url) {
    return `
        <div class="bg-gray-900 rounded-lg p-4 mb-3 flex items-center justify-center">
            <img src="${preview_url}" 
                 alt="${title}" 
                 class="max-w-full max-h-[400px] object-contain rounded-lg shadow-2xl">
        </div>
    `;
}
```

### 2. Videos

**HTML básico:**
```html
<video src="{{ signed_url }}" 
       controls 
       class="w-full h-full rounded-lg"
       preload="metadata">
</video>
```

**Estados:**
- ✅ `completed`: Player HTML5 con `signed_url`
- ⏳ `processing`: Spinner + mensaje "Generando video..."
- ❌ `error`: Mensaje de error
- ⏸️ `pending`: Mensaje "Video pendiente"

**Ejemplo en chat:**
```javascript
if (status === 'completed' && preview_url) {
    return `
        <div class="bg-gray-900 rounded-lg mb-3 aspect-video">
            <video src="${preview_url}" 
                   controls 
                   class="w-full h-full rounded-lg"
                   preload="metadata">
            </video>
        </div>
    `;
}
```

**Nota:** Usar `aspect-video` (16:9) para mantener proporción correcta.

### 3. Audios

**HTML básico:**
```html
<audio controls class="w-full">
    <source src="{{ signed_url }}" type="audio/mpeg">
    Tu navegador no soporta el elemento de audio.
</audio>
```

**Estados:**
- ✅ `completed`: Player HTML5 con `signed_url`
- ⏳ `processing`: Spinner + mensaje "Generando audio..."
- ❌ `error`: Mensaje de error
- ⏸️ `pending`: Mensaje "Audio pendiente"

**Ejemplo en chat:**
```javascript
if (status === 'completed' && preview_url) {
    return `
        <div class="bg-white rounded-lg p-4 mb-3">
            <audio controls class="w-full">
                <source src="${preview_url}" type="audio/mpeg">
                Tu navegador no soporta el elemento de audio.
            </audio>
        </div>
    `;
}
```

## 🎯 Estructura de Tool Output

Cada tool debe retornar un objeto con esta estructura:

```javascript
{
    status: 'success' | 'error' | 'partial_success',
    image_id: 123,              // Para imágenes
    video_id: 456,              // Para videos
    audio_id: 789,              // Para audios
    title: 'Título del contenido',
    message: 'Mensaje descriptivo',
    preview_url: 'https://...',  // URL firmada (si está disponible)
    detail_url: '/images/123/', // Link a página de detalle
    status_current: 'completed' | 'processing' | 'pending' | 'error'
}
```

## 🔄 Flujo de Renderizado en el Chat

1. **Usuario envía mensaje** → `sendMessage()`
2. **Backend procesa** → `CreationAgentChatView`
3. **Agente ejecuta tool** → `create_image_tool()`
4. **Tool retorna resultado** → `{ image_id, preview_url, ... }`
5. **Frontend recibe** → `data.tool_results`
6. **Alpine.js renderiza** → `renderContent(message)`
7. **Muestra preview** → HTML generado dinámicamente

## 📝 Función `renderContent()` en el Chat

La función `renderContent()` en `templates/chat/creation_agent.html`:

1. Renderiza markdown del mensaje del agente
2. Itera sobre `tool_results`
3. Detecta tipo de contenido (`image_id`, `video_id`, `audio_id`)
4. Genera HTML según estado (`completed`, `processing`, etc.)
5. Agrega link a página de detalle

## ✅ Checklist de Renderizado

### Imágenes
- [x] Renderiza imagen con `signed_url` cuando `status === 'completed'`
- [x] Muestra spinner cuando `status === 'processing'`
- [x] Muestra mensaje de error cuando `status === 'error'`
- [x] Muestra mensaje pendiente cuando `status === 'pending'`
- [x] Link a página de detalle funciona

### Videos (Preparado)
- [x] Estructura HTML preparada
- [x] Player HTML5 con controles
- [x] Manejo de estados
- [ ] Probar cuando `create_video_tool` esté listo

### Audios (Preparado)
- [x] Estructura HTML preparada
- [x] Player HTML5 con controles
- [x] Manejo de estados
- [ ] Probar cuando `create_audio_tool` esté listo

## 🎨 Clases Tailwind Usadas

### Contenedores
- `bg-gray-900` - Fondo oscuro para media
- `bg-green-50` - Fondo verde claro para imágenes
- `bg-blue-50` - Fondo azul claro para videos
- `bg-purple-50` - Fondo morado claro para audios
- `rounded-lg` - Bordes redondeados
- `p-4` - Padding estándar
- `mb-3` - Margen inferior

### Imágenes
- `max-w-full` - Ancho máximo 100%
- `max-h-[400px]` - Altura máxima 400px
- `object-contain` - Mantener proporción
- `shadow-2xl` - Sombra grande

### Videos
- `aspect-video` - Proporción 16:9
- `w-full h-full` - Tamaño completo

### Estados
- `animate-spin` - Spinner animado
- `animate-pulse` - Pulso animado

## 🚀 Próximos Pasos

1. ✅ Renderizado de imágenes implementado
2. ⏳ Agregar polling para actualizar estados (`processing` → `completed`)
3. ⏳ Implementar `create_video_tool` y probar renderizado
4. ⏳ Implementar `create_audio_tool` y probar renderizado
5. ⏳ Agregar previews de guiones (texto formateado)


