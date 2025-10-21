/**
 * Configuración dinámica de modelos Veo
 * Maneja la UI del formulario según el modelo seleccionado
 */

// Configuración de cada modelo Veo (sincronizado con gemini_veo.py)
const VEO_MODELS_CONFIG = {
    'veo-2.0-generate-001': {
        version: '2.0',
        name: 'Veo 2.0',
        description: 'Modelo estable con lastFrame y extensión de video',
        badge: 'Estable',
        badgeColor: '#10b981',
        durationOptions: [5, 6, 7, 8],
        durationDefault: 8,
        features: {
            audio: false,
            resolution: false,
            resizeMode: false,
            referenceImages: false,
            lastFrame: true,
            videoExtension: true,
            mask: false
        }
    },
    'veo-2.0-generate-exp': {
        version: '2.0',
        name: 'Veo 2.0 Experimental',
        description: 'Soporta imágenes de referencia (asset Y style)',
        badge: 'Experimental',
        badgeColor: '#f59e0b',
        durationOptions: [5, 6, 7, 8],
        durationDefault: 8,
        durationFixed: 8, // Forzar 8s cuando se usan reference images
        features: {
            audio: false,
            resolution: false,
            resizeMode: false,
            referenceImages: true,
            referenceImageTypes: ['asset', 'style'], // Soporta ambos
            lastFrame: false,
            videoExtension: false,
            mask: false
        }
    },
    'veo-2.0-generate-preview': {
        version: '2.0',
        name: 'Veo 2.0 Preview',
        description: 'Edición de video con máscaras',
        badge: 'Preview',
        badgeColor: '#8b5cf6',
        durationOptions: [5, 6, 7, 8],
        durationDefault: 8,
        features: {
            audio: false,
            resolution: false,
            resizeMode: false,
            referenceImages: false,
            lastFrame: false,
            videoExtension: false,
            mask: true
        }
    },
    'veo-3.0-generate-001': {
        version: '3.0',
        name: 'Veo 3.0',
        description: 'Generación con audio y resolución hasta 1080p',
        badge: 'Con Audio',
        badgeColor: '#3b82f6',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: false,
            lastFrame: false,
            videoExtension: false,
            mask: false
        }
    },
    'veo-3.0-fast-generate-001': {
        version: '3.0',
        name: 'Veo 3.0 Fast',
        description: 'Generación rápida con audio',
        badge: 'Rápido',
        badgeColor: '#06b6d4',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: false,
            lastFrame: false,
            videoExtension: false,
            mask: false
        }
    },
    'veo-3.0-generate-preview': {
        version: '3.0',
        name: 'Veo 3.0 Preview',
        description: 'Con lastFrame y extensión de video',
        badge: 'Preview',
        badgeColor: '#8b5cf6',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: false,
            lastFrame: true,
            videoExtension: true,
            mask: false
        }
    },
    'veo-3.0-fast-generate-preview': {
        version: '3.0',
        name: 'Veo 3.0 Fast Preview',
        description: 'Rápido con audio',
        badge: 'Rápido',
        badgeColor: '#06b6d4',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: false,
            lastFrame: false,
            videoExtension: false,
            mask: false
        }
    },
    'veo-3.1-generate-preview': {
        version: '3.1',
        name: 'Veo 3.1 Preview',
        description: 'Última versión con todas las características',
        badge: 'Recomendado ⭐',
        badgeColor: '#10b981',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        durationFixed: 8, // Forzar 8s cuando se usan reference images
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: true,
            referenceImageTypes: ['asset'], // Solo asset, NO style
            lastFrame: true,
            videoExtension: false,
            mask: false
        }
    },
    'veo-3.1-fast-generate-preview': {
        version: '3.1',
        name: 'Veo 3.1 Fast',
        description: 'Más rápido con todas las características',
        badge: 'Rápido ⚡',
        badgeColor: '#06b6d4',
        durationOptions: [4, 6, 8],
        durationDefault: 8,
        durationFixed: 8, // Forzar 8s cuando se usan reference images
        features: {
            audio: true,
            resolution: true,
            resizeMode: true,
            referenceImages: true,
            referenceImageTypes: ['asset'], // Solo asset, NO style
            lastFrame: true,
            videoExtension: false,
            mask: false
        }
    }
};

