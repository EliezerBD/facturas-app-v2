class GmailDownloader {
    constructor() {
        this.correctPassword = "78945coe";
        this.isAuthenticated = false;
        this.currentState = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuthStatus();
        this.showNotification('Sistema listo - Conecta tu Gmail', 'info');
    }

    bindEvents() {
        document.getElementById('password-input')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.checkAccess();
        });
        
        document.getElementById('search-input')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchFiles();
        });
    }

    checkAuthStatus() {
        console.log('Verificando estado de autenticación...');
        
        if (window.location.hash === '#auth_success') {
            console.log('Autenticación detectada, mostrando app principal...');
            this.showMainApp();
            this.showNotification('✅ Conectado a Gmail correctamente', 'success');
            history.replaceState(null, null, ' ');
        }
    }

    async connectGmail() {
        try {
            this.showNotification('Conectando con Google...', 'info');
            
            const response = await fetch('/auth/google');
            const data = await response.json();
            
            if (data.authUrl && data.state) {
                this.currentState = data.state;
                localStorage.setItem('oauth_state', data.state);
                console.log('State guardado:', data.state);
                
                window.location.href = data.authUrl;
            } else {
                this.showNotification('Error al conectar con Google', 'error');
            }
        } catch (error) {
            this.showNotification('Error de conexión con el servidor', 'error');
            console.error('Error:', error);
        }
    }

    checkAccess() {
        const passwordInput = document.getElementById('password-input');
        const enteredPassword = passwordInput?.value.trim();

        if (enteredPassword === this.correctPassword) {
            this.showMainApp();
            this.showNotification('✅ Acceso concedido', 'success');
        } else {
            this.showNotification('❌ Contraseña incorrecta', 'error');
            if (passwordInput) passwordInput.value = '';
        }
    }

    showMainApp() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('main-screen').classList.remove('hidden');
        this.isAuthenticated = true;
        
        const savedState = localStorage.getItem('oauth_state');
        if (savedState) {
            this.currentState = savedState;
            console.log('State recuperado:', this.currentState);
        }
    }

    async searchFiles() {
        if (!this.isAuthenticated) {
            this.showNotification('Primero conecta tu Gmail', 'error');
            return;
        }

        const searchTerm = document.getElementById('search-input').value;
        const fileType = document.getElementById('file-type').value;

        try {
            this.showLoading();
            
            console.log('Enviando state:', this.currentState);
            
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    search: searchTerm,
                    fileType: fileType,
                    state: this.currentState
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayEmails(data.emails);
                const message = searchTerm ? 
                    `Encontrados ${data.total} resultados para "${searchTerm}"` :
                    `Mostrando ${data.total} emails`;
                this.showNotification(message, 'success');
            } else {
                this.showNotification(data.error || 'Error en la búsqueda', 'error');
            }
        } catch (error) {
            this.showNotification('Error de conexión', 'error');
            console.error('Error:', error);
        }
    }

    displayEmails(emails) {
        const resultsContainer = document.getElementById('results-list');
        const resultsCount = document.getElementById('results-count');
        
        resultsCount.textContent = emails.length;
        
        if (emails.length === 0) {
            resultsContainer.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <svg class="w-12 h-12 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p class="mt-2">No se encontraron emails</p>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = emails.map(email => `
            <div class="file-item border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50 transition-colors">
                <div class="flex items-center">
                    <input type="checkbox" class="file-checkbox w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500" 
                           data-email='${JSON.stringify(email)}'>
                    <div class="file-info ml-3 flex-1">
                        <div class="file-name font-semibold text-blue-600 flex items-center gap-2">
                            ${email.has_attachments ? 
                                (email.type === 'pdf' ? 
                                    '<svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z"/></svg>' : 
                                    '<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/></svg>'
                                ) :
                                '<svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>'
                            }
                            ${email.subject}
                        </div>
                        <div class="file-meta text-sm text-gray-600 mt-1">
                            <strong>De:</strong> ${email.from} | 
                            <strong>Fecha:</strong> ${email.date}
                        </div>
                        <div class="file-snippet text-xs text-gray-500 mt-1">
                            ${email.snippet}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const fileItem = e.target.closest('.file-item');
                if (e.target.checked) {
                    fileItem.classList.add('bg-blue-50', 'border-blue-300');
                } else {
                    fileItem.classList.remove('bg-blue-50', 'border-blue-300');
                }
            });
        });
    }

    async downloadSelected() {
        const selectedCheckboxes = document.querySelectorAll('.file-checkbox:checked');
        
        if (selectedCheckboxes.length === 0) {
            this.showNotification('Selecciona al menos un archivo', 'error');
            return;
        }

        const selectedEmails = Array.from(selectedCheckboxes).map(checkbox => 
            JSON.parse(checkbox.dataset.email)
        );

        if (selectedEmails.length === 1) {
            this.simulateDownload(selectedEmails[0]);
        } else {
            this.downloadAsZip(selectedEmails);
        }
    }

    async downloadAsZip(emails) {
        this.showNotification(`Preparando ZIP con ${emails.length} archivos...`, 'info');

        try {
            const response = await fetch('/api/download-batch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    emails: emails,
                    state: this.currentState
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'facturas_descargadas.zip';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                this.showNotification(`✅ ZIP descargado con ${emails.length} archivos`, 'success');
            }
        } catch (error) {
            this.showNotification('Error al descargar ZIP', 'error');
        }
    }

    simulateDownload(email) {
        const content = `Email: ${email.subject}\nDe: ${email.from}\nFecha: ${email.date}\n\n${email.snippet}`;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${email.subject}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    selectAll() {
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.file-item').classList.add('bg-blue-50', 'border-blue-300');
        });
        this.showNotification('Todos los emails seleccionados', 'info');
    }

    clearSelection() {
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.file-item').classList.remove('bg-blue-50', 'border-blue-300');
        });
        this.showNotification('Selección limpiada', 'info');
    }

    showLoading() {
        document.getElementById('results-list').innerHTML = `
            <div class="text-center py-8">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p class="mt-2 text-gray-600">Cargando emails...</p>
            </div>
        `;
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container');
        
        const notification = document.createElement('div');
        notification.className = `flex w-full max-w-sm overflow-hidden bg-white rounded-lg shadow-md ${
            type === 'success' ? 'border-l-4 border-green-500' :
            type === 'error' ? 'border-l-4 border-red-500' :
            'border-l-4 border-blue-500'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-center justify-center w-12 ${
                type === 'success' ? 'bg-green-500' :
                type === 'error' ? 'bg-red-500' :
                'bg-blue-500'
            }">
                <svg class="w-6 h-6 text-white fill-current" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                    ${
                        type === 'success' ? 
                        '<path d="M20 3.33331C10.8 3.33331 3.33337 10.8 3.33337 20C3.33337 29.2 10.8 36.6666 20 36.6666C29.2 36.6666 36.6667 29.2 36.6667 20C36.6667 10.8 29.2 3.33331 20 3.33331ZM16.6667 28.3333L8.33337 20L10.6834 17.65L16.6667 23.6166L29.3167 10.9666L31.6667 13.3333L16.6667 28.3333Z"/>' :
                        type === 'error' ?
                        '<path d="M20 3.36667C10.8167 3.36667 3.3667 10.8167 3.3667 20C3.3667 29.1833 10.8167 36.6333 20 36.6333C29.1834 36.6333 36.6334 29.1833 36.6334 20C36.6334 10.8167 29.1834 3.36667 20 3.36667ZM19.1334 33.3333V22.9H13.3334L21.6667 6.66667V17.1H27.25L19.1334 33.3333Z"/>' :
                        '<path d="M20 3.33331C10.8 3.33331 3.33337 10.8 3.33337 20C3.33337 29.2 10.8 36.6666 20 36.6666C29.2 36.6666 36.6667 29.2 36.6667 20C36.6667 10.8 29.2 3.33331 20 3.33331ZM21.6667 28.3333H18.3334V25H21.6667V28.3333ZM21.6667 21.6666H18.3334V11.6666H21.6667V21.6666Z"/>'
                    }
                </svg>
            </div>
            <div class="px-4 py-2 -mx-3">
                <div class="mx-3">
                    <span class="font-semibold ${
                        type === 'success' ? 'text-green-500' :
                        type === 'error' ? 'text-red-500' :
                        'text-blue-500'
                    }">
                        ${type === 'success' ? 'Éxito' : type === 'error' ? 'Error' : 'Información'}
                    </span>
                    <p class="text-sm text-gray-600">${message}</p>
                </div>
            </div>
        `;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Funciones globales
function connectGmail() { window.downloader.connectGmail(); }
function checkAccess() { window.downloader.checkAccess(); }
function searchFiles() { window.downloader.searchFiles(); }
function downloadSelected() { window.downloader.downloadSelected(); }
function selectAll() { window.downloader.selectAll(); }
function clearSelection() { window.downloader.clearSelection(); }

document.addEventListener('DOMContentLoaded', () => {
    window.downloader = new GmailDownloader();
});