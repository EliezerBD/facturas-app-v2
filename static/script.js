// La configuración de Supabase se ha movido al backend por seguridad (ahora se usa la librería global si fuera necesario)
// const supabase = null;

// Inicializar los iconos de la librería Lucide
lucide.createIcons();

// Conjunto para almacenar los IDs de los archivos seleccionados por el usuario
let selectedFiles = new Set();
// Arreglo para almacenar los resultados actuales de la búsqueda de correos
let currentResults = [];
// Almacenar el email del usuario actual para el historial
let currentUserEmail = '';

// Selección de elementos del DOM para manipular la interfaz
const loginScreen = document.getElementById('login-screen'); // Pantalla de inicio de sesión
const mainScreen = document.getElementById('main-screen');   // Pantalla principal de la aplicación
const heroSection = document.getElementById('hero-section'); // Sección de presentación (hero)
const userBadge = document.getElementById('user-badge');     // Distintivo que muestra el usuario conectado
const resultsList = document.getElementById('results-list'); // Contenedor de la lista de resultados
const resultsCountLabel = document.getElementById('results-count'); // Etiqueta con el total de encontrados
const actionBar = document.getElementById('action-bar');     // Barra de acciones para archivos seleccionados
const selectedCountLabel = document.getElementById('selected-count'); // Etiqueta con el total de seleccionados
const selectionControls = document.getElementById('selection-controls'); // Controles de selección global
const userEmailLabel = document.getElementById('user-email'); // Etiqueta para mostrar el email del usuario

// --- LÓGICA DE AUTENTICACIÓN ---

/**
 * Analiza los parámetros del hash en la URL para verificar si el login fue exitoso.
 */
function parseHashParams() {
    const hash = window.location.hash.substring(1);
    return {
        authSuccess: hash.startsWith('auth_success')
    };
}

async function checkAuthStatus() {
    console.log("Verificando conexión con el servidor...");
    try {
        const pingRes = await fetch('/api/ping');
        const pingData = await pingRes.json();
        console.log("Servidor responde:", pingData);
    } catch (e) {
        console.error("ERROR: No se pudo conectar con el servidor Flask en Docker.");
        showToast("Error crítico: No hay conexión con el servidor", "error");
    }

    const { authSuccess } = parseHashParams();

    if (authSuccess) {
        // Si el hash indica éxito en la autenticación, se consulta al backend por la sesión
        try {
            const response = await fetch('/auth/check-session');
            if (response.ok) {
                const data = await response.json();
                currentUserEmail = data.email;
                showMainApp(data.email); // Mostrar la aplicación con el email del usuario
            } else {
                showMainApp(); // Mostrar la aplicación sin email si no se obtuvo
            }
        } catch (e) {
            showMainApp();
        }

        // Limpiar el hash de la URL para una apariencia más limpia
        history.replaceState(null, null, ' ');
        showToast("Conectado a Gmail correctamente", "success");
    } else {
        // Si no hay hash de éxito, se verifica si ya existe una sesión activa
        try {
            const response = await fetch('/auth/check-session');
            if (response.ok) {
                const data = await response.json();
                currentUserEmail = data.email;
                showMainApp(data.email);
            }
        } catch (error) {
            console.error('Error verificando sesión:', error);
        }
    }
}

/**
 * Cambia la visibilidad de las pantallas para mostrar la interfaz principal de la aplicación.
 */
function showMainApp(email) {
    if (!loginScreen || !heroSection || !mainScreen || !userBadge) return;
    loginScreen.classList.add('hidden'); // Ocultar login
    heroSection.classList.add('hidden'); // Ocultar sección hero
    mainScreen.classList.remove('hidden'); // Mostrar aplicación
    userBadge.classList.remove('hidden');   // Mostrar distintivo de usuario
    if (email) {
        userEmailLabel.innerText = email; // Mostrar el email del usuario conectado
    }
}

/**
 * Inicia el proceso de login redirigiendo al usuario a la URL de Google proporcionada por el backend.
 */
async function mockLogin() {
    try {
        console.log("Iniciando login...");
        showToast("Conectando con Google...", "info");

        const response = await fetch('/auth/google');
        console.log("Respuesta de /auth/google recibida. Status:", response.status);

        const data = await response.json();
        console.log("Datos recibidos:", data);

        if (data.authUrl) {
            console.log("Redirigiendo a:", data.authUrl);
            window.location.href = data.authUrl; // Redirigir a Google
        } else {
            console.error("No se recibió authUrl");
            showToast("Error al conectar con Google", "error");
        }
    } catch (error) {
        console.error("Error en mockLogin:", error);
        showToast("Error de conexión", "error");
    }
}

