/**
 * Modal de selección de voces ElevenLabs - Reutilizable
 * Puede ser usado en cualquier template con diferentes callbacks
 */

// Cache global de voces (compartido entre todos los modales)
let globalVoicesCache = null;

/**
 * Abre el modal de selección de voces
 * @param {Object} config - Configuración del modal
 * @param {string} config.modalId - ID único del modal (ej: 'voice-modal-inspector')
 * @param {Function} config.onSelect - Callback cuando se selecciona una voz (voiceId, voiceName, voiceCategory)
 * @param {string} config.apiUrl - URL del endpoint de voces (opcional, usa default si no se proporciona)
 * @param {string} config.filterPrefix - Prefijo para funciones de filtro (ej: 'inspector', 'manual')
 */
async function openVoiceModal(config) {
    const {
        modalId = 'voice-modal-generic',
        onSelect = null,
        apiUrl = null,
        filterPrefix = 'generic'
    } = config;
    
    // Cargar voces si no están en cache global
    if (!globalVoicesCache) {
        try {
            // Usar URL por defecto si no se proporciona
            const url = apiUrl || (typeof window !== 'undefined' && window.location ? window.location.origin + '/api/elevenlabs/voices/' : '/api/elevenlabs/voices/');
            const response = await fetch(url);
            const data = await response.json();
            globalVoicesCache = data.voices || [];
        } catch (error) {
            console.error('Error cargando voces:', error);
            alert('Error al cargar voces de ElevenLabs');
            return;
        }
    }
    
    // Crear y mostrar modal usando la función interna
    createVoiceModalInternal({
        modalId,
        voices: globalVoicesCache,
        onSelect,
        filterPrefix
    });
}

/**
 * Crea el modal de voces (función interna)
 */
