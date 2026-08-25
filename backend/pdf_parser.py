import pytesseract
from PIL import Image
import pdfplumber
import re
import json
import os
from datetime import datetime

MAX_PAGES = 3  # Only process first 3 pages (all relevant data is there)
OCR_DPI = 150  # 150 DPI is sufficient for text extraction (vs 300 = 4x faster)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from image-based PDF using OCR.
    Optimized: lower DPI, grayscale, limited pages, fast Tesseract engine."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_process = pdf.pages[:MAX_PAGES]
        for page in pages_to_process:
            img = page.to_image(resolution=OCR_DPI).original
            # Convert to grayscale for faster OCR
            img = img.convert('L')
            # PSM 6 = uniform block | OEM 1 = LSTM only (fastest neural engine)
            text = pytesseract.image_to_string(img, config='--psm 6 --oem 1', lang='spa')
            full_text += text + "\n\n--- PAGE BREAK ---\n\n"
    return full_text

def parse_incidencia_data(text: str, pdf_filename: str) -> dict:
    """Parse the OCR text and extract all fields into a dictionary."""
    data = {}
    
    # Basic fields with regex — using robust positive lookaheads to stop at the next known label
    patterns = {
        'incidencia': r'(?:ID\s+Incidencia|Incidencia)[:\s]+INC\s*(\d+)',
        'alimentador_actual': r'Alimentador\s+actual[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Alimentador|\s+Problemas|$)',
        'alimentador_normal': r'Alimentador\s+normal[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Subtipo|\s+Problemas|$)',
        'tipo_incidencia': r'Tipo[:\s]+(No Programadas[^\n]*?)(?=\s{2,}|\s+Alimentador|$)',
        'subtipo': r'Subtipo[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Problemas|\s+Prioridad|$)',
        'prioridad': r'Prioridad[:\s]+(\d+)',
        'fecha_interrupcion': r'(?:Fecha|Tiempo)\s+de\s+interrupci[oó]n[:\s]+([\d/]+\s+[\d:]+)',
        'estado_adms': r'Estado[:\s]+(En\s+curso|Archivado|Trabajo\s+Adicional|Cerrado)',
        'etr': r'ETR[:\s]+([\d/]+\s+[\d:]+)',
        'estado_energia': r'Estado\s+de\s+energ[ií]a[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+ATR|$)',
        'atr': r'ATR[:\s]+([\d/]+\s+[\d:]+)',
        'llamadas_count': r'Llamadas[:\s]+(\d+)',
        'afectados': r'(?:Clientes\s+afectados|Afectados)[:\s]+([\doO]+)(?!\s*\[kW\])',
        'creado_en': r'Creado\s+en[:\s]+([\d/]+\s+[\d:]+)',
        'creado_por': r'Creado\s+por[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Dispositivos|\s+[Cd]ientes\s+de\s+restauraci[oó]n|$)',
        'instruccion': r'Instrucci[oó]n[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Llamadas|\s+ATR|$)',
        'causa': r'Causa[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Tipo\s+de|$)',
        'subcausa': r'Subcausa[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Componente|$)',
        'componente_fallo': r'Componente\s+con\s+fallo[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Material|$)',
        'tipo_construccion': r'Tipo\s+de\s+construcci[oó]n[:\s]+(\S+(?:\s+\S+)*?)(?=\s{2,}|\s+Componente|$)',
        'cmi': r'CMI[:\s]+(\d+)',
        'potencia_afectados_kw': r'(?:Potencia\s+Afectados|Afectados)[:\s]+([\d.,]+)\s+\[kW\]',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        data[key] = match.group(1).strip() if match else ''
        
    if data.get('afectados'):
        data['afectados'] = data['afectados'].lower().replace('o', '0')
    
    # Extract cuadrilla ID
    cuadrilla_match = re.search(r'(?:ID\s+cuadrilla|cuadrilla)[:\s]+([A-Z0-9][A-Z0-9\-]+)', text, re.IGNORECASE)
    data['cuadrillas'] = cuadrilla_match.group(1).strip() if cuadrilla_match else ''
    
    # Extract device info
    dispositivo_match = re.search(r'Nombre\s+Fases.*?\n([^\n]+)', text)
    if dispositivo_match:
        data['dispositivo_nombre'] = dispositivo_match.group(1).split()[0] if dispositivo_match else ''
    else:
        data['dispositivo_nombre'] = ''
    
    # Extract transformer number from comments (look for patterns like 'transformador 20375', 'trafo trifasico #5321')
    trafo_match = re.search(r'(?:transformador|trafo|TRF)[^\d#]{0,25}?(?:#|Nro\.?|No\.?)?\s*(\d{3,6})', text, re.IGNORECASE)
    data['num_transf'] = trafo_match.group(1) if trafo_match else ''
    
    # Extract potencia from comments (look for patterns like '5KVA', '15 kVA', '37.5KVA')
    potencia_match = re.search(r'(\d+(?:[.,]\d+)?)\s*[kK][vV][aA]', text)
    data['potencia_transf'] = potencia_match.group(1) if potencia_match else ''
    
    # Extract coordinates from comments (e.g. Lat: -1.398, Lon: -78.522)
    coord_match = re.search(r'[Ll]at(?:itud)?[:\s]+(-?\d+[,.]+\d+)[\s\S]{1,60}?[Ll]on(?:gitud)?[:\s]+(-?\d+[,.]+\d+)', text)
    if coord_match:
        lat = coord_match.group(1).replace(',', '')
        lon = coord_match.group(2).replace(',', '')
        data['coordenadas'] = f"{lat}, {lon}"
    else:
        data['coordenadas'] = ''
    
    # Extract ID Medidor (often appears after a date/time in the Llamadas table)
    medidor_match = re.search(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(\d{5,10}(?:_\d+)?)', text)
    data['id_medidor'] = medidor_match.group(1) if medidor_match else ''
    
    # Extract trabajo adicional text from comments
    ta_matches = re.findall(r'[Tt]rabajo[s]?\s+[Aa]dicional[es]?[:\s]+([^\n]+(?:\n[^\n]+)?)', text)
    data['trabajo_adicional'] = ' '.join(m.strip() for m in ta_matches) if ta_matches else ''
    
    # If no explicit trabajo adicional but filename contains it
    if not data['trabajo_adicional']:
        # Try broader search in comments for work description after RTEL
        rtel_match = re.search(r'1\.RTEL[^\n]*se\s+requiere\s+([^\n]+)', text, re.IGNORECASE)
        if rtel_match:
            data['trabajo_adicional'] = rtel_match.group(1).strip()
    
    # Extract resolution comments as JSON
    comment_pattern = r'(\d{2}/\d{2}/\d{4}\s+\d+:\d+:\d+)\s+([^\s]+)\s+(Operador|Cuadrilla\s+de\s+campo)\s+(.+?)(?=\d{2}/\d{2}/\d{4}|$)'
    comments = []
    for match in re.finditer(comment_pattern, text, re.DOTALL):
        comments.append({
            'tiempo': match.group(1).strip(),
            'usuario': match.group(2).strip(),
            'tipo': match.group(3).strip(),
            'comentario': match.group(4).strip()
        })
    data['comentarios_resolucion'] = json.dumps(comments, ensure_ascii=False) if comments else '[]'
    
    # Extract call details
    call_pattern = r'CALL\s+(\d+)\s+(.+?)\s+(\w+)\s+(\w+)'
    calls = []
    for match in re.finditer(call_pattern, text):
        calls.append({
            'id': f'CALL {match.group(1)}',
            'motivo': match.group(2).strip()
        })
    data['llamadas_detalle'] = json.dumps(calls, ensure_ascii=False) if calls else '[]'
    
    # Determine if es_trabajo_adicional
    data['es_trabajo_adicional'] = bool(
        'TRABAJO ADICIONAL' in pdf_filename.upper() or
        re.search(r'trabajo\s+adicional', text, re.IGNORECASE)
    )
    
    # Determine tipo_cuadrilla
    data['tipo_cuadrilla'] = 'Trabajo Adicional' if data['es_trabajo_adicional'] else 'Especializada'
    
    # Map prioridad to display format
    prio_map = {'1': '1 - Muy Alta', '2': '2 - Alta', '3': '3 - Media', '4': '4 - Baja', '5': '5 - Muy Baja'}
    if data.get('prioridad') in prio_map:
        data['prioridad'] = prio_map[data['prioridad']]
    
    # Determine tipo (Monofásico/Trifásico) from device info
    if re.search(r'trif[aá]sico', text, re.IGNORECASE):
        data['tipo'] = 'Trifásico'
    else:
        data['tipo'] = 'Monofásico'
    
    # Set metadata
    data['pdf_filename'] = pdf_filename
    data['fecha_procesado'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['estado'] = 'No iniciado'  # Default status
    data['observaciones'] = ''
    data['grupo'] = ''
    data['wr'] = ''
    data['orden_bodega'] = ''
    data['fecha_planificado'] = ''
    data['hora_planificado'] = ''
    data['dispositivo_tipo'] = ''
    data['loc_red'] = ''
    
    # Try to extract loc_red
    loc_match = re.search(r'Loc\s+red[:\s]+([^\n]+)', text, re.IGNORECASE)
    data['loc_red'] = loc_match.group(1).strip() if loc_match else ''
    
    return data

def extract_analizador_data(data: dict) -> dict | None:
    """If the incident mentions an analyzer/registrador, create Analizador entry."""
    text = data.get('trabajo_adicional', '') + ' ' + data.get('comentarios_resolucion', '')
    if re.search(r'(analizador|registrador\s+de\s+carga)', text, re.IGNORECASE):
        return {
            'analizado': 'No',
            'fecha_instalacion': '',
            'fecha_retiro': '',
            'inc': data.get('incidencia', ''),
            'trafo': data.get('num_transf', ''),
            'potencia': data.get('potencia_transf', ''),
            'tipo': data.get('tipo', ''),
            'alimentador': data.get('alimentador_actual', ''),
            'resp_instalacion': '',
            'resp_retiro': '',
            'observacion': f"Detectado desde PDF: {data.get('trabajo_adicional', '')}"
        }
    return None

def extract_gis_data(data: dict) -> dict | None:
    """If the incident mentions a transformer change, create GIS entry."""
    comments_text = data.get('comentarios_resolucion', '')
    
    # Look for transformer replacement patterns
    cambio_match = re.search(
        r'(?:cambio|remplazo|reemplazo).*?(?:transformador|trafo|TRF)\s+#?(\d+).*?(?:queda|por).*?(?:TRF|trafo|transformador)?\s*#?(\d+)',
        comments_text, re.IGNORECASE
    )
    if cambio_match:
        return {
            'estado': '',
            'tarea': f"Cambio de transformador {cambio_match.group(1)} - detectado desde PDF",
            'tipo': 'Remplazo',
            'antiguo_trafo': cambio_match.group(1),
            'antiguo_potencia': data.get('potencia_transf', ''),
            'nuevo_trafo': cambio_match.group(2),
            'nuevo_potencia': '',
            'poste_nuevo': '',
            'fecha_realizacion': '',
            'inc': data.get('incidencia', ''),
            'documento': '',
            'observacion': f"Detectado automáticamente desde PDF"
        }
    
    # Also check for 'quemado' pattern
    if re.search(r'(?:transformador|trafo).*?quemado', comments_text, re.IGNORECASE):
        return {
            'estado': '',
            'tarea': f"Transformador {data.get('num_transf', '')} quemado - requiere cambio",
            'tipo': 'Remplazo',
            'antiguo_trafo': data.get('num_transf', ''),
            'antiguo_potencia': data.get('potencia_transf', ''),
            'nuevo_trafo': '',
            'nuevo_potencia': '',
            'poste_nuevo': '',
            'fecha_realizacion': '',
            'inc': data.get('incidencia', ''),
            'documento': '',
            'observacion': f"Detectado automáticamente desde PDF"
        }
    return None

def process_single_pdf(pdf_path: str) -> dict:
    """Process a single PDF and return all extracted data."""
    filename = os.path.basename(pdf_path)
    text = extract_text_from_pdf(pdf_path)
    data = parse_incidencia_data(text, filename)
    
    result = {
        'incidencia': data,
        'analizador': extract_analizador_data(data),
        'gis': extract_gis_data(data),
    }
    return result

def process_all_pdfs(pdf_folder: str) -> list:
    """Process all PDFs in a folder."""
    results = []
    pdf_files = sorted([
        f for f in os.listdir(pdf_folder) 
        if f.lower().endswith('.pdf')
    ])
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        try:
            result = process_single_pdf(pdf_path)
            results.append(result)
            print(f"✓ Procesado: {pdf_file}")
        except Exception as e:
            print(f"✗ Error procesando {pdf_file}: {e}")
            results.append({'error': str(e), 'filename': pdf_file})
    
    return results