/**
 * Cierra la sesión activa y recarga la página para volver al estado inicial.
 */
async function logout() {
    await fetch('/auth/logout', { method: 'POST' });
    location.reload();
}

// --- LÓGICA DE BÚSQUEDA ---

/**
 * Captura los filtros de búsqueda y realiza la petición al servidor para encontrar correos.
 */
async function simulateSearch() {
    const searchTerm = document.getElementById('search-input').value; // Término de búsqueda
    const fileType = document.getElementById('file-type').value;      // Filtro de extensión de archivo
    const startDate = document.getElementById('start-date').value;   // Fecha de inicio
    const endDate = document.getElementById('end-date').value;       // Fecha de fin

    // Mostrar estado de carga en la lista de resultados
    resultsList.innerHTML = `<div class="flex flex-col items-center justify-center py-20 animate-pulse"><div class="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div><p class="text-slate-500">Escaneando bandeja de entrada...</p></div>`;

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                search: searchTerm,
                startDate: startDate,
                endDate: endDate,
                fileType: fileType
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentResults = data.emails; // Guardar los correos encontrados
            renderResults();             // Dibujar los resultados en pantalla
            if (currentResults.length === 0) {
                // Mostrar mensaje si no hubo coincidencias
                resultsList.innerHTML = `
                    <div id="empty-state" class="flex flex-col items-center justify-center py-20 px-6 text-center">
                        <div class="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4 text-slate-400">
                            <i data-lucide="inbox" class="w-10 h-10"></i>
                        </div>
                        <h4 class="text-lg font-semibold text-slate-700">No se encontraron facturas</h4>
                        <p class="text-slate-500">Prueba con otros términos o filtros de fecha.</p>
                    </div>
                `;
                lucide.createIcons();
            }
        } else {
            showToast(data.error || "Error en la búsqueda", "error");
            if (response.status === 401) logout(); // Desloguear si el token expiró
        }
    } catch (error) {
        showToast("Error de conexión con el servidor", "error");
    }
}

/**
 * Genera el HTML necesario para mostrar cada uno de los correos encontrados.
 */
function renderResults() {
    if (currentResults.length === 0) {
        selectionControls.classList.add('hidden'); // Ocultar controles de selección masiva
        resultsCountLabel.innerText = "0 encontrados";
        return;
    }

    selectionControls.classList.remove('hidden'); // Mostrar controles de selección masiva
    resultsCountLabel.innerText = `${currentResults.length} encontrados`;
    resultsList.innerHTML = '';

    currentResults.forEach(email => {
        const isSelected = selectedFiles.has(email.id); // Verificar si este correo está seleccionado
        const firstAtt = email.attachments[0] || { filename: 'Sin adjunto' };
        const isPdf = firstAtt.filename.toLowerCase().endsWith('.pdf');

        // Crear contenedor para el elemento de la lista
        const item = document.createElement('div');
        item.className = `group flex items-center p-4 border-b border-slate-50 hover:bg-slate-50 cursor-pointer ${isSelected ? 'bg-blue-50/50' : ''}`;

        // Manejar el click para seleccionar/deseleccionar el correo
        item.onclick = (e) => {
            if (e.target.type !== 'checkbox') toggleSelect(email.id);
        };

        // Estructura HTML del cada elemento factura
        item.innerHTML = `
            <div class="mr-4">
                <div class="w-6 h-6 border-2 rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-slate-300'}">
                    ${isSelected ? '<i data-lucide="check" class="w-4 h-4 text-white"></i>' : ''}
                </div>
            </div>
            <div class="p-2.5 rounded-xl mr-4 ${isPdf ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'}">
                <i data-lucide="${isPdf ? 'file-text' : 'code'}" class="w-6 h-6"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <h5 class="font-semibold text-slate-800 truncate">${email.subject}</h5>
                    ${email.downloaded ? '<span class="px-2 py-0.5 bg-green-100 text-green-700 text-[9px] font-bold rounded-full uppercase tracking-wider">Ya descargado</span>' : ''}
                </div>
                <div class="flex flex-wrap gap-2 text-xs text-slate-500 mt-0.5">
                    <span class="font-medium">${email.emisor_registrado || email.from}</span>
                    <span class="text-slate-300">|</span>
                    <span>${email.date}</span>
                </div>
                <div class="text-[10px] text-slate-400 mt-1 truncate flex items-center gap-2">
                    ${email.codigo_generacion ? `
                        <button onclick="event.stopPropagation(); navigator.clipboard.writeText('${email.codigo_generacion}'); showToast('Código copiado', 'success')" 
                            class="group/code inline-flex items-center gap-1.5 bg-slate-50 hover:bg-blue-50 text-slate-600 hover:text-blue-700 px-2 py-0.5 rounded-md font-mono text-[9px] border border-slate-200 hover:border-blue-200 transition-colors" title="Clic para copiar código">
                            <i data-lucide="hash" class="w-3 h-3 text-slate-400 group-hover/code:text-blue-500"></i>
                            <span class="truncate max-w-[150px]">${email.codigo_generacion}</span>
                            <i data-lucide="copy" class="w-3 h-3 opacity-0 group-hover/code:opacity-100 transition-opacity"></i>
                        </button>
                    ` : ''}

                    <span class="ml-1 opacity-75">${email.snippet}</span>
                </div>
            </div>
            <div class="hidden sm:block text-right text-[10px] text-slate-400 font-bold ml-4">
                ${email.attachments.length} adjunto(s)
            </div>
        `;
        resultsList.appendChild(item);
    });
    lucide.createIcons(); // Re-inicializar iconos para los nuevos elementos
    updateActionBar();   // Actualizar la barra inferior de descargar
}

