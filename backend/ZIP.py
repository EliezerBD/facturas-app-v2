import zipfile
import io

@app.route('/api/download-batch', methods=['POST'])
def download_batch():
    """Descarga todos los archivos seleccionados en un ZIP"""
    try:
        data = request.json
        selected_emails = data.get('emails', [])
        
        # Crear ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for email in selected_emails:
                # Aquí descargarías el archivo real de Gmail
                # Por ahora simulamos con contenido de ejemplo
                content = f"Factura: {email['subject']}"
                zip_file.writestr(f"{email['subject']}.txt", content)
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='facturas_descargadas.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500