function createVoiceModalInternal(config) {
    const {
        modalId,
        voices,
        onSelect,
        filterPrefix
    } = config;
    
    // Eliminar modal anterior si existe
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Crear modal
    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4';
    
    // Función de cierre específica para este modal
    const closeFunctionName = `closeVoiceModal_${filterPrefix}`;
    window[closeFunctionName] = function() {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.remove();
        }
    };
    
    // Función de selección específica
    const selectFunctionName = `selectVoice_${filterPrefix}`;
    window[selectFunctionName] = function(voiceId, voiceName, voiceCategory) {
        if (onSelect) {
            onSelect(voiceId, voiceName, voiceCategory);
        }
        window[closeFunctionName]();
    };
    
    // Función de renderizado de cards
    const renderCards = () => {
        if (!voices || voices.length === 0) {
            return '<div class="col-span-3 text-center py-12"><p class="text-gray-500">No hay voces disponibles</p></div>';
        }
        
        return voices.map(voice => {
            const labels = voice.labels || {};
            const labelsHtml = Object.values(labels).map(label => 
                `<span class="inline-block bg-gray-100 text-gray-700 rounded-full px-2 py-1 text-xs">${escapeHtml(label)}</span>`
            ).join('');
            
            const gender = labels.gender || labels.Gender || 'unknown';
            const language = labels.language || labels.Language || labels.accent || labels.Accent || 'unknown';
            const accent = labels.accent || labels.Accent || '';
            const voiceName = escapeHtml(voice.name || voice.display_name || voice.voice_name || `Voz ${voice.voice_id?.substring(0, 8) || 'Desconocida'}`);
            const voiceId = escapeHtml(voice.voice_id);
            const category = escapeHtml(voice.category || 'premade');
            const description = voice.description ? escapeHtml(voice.description) : '';
            const previewUrl = voice.preview_url ? escapeHtml(voice.preview_url) : '';
            
            return `
                <div class="voice-card border-2 border-gray-200 rounded-xl p-5 hover:border-green-500 hover:shadow-lg transition-all cursor-pointer bg-white" 
                     data-voice-id="${voiceId}"
                     data-voice-name="${voiceName}"
                     data-voice-category="${category}"
                     data-voice-gender="${gender.toLowerCase()}"
                     data-voice-language="${language.toLowerCase()}"
                     data-voice-accent="${accent.toLowerCase()}"
                     onclick="${selectFunctionName}('${voiceId}', '${voiceName}', '${category}')">
                    
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex-1">
                            <h3 class="font-bold text-gray-900 text-lg">${voiceName}</h3>
                            <p class="text-xs text-gray-500 uppercase tracking-wide mt-1">${category} • ${voice.language || 'Desconocido'}</p>
                        </div>
                        <div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <span class="text-xl">🎙️</span>
                        </div>
                    </div>
                    
                    ${description ? `<p class="text-sm text-gray-700 mb-3">${description}</p>` : ''}
                    
                    ${labelsHtml ? `<div class="flex flex-wrap gap-1 mb-3">${labelsHtml}</div>` : ''}
                    
                    ${previewUrl ? `
                        <div class="mt-3" onclick="event.stopPropagation();">
                            <audio controls preload="none" class="w-full h-8">
                                <source src="${previewUrl}" type="audio/mpeg">
                            </audio>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    };
    
    // Estado de filtros
    const filterStateName = `voiceFilters_${filterPrefix}`;
    window[filterStateName] = {
        gender: 'all',
        language: 'all',
        search: ''
    };
    
    // Función de toggle de filtros
    const toggleFilterName = `toggleVoiceFilter_${filterPrefix}`;
    window[toggleFilterName] = function(filterType, value) {
        window[filterStateName][filterType] = value;
        
        // Actualizar UI de botones
        document.querySelectorAll(`.voice-filter-btn-${filterPrefix}[data-filter="${filterType}"]`).forEach(btn => {
            if (btn.dataset.value === value) {
                btn.classList.remove('bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');
                btn.classList.add('bg-green-600', 'text-white');
            } else {
                btn.classList.remove('bg-green-600', 'text-white');
                btn.classList.add('bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');
            }
        });
        
        applyVoiceFilters(filterPrefix, modalId);
    };
    
    // Función de aplicación de filtros
    const applyFiltersName = `applyVoiceFilters_${filterPrefix}`;
    window[applyFiltersName] = function() {
        applyVoiceFilters(filterPrefix, modalId);
    };
    
    modal.innerHTML = `
        <div class="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
            <!-- Header -->
            <div class="bg-gradient-to-r from-green-500 to-green-600 px-6 py-5 flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-bold text-white">Catálogo de Voces ElevenLabs</h2>
                    <p class="text-green-100 text-sm mt-1" id="voice-count-${filterPrefix}">${voices.length} voces disponibles</p>
                </div>
                <button type="button" onclick="${closeFunctionName}()" 
                        class="text-white hover:text-green-100 text-3xl leading-none">
                    &times;
                </button>
            </div>
            
            <!-- Buscador y Filtros -->
            <div class="px-6 py-4 bg-gray-50 border-b">
                <input type="text" id="voice-search-${filterPrefix}" placeholder="🔍 Buscar por nombre, acento, género..." 
                       class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 mb-3"
                       oninput="${applyFiltersName}()">
                
                <!-- Filtros -->
                <div class="flex flex-wrap gap-2">
                    <span class="text-sm font-medium text-gray-700 self-center">Filtros:</span>
                    
                    <!-- Género -->
                    <button type="button" onclick="${toggleFilterName}('gender', 'all')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-green-600 text-white" 
                            data-filter="gender" data-value="all">
                        Todos
                    </button>
                    <button type="button" onclick="${toggleFilterName}('gender', 'male')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-gray-200 text-gray-700 hover:bg-gray-300" 
                            data-filter="gender" data-value="male">
                        👨 Masculino
                    </button>
                    <button type="button" onclick="${toggleFilterName}('gender', 'female')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-gray-200 text-gray-700 hover:bg-gray-300" 
                            data-filter="gender" data-value="female">
                        👩 Femenino
                    </button>
                    
                    <!-- Idioma -->
                    <button type="button" onclick="${toggleFilterName}('language', 'all')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-green-600 text-white" 
                            data-filter="language" data-value="all">
                        Todos
                    </button>
                    <button type="button" onclick="${toggleFilterName}('language', 'es')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-gray-200 text-gray-700 hover:bg-gray-300" 
                            data-filter="language" data-value="es">
                        🇪🇸 Español
                    </button>
                    <button type="button" onclick="${toggleFilterName}('language', 'en')" 
                            class="voice-filter-btn-${filterPrefix} px-3 py-1 rounded-full text-sm font-medium transition-colors bg-gray-200 text-gray-700 hover:bg-gray-300" 
                            data-filter="language" data-value="en">
                        🇬🇧 Inglés
                    </button>
                </div>
            </div>
            
            <!-- Lista de Voces -->
            <div class="overflow-y-auto p-6" style="max-height: calc(90vh - 200px);">
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="voices-grid-${filterPrefix}">
                    ${renderCards()}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Inicializar filtros
    applyVoiceFilters(filterPrefix, modalId);
}

/**
 * Aplica filtros a las voces del modal
 */
function applyVoiceFilters(filterPrefix, modalId) {
    const filterState = window[`voiceFilters_${filterPrefix}`];
    const searchInput = document.getElementById(`voice-search-${filterPrefix}`);
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    filterState.search = searchTerm;
    
    const cards = document.querySelectorAll(`#voices-grid-${filterPrefix} .voice-card`);
    let visibleCount = 0;
    
    cards.forEach(card => {
        const voiceName = (card.dataset.voiceName || '').toLowerCase();
        const voiceCategory = (card.dataset.voiceCategory || '').toLowerCase();
        const voiceGender = card.dataset.voiceGender || 'unknown';
        const voiceLanguage = card.dataset.voiceLanguage || 'unknown';
        const text = card.textContent.toLowerCase();
        
        const matchesSearch = !filterState.search || 
            voiceName.includes(filterState.search) || 
            voiceCategory.includes(filterState.search) || 
            text.includes(filterState.search);
        
        const matchesGender = filterState.gender === 'all' || 
            voiceGender === filterState.gender.toLowerCase();
        
        const matchesLanguage = filterState.language === 'all' || 
            voiceLanguage.includes(filterState.language.toLowerCase());
        
        if (matchesSearch && matchesGender && matchesLanguage) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // Actualizar contador
    const countElement = document.getElementById(`voice-count-${filterPrefix}`);
    if (countElement) {
        countElement.textContent = `${visibleCount} voces disponibles`;
    }
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