// --- LÓGICA DE DESCARGA ---

/**
 * Agrupa los correos seleccionados y solicita al servidor la creación y descarga de un archivo ZIP.
 */
async function mockDownload() {
    // Filtrar la información completa de los correos seleccionados
    const selectedData = currentResults.filter(r => selectedFiles.has(r.id));
    if (selectedData.length === 0) return;

    showToast(`Preparando ZIP con ${selectedData.length} facturas...`, "info");

    try {
        const response = await fetch('/api/download-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ emails: selectedData })
        });

        if (response.ok) {
            // --- NUEVO: EXTRAER METADATOS DTE DEL HEADER ---
            // Se extrae el encabezado 'X-DTE-Metadata' que contiene información estructurada de los DTEs.
            const dteMetadataHeader = response.headers.get('X-DTE-Metadata');
            // Se parsea el JSON del encabezado; si no existe, se usa un array vacío.
            const dteMetadata = dteMetadataHeader ? JSON.parse(dteMetadataHeader) : [];

            // Recibir el archivo binario y forzar la descarga en el navegador
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'facturas_descargadas.zip';
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            // --- NOTA: EL HISTORIAL AHORA SE GUARDA AUTOMÁTICAMENTE EN EL BACKEND ---

            showToast("Descarga completada", "success");
            clearSelection(); // Limpiar la selección tras una descarga exitosa
        } else {
            showToast("Error al generar el ZIP", "error");
        }
    } catch (error) {
        showToast("Error de conexión", "error");
    }
}



// --- AYUDAS DE INTERFAZ DE USUARIO ---

/**
 * Añade o quita un ID del conjunto de seleccionados.
 */
function toggleSelect(id) {
    selectedFiles.has(id) ? selectedFiles.delete(id) : selectedFiles.add(id);
    renderResults();
}

/**
 * Selecciona todos los resultados actuales o vacía la selección si ya están todos.
 */
function toggleSelectAll() {
    if (selectedFiles.size === currentResults.length) {
        selectedFiles.clear();
    } else {
        currentResults.forEach(f => selectedFiles.add(f.id));
    }
    renderResults();
}

/**
 * Vacía el conjunto de archivos seleccionados.
 */
function clearSelection() {
    selectedFiles.clear();
    renderResults();
}

/**
 * Muestra u oculta la barra inferior de acciones dependiendo de si hay archivos seleccionados.
 */
function updateActionBar() {
    if (!actionBar || !selectedCountLabel) return;
    actionBar.classList.toggle('hidden', selectedFiles.size === 0);
    selectedCountLabel.innerText = selectedFiles.size;
}

/**
 * Muestra notificaciones temporales (toasts) en la pantalla.
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    // Configurar color y animación basándose en el tipo de mensaje
    toast.className = `flex items-center gap-3 ${type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-slate-800'} text-white px-6 py-3 rounded-2xl shadow-xl mb-3 animate-fade-in pointer-events-auto transition-all`;
    toast.innerHTML = `<i data-lucide="${type === 'success' ? 'check-circle' : 'info'}" class="w-5 h-5"></i><span class="text-sm font-medium">${message}</span>`;
    container.appendChild(toast);
    lucide.createIcons();
    // Eliminar el toast automáticamente después de 3 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Ejecutar la verificación inicial de sesión cuando el documento esté cargado
document.addEventListener('DOMContentLoaded', checkAuthStatus);

