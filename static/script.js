lucide.createIcons();

let selectedFiles = new Set();
let currentResults = [];

// Elements
const loginScreen = document.getElementById('login-screen');
const mainScreen = document.getElementById('main-screen');
const heroSection = document.getElementById('hero-section');
const userBadge = document.getElementById('user-badge');
const resultsList = document.getElementById('results-list');
const resultsCountLabel = document.getElementById('results-count');
const actionBar = document.getElementById('action-bar');
const selectedCountLabel = document.getElementById('selected-count');
const selectionControls = document.getElementById('selection-controls');
const userEmailLabel = document.getElementById('user-email');

// --- AUTH LOGIC ---

function parseHashParams() {
    const hash = window.location.hash.substring(1);
    return {
        authSuccess: hash.startsWith('auth_success')
    };
}

async function checkAuthStatus() {
    const { authSuccess } = parseHashParams();

    if (authSuccess) {
        // Si el hash indica éxito, pedimos los datos al backend
        try {
            const response = await fetch('/auth/check-session');
            if (response.ok) {
                const data = await response.json();
                showMainApp(data.email);
            } else {
                showMainApp();
            }
        } catch (e) {
            showMainApp();
        }

        history.replaceState(null, null, ' ');
        showToast("Conectado a Gmail correctamente", "success");
    } else {
        try {
            const response = await fetch('/auth/check-session');
            if (response.ok) {
                const data = await response.json();
                showMainApp(data.email);
            }
        } catch (error) {
            console.error('Error verificando sesión:', error);
        }
    }
}

function showMainApp(email) {
    if (!loginScreen || !heroSection || !mainScreen || !userBadge) return;
    loginScreen.classList.add('hidden');
    heroSection.classList.add('hidden');
    mainScreen.classList.remove('hidden');
    userBadge.classList.remove('hidden');
    if (email) {
        userEmailLabel.innerText = email;
    }
}

async function mockLogin() { // Reusing the function name called from HTML
    try {
        showToast("Conectando con Google...", "info");
        const response = await fetch('/auth/google');
        const data = await response.json();

        if (data.authUrl) {
            window.location.href = data.authUrl;
        } else {
            showToast("Error al conectar con Google", "error");
        }
    } catch (error) {
        showToast("Error de conexión", "error");
    }
}

async function logout() {
    await fetch('/auth/logout', { method: 'POST' });
    location.reload();
}

// --- SEARCH LOGIC ---

async function simulateSearch() { // Reusing the name for consistency with HTML
    const searchTerm = document.getElementById('search-input').value;
    const fileType = document.getElementById('file-type').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

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
            currentResults = data.emails;
            renderResults();
            if (currentResults.length === 0) {
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
            if (response.status === 401) logout();
        }
    } catch (error) {
        showToast("Error de conexión con el servidor", "error");
    }
}

function renderResults() {
    if (currentResults.length === 0) {
        selectionControls.classList.add('hidden');
        resultsCountLabel.innerText = "0 encontrados";
        return;
    }

    selectionControls.classList.remove('hidden');
    resultsCountLabel.innerText = `${currentResults.length} encontrados`;
    resultsList.innerHTML = '';

    currentResults.forEach(email => {
        const isSelected = selectedFiles.has(email.id);
        const firstAtt = email.attachments[0] || { filename: 'Sin adjunto' };
        const isPdf = firstAtt.filename.toLowerCase().endsWith('.pdf');

        const item = document.createElement('div');
        item.className = `group flex items-center p-4 border-b border-slate-50 hover:bg-slate-50 cursor-pointer ${isSelected ? 'bg-blue-50/50' : ''}`;
        item.onclick = (e) => {
            // Evitar que el click en el checkbox dispare doble
            if (e.target.type !== 'checkbox') toggleSelect(email.id);
        };

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
                <h5 class="font-semibold text-slate-800 truncate">${email.subject}</h5>
                <div class="flex flex-wrap gap-2 text-xs text-slate-500 mt-0.5">
                    <span class="font-medium">${email.from}</span>
                    <span class="text-slate-300">|</span>
                    <span>${email.date}</span>
                </div>
                <div class="text-[10px] text-slate-400 mt-1 truncate">${email.snippet}</div>
            </div>
            <div class="hidden sm:block text-right text-[10px] text-slate-400 font-bold ml-4">
                ${email.attachments.length} adjunto(s)
            </div>
        `;
        resultsList.appendChild(item);
    });
    lucide.createIcons();
    updateActionBar();
}

// --- DOWNLOAD LOGIC ---

async function mockDownload() { // Reusing name from HTML
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
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'facturas_descargadas.zip';
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            showToast("Descarga completada", "success");
            clearSelection();
        } else {
            showToast("Error al generar el ZIP", "error");
        }
    } catch (error) {
        showToast("Error de conexión", "error");
    }
}



// --- UI HELPERS ---

function toggleSelect(id) {
    selectedFiles.has(id) ? selectedFiles.delete(id) : selectedFiles.add(id);
    renderResults();
}

function toggleSelectAll() {
    if (selectedFiles.size === currentResults.length) {
        selectedFiles.clear();
    } else {
        currentResults.forEach(f => selectedFiles.add(f.id));
    }
    renderResults();
}

function clearSelection() {
    selectedFiles.clear();
    renderResults();
}

function updateActionBar() {
    if (!actionBar || !selectedCountLabel) return;
    actionBar.classList.toggle('hidden', selectedFiles.size === 0);
    selectedCountLabel.innerText = selectedFiles.size;
}



function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 ${type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-slate-800'} text-white px-6 py-3 rounded-2xl shadow-xl mb-3 animate-fade-in pointer-events-auto transition-all`;
    toast.innerHTML = `<i data-lucide="${type === 'success' ? 'check-circle' : 'info'}" class="w-5 h-5"></i><span class="text-sm font-medium">${message}</span>`;
    container.appendChild(toast);
    lucide.createIcons();
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// Initial check
document.addEventListener('DOMContentLoaded', checkAuthStatus);
