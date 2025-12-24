# 🇸🇻 FactorDTE

Hacer la contabilidad en El Salvador puede ser un dolor de cabeza cuando todas las facturas llegan perdidas en el correo. Creé esta herramienta para automatizar el proceso de buscar, filtrar y descargar esos archivos DTE directamente desde Gmail sin tener que entrar uno por uno.

### ¿Qué hace exactamente?
- **Escaneo Inteligente:** Busca en tu Gmail correos que contengan facturas electrónicas.
- **Filtros por Fecha:** No descarga todo, solo lo que necesites para tu declaración o control mensual.
- **Descarga Consolidada:** Te genera un archivo ZIP con todos los documentos ordenados, listo para procesar.

---

## 🌐 Prueba la App en Vivo
Puedes ver el buscador funcionando aquí: **[FacturaFlow en Render](https://facturas-app-v2.onrender.com/)**

> ⏳ **Nota:** Como el servidor está en el plan gratuito de Render, la primera vez que entres puede tardar unos **50 segundos** en cargar mientras se "despierta". ¡Vale la pena la espera!

---

## 🛠️ Tecnologías Utilizadas
- **Backend:** Python con Flask para la lógica del servidor.
- **Integración:** API de Gmail para el escaneo de correos.
- **Frontend:** HTML y JavaScript limpio y funcional.
- **Despliegue:** Docker para un entorno estable y escalable.

---
*Hecho por [Eliezer Beltrán](https://github.com/EliezerBD). ¡Espero que te sirva tanto como a mí!*