/**
 * Actualiza la UI según el modelo seleccionado
 */
function updateVeoModelFeatures(modelId) {
    const config = VEO_MODELS_CONFIG[modelId];
    
    if (!config) {
        console.error('Modelo no encontrado:', modelId);
        return;
    }
    
    console.log('Actualizando UI para modelo:', modelId, config);
    
    // Actualizar descripción del modelo
    updateModelDescription(config);
    
    // Actualizar opciones de duración
    updateDurationOptions(config);
    
    // Mostrar/ocultar características según el modelo
    toggleFeature('veo3-features', config.features.audio);
    toggleFeature('reference-images-section', config.features.referenceImages);
    toggleFeature('last-frame-section', config.features.lastFrame);
    toggleFeature('video-extension-section', config.features.videoExtension);
    toggleFeature('mask-section', config.features.mask);
    
    // Actualizar tipos de reference images permitidos
    if (config.features.referenceImages) {
        updateReferenceImageTypes(config.features.referenceImageTypes);
    }
    
    // Actualizar hints y validaciones
    updateFormHints(config);
}

/**
 * Actualiza la descripción del modelo
 */
function updateModelDescription(config) {
    const descElement = document.getElementById('model-description');
    if (!descElement) return;
    
    descElement.innerHTML = `
        <span style="display: inline-flex; align-items: center; gap: 0.5rem;">
            <span style="background: ${config.badgeColor}; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">
                ${config.badge}
            </span>
            <span>${config.description}</span>
        </span>
    `;
}

/**
 * Actualiza las opciones de duración disponibles
 */
function updateDurationOptions(config) {
    const durationSelect = document.getElementById('veo-duration');
    if (!durationSelect) return;
    
    // Limpiar opciones actuales
    durationSelect.innerHTML = '';
    
    // Agregar nuevas opciones
    config.durationOptions.forEach(duration => {
        const option = document.createElement('option');
        option.value = duration;
        option.textContent = `${duration} segundos`;
        if (duration === config.durationDefault) {
            option.selected = true;
        }
        durationSelect.appendChild(option);
    });
    
    // Actualizar hint de duración
    const durationHint = document.getElementById('duration-hint');
    if (durationHint) {
        let hintText = `Opciones: ${config.durationOptions.join(', ')} segundos.`;
        
        if (config.features.referenceImages) {
            hintText += ' <strong>IMPORTANTE: Debe ser 8 segundos si usas imágenes de referencia.</strong>';
        }
        
        durationHint.innerHTML = hintText;
    }
}

/**
 * Muestra u oculta una sección
 */
function toggleFeature(elementId, show) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.style.display = show ? 'block' : 'none';
    
    // Deshabilitar inputs de secciones ocultas
    if (!show) {
        element.querySelectorAll('input, select, textarea').forEach(input => {
            input.disabled = true;
        });
    } else {
        element.querySelectorAll('input, select, textarea').forEach(input => {
            input.disabled = false;
        });
    }
}

/**
 * Actualiza los tipos de reference images permitidos
 */
function updateReferenceImageTypes(allowedTypes) {
    const typeSelects = ['ref-type-1', 'ref-type-2', 'ref-type-3'];
    
    typeSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Guardar valor actual
        const currentValue = select.value;
        
        // Limpiar y reconstruir opciones
        select.innerHTML = '';
        
        if (allowedTypes.includes('asset')) {
            const option = document.createElement('option');
            option.value = 'asset';
            option.textContent = 'Asset (Personaje/Objeto/Escena)';
            select.appendChild(option);
        }
        
        if (allowedTypes.includes('style')) {
            const option = document.createElement('option');
            option.value = 'style';
            option.textContent = 'Style (Estilo Visual)';
            select.appendChild(option);
        }
        
        // Restaurar valor si aún es válido
        if (allowedTypes.includes(currentValue)) {
            select.value = currentValue;
        }
    });
    
    // Actualizar hint
    const refHint = document.getElementById('reference-images-hint');
    if (refHint) {
        if (allowedTypes.includes('style')) {
            refHint.innerHTML = `
                💡 <strong>Asset:</strong> Mantiene personajes/objetos/escenas consistentes (hasta 3)<br>
                💡 <strong>Style:</strong> Aplica un estilo visual artístico (solo 1 permitida)
            `;
        } else {
            refHint.innerHTML = `
                💡 <strong>Asset:</strong> Mantiene personajes/objetos/escenas consistentes (hasta 3)<br>
                ⚠️ <strong>Nota:</strong> Veo 3.1 no soporta imágenes de estilo (style)
            `;
        }
    }
}

/**
 * Actualiza hints y mensajes de ayuda
 */
function updateFormHints(config) {
    // Hint para resize mode (solo Veo 3 con image-to-video)
    const resizeModeGroup = document.getElementById('resize-mode-group');
    if (resizeModeGroup) {
        if (config.features.resizeMode) {
            resizeModeGroup.style.display = 'block';
        } else {
            resizeModeGroup.style.display = 'none';
        }
    }
}

/**
 * Valida el formulario antes de enviar
 */
function validateVeoForm(modelId) {
    const config = VEO_MODELS_CONFIG[modelId];
    if (!config) return true;
    
    const errors = [];
    
    // Validar duración con reference images
    if (config.features.referenceImages) {
        const hasRefImages = document.querySelector('#ref-image-1')?.files?.length > 0 ||
                           document.querySelector('#ref-image-2')?.files?.length > 0 ||
                           document.querySelector('#ref-image-3')?.files?.length > 0;
        
        if (hasRefImages) {
            const duration = parseInt(document.getElementById('veo-duration')?.value);
            if (duration !== 8) {
                errors.push('❌ Con imágenes de referencia, la duración debe ser 8 segundos.');
            }
        }
    }
    
    // Validar style images (solo 1 permitida en Veo 2.0-exp)
    if (config.features.referenceImages && config.features.referenceImageTypes.includes('style')) {
        const styleCount = Array.from(document.querySelectorAll('[id^="ref-type-"]'))
            .filter(select => select.value === 'style')
            .length;
        
        if (styleCount > 1) {
            errors.push('❌ Solo puedes usar 1 imagen de tipo "Style".');
        }
    }
    
    // Mostrar errores si hay
    if (errors.length > 0) {
        alert(errors.join('\n\n'));
        return false;
    }
    
    return true;
}

/**
 * Monitorear cambios en reference images para validar duración
 */
function setupReferenceImagesMonitoring() {
    const refImageInputs = ['ref-image-1', 'ref-image-2', 'ref-image-3'];
    
    refImageInputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (!input) return;
        
        input.addEventListener('change', function() {
            const modelId = document.getElementById('veo-model-select')?.value;
            const config = VEO_MODELS_CONFIG[modelId];
            
            if (!config || !config.features.referenceImages) return;
            
            // Si se sube una imagen de referencia, forzar duración a 8s
            const hasAnyRefImage = refImageInputs.some(id => 
                document.getElementById(id)?.files?.length > 0
            );
            
            if (hasAnyRefImage) {
                const durationSelect = document.getElementById('veo-duration');
                if (durationSelect) {
                    durationSelect.value = '8';
                    
                    // Mostrar advertencia
                    const durationHint = document.getElementById('duration-hint');
                    if (durationHint) {
                        durationHint.innerHTML = '⚠️ <strong>Duración automáticamente ajustada a 8 segundos</strong> (requerido para imágenes de referencia)';
                        durationHint.style.color = '#92400e';
                        durationHint.style.fontWeight = '600';
                    }
                }
            }
        });
    });
}

/**
 * Inicialización
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando veo-models.js');
    
    // Configurar el selector de modelo
    const modelSelect = document.getElementById('veo-model-select');
    if (modelSelect) {
        // Actualizar UI cuando cambia el modelo
        modelSelect.addEventListener('change', function() {
            updateVeoModelFeatures(this.value);
        });
        
        // Inicializar con el modelo por defecto
        if (modelSelect.value) {
            updateVeoModelFeatures(modelSelect.value);
        }
    }
    
    // Configurar monitoreo de reference images
    setupReferenceImagesMonitoring();
    
    console.log('veo-models.js inicializado correctamente');
});

