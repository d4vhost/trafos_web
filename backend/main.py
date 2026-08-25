from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import json
import shutil
from datetime import datetime

from database import get_db, init_db, engine, Base
from models import Incidencia, Analizador, GISEntry, Eventual, Bodega
from pdf_parser import process_single_pdf, process_all_pdfs

# --- Configuración ---
app = FastAPI(title="Sistema de Gestión de Incidencias EEASA")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

PDF_FOLDER = os.environ.get("PDF_FOLDER", "/data/pdfs")
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=PDF_FOLDER), name="pdfs")

@app.on_event("startup")
def on_startup():
    """Crear tablas al iniciar."""
    import models  # Asegurar que los modelos están importados
    Base.metadata.create_all(bind=engine)
    os.makedirs(PDF_FOLDER, exist_ok=True)
    print(f"✓ Base de datos inicializada")
    print(f"✓ Carpeta PDFs: {PDF_FOLDER}")


# ============================================================
# VISTAS HTML
# ============================================================

@app.get("/")
async def root(request: Request):
    """Redirigir a navegador."""
    return RedirectResponse(url="/navegador")


@app.get("/navegador", response_class=HTMLResponse)
async def vista_navegador(
    request: Request,
    page: int = 1,
    estado: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    alimentador: str = "",
    cuadrilla: str = "",
    buscar: str = "",
    db: Session = Depends(get_db)
):
    """Vista principal: tabla de todas las incidencias con filtros y paginación."""
    query = db.query(Incidencia)

    # Aplicar filtros
    if estado:
        query = query.filter(Incidencia.estado == estado)
    if alimentador:
        query = query.filter(Incidencia.alimentador_actual.contains(alimentador))
    if cuadrilla:
        query = query.filter(Incidencia.cuadrillas.contains(cuadrilla))
    if buscar:
        query = query.filter(
            Incidencia.incidencia.contains(buscar) |
            Incidencia.trabajo_adicional.contains(buscar) |
            Incidencia.alimentador_actual.contains(buscar)
        )
    if fecha_desde:
        query = query.filter(Incidencia.fecha_interrupcion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Incidencia.fecha_interrupcion <= fecha_hasta)

    # Paginación
    total_items = query.count()
    limit = 7
    total_pages = max(1, (total_items + limit - 1) // limit)
    offset = (page - 1) * limit
    
    incidencias = query.order_by(Incidencia.id.desc()).offset(offset).limit(limit).all()

    # Estadísticas
    total = db.query(Incidencia).count()
    completados = db.query(Incidencia).filter(Incidencia.estado == "Completado").count()
    en_proceso = db.query(Incidencia).filter(Incidencia.estado == "En proceso").count()
    no_iniciado = db.query(Incidencia).filter(Incidencia.estado == "No iniciado").count()

    # Listas para filtros
    alimentadores = [r[0] for r in db.query(Incidencia.alimentador_actual).distinct().all() if r[0]]
    cuadrillas_list = [r[0] for r in db.query(Incidencia.cuadrillas).distinct().all() if r[0]]

    stats = {
        "total": total,
        "completados": completados,
        "en_proceso": en_proceso,
        "no_iniciado": no_iniciado,
    }

    # Listar PDFs disponibles
    pdfs_disponibles = sorted([f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]) if os.path.exists(PDF_FOLDER) else []

    return templates.TemplateResponse(request=request, name="navegador.html", context={
        "request": request,
        "incidencias": incidencias,
        "current_page": page,
        "total_pages": total_pages,
        "pdfs_disponibles": pdfs_disponibles,
        "alimentadores": alimentadores,
        "cuadrillas_list": cuadrillas_list,
        "filtros": {
            "estado": estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "alimentador": alimentador,
            "cuadrilla": cuadrilla,
            "buscar": buscar,
        },
        "stats": stats
    })


@app.get("/detalle/{inc_id}", response_class=HTMLResponse)
async def vista_detalle(request: Request, inc_id: str, db: Session = Depends(get_db)):
    """Vista detalle de una incidencia con secciones desplegables."""
    incidencia = db.query(Incidencia).filter(Incidencia.incidencia == inc_id).first()
    if not incidencia:
        raise HTTPException(status_code=404, detail=f"Incidencia {inc_id} no encontrada")

    # Parsear JSON de comentarios y llamadas
    comentarios = []
    llamadas = []
    try:
        comentarios = json.loads(incidencia.comentarios_resolucion) if incidencia.comentarios_resolucion else []
    except:
        pass
    try:
        llamadas = json.loads(incidencia.llamadas_detalle) if incidencia.llamadas_detalle else []
    except:
        pass

    # Obtener analizadores y GIS relacionados
    analizadores = db.query(Analizador).filter(Analizador.inc == inc_id).all()
    gis_entries = db.query(GISEntry).filter(GISEntry.inc == inc_id).all()

    return templates.TemplateResponse(request=request, name="detalle.html", context={
        "inc": incidencia,
        "comentarios": comentarios,
        "llamadas": llamadas,
        "analizadores": analizadores,
        "gis_entries": gis_entries,
    })


@app.get("/analizadores", response_class=HTMLResponse)
async def vista_analizadores(request: Request, db: Session = Depends(get_db)):
    """Vista de analizadores."""
    analizadores = db.query(Analizador).all()
    return templates.TemplateResponse(request=request, name="analizadores.html", context={
        "analizadores": analizadores,
    })


@app.get("/gis", response_class=HTMLResponse)
async def vista_gis(request: Request, db: Session = Depends(get_db)):
    """Vista de entradas GIS."""
    entries = db.query(GISEntry).all()
    return templates.TemplateResponse(request=request, name="gis.html", context={
        "entries": entries,
    })


@app.get("/bodega", response_class=HTMLResponse)
async def vista_bodega(request: Request, db: Session = Depends(get_db)):
    """Vista de bodega."""
    items = db.query(Bodega).all()
    return templates.TemplateResponse(request=request, name="bodega.html", context={
        "items": items,
    })


# ============================================================
# API DE PROCESAMIENTO DE PDFs
# ============================================================

@app.post("/subir-pdf")
async def subir_pdf(archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Subir un PDF, guardarlo en la carpeta y procesarlo."""
    if not archivo.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    # Guardar PDF en la carpeta
    pdf_path = os.path.join(PDF_FOLDER, archivo.filename)
    with open(pdf_path, "wb") as f:
        content = await archivo.read()
        f.write(content)

    # Procesar
    try:
        result = process_single_pdf(pdf_path)
        saved = _save_result_to_db(result, db)
        return {"mensaje": f"✓ {archivo.filename} procesado correctamente", "incidencia": saved.get('incidencia_id', '')}
    except Exception as e:
        return {"mensaje": f"✗ Error procesando {archivo.filename}: {str(e)}", "error": True}


@app.post("/api/limpiar-datos")
async def limpiar_datos(db: Session = Depends(get_db)):
    """Borrar todos los registros de incidencias y PDFs para reiniciar."""
    try:
        total = db.query(Incidencia).count()
        db.query(Incidencia).delete()
        db.commit()
        # Limpiar PDFs del servidor
        if os.path.exists(PDF_FOLDER):
            for f in os.listdir(PDF_FOLDER):
                if f.lower().endswith('.pdf'):
                    os.remove(os.path.join(PDF_FOLDER, f))
        return {"mensaje": f"Se eliminaron {total} registros y sus PDFs.", "eliminados": total}
    except Exception as e:
        db.rollback()
        return {"mensaje": f"Error: {str(e)}", "eliminados": 0}

@app.post("/subir-pdf-unico")
async def subir_pdf_unico(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER, exist_ok=True)
        
    if not file.filename.lower().endswith('.pdf'):
        return {"estado": "error", "detalle": "Archivo no es PDF"}
        
    file_path = os.path.join(PDF_FOLDER, file.filename)
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Procesar
    inc_num = _extract_inc_from_filename(file.filename)
    if inc_num and db.query(Incidencia).filter(Incidencia.incidencia == inc_num).first():
        return {"estado": "duplicado"}
        
    try:
        result = process_single_pdf(file_path)
        _save_result_to_db(result, db)
        return {"estado": "procesado"}
    except Exception as e:
        return {"estado": "error", "detalle": str(e)}

@app.post("/subir-pdfs")
async def subir_pdfs(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
        
    resultados = {"procesados": 0, "errores": 0, "duplicados": 0, "detalles": []}
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue
            
        file_path = os.path.join(PDF_FOLDER, file.filename)
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Procesar
        inc_num = _extract_inc_from_filename(file.filename)
        if inc_num and db.query(Incidencia).filter(Incidencia.incidencia == inc_num).first():
            resultados["duplicados"] += 1
            resultados["detalles"].append({"archivo": file.filename, "estado": "duplicado"})
            continue
            
        try:
            result = process_single_pdf(file_path)
            _save_result_to_db(result, db)
            resultados["procesados"] += 1
            resultados["detalles"].append({"archivo": file.filename, "estado": "procesado"})
        except Exception as e:
            resultados["errores"] += 1
            resultados["detalles"].append({"archivo": file.filename, "estado": "error", "detalle": str(e)})

    return resultados

@app.post("/procesar-carpeta")
async def procesar_carpeta(db: Session = Depends(get_db)):
    """Procesar todos los PDFs de la carpeta pdfs_incidencias."""
    if not os.path.exists(PDF_FOLDER):
        raise HTTPException(status_code=404, detail="Carpeta de PDFs no encontrada")

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return {"mensaje": "No hay PDFs para procesar", "procesados": 0}

    resultados = {"procesados": 0, "errores": 0, "duplicados": 0, "detalles": []}

    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(PDF_FOLDER, pdf_file)

        # Verificar si ya fue procesado
        inc_num = _extract_inc_from_filename(pdf_file)
        if inc_num and db.query(Incidencia).filter(Incidencia.incidencia == inc_num).first():
            resultados["duplicados"] += 1
            resultados["detalles"].append({"archivo": pdf_file, "estado": "duplicado"})
            continue

        try:
            result = process_single_pdf(pdf_path)
            _save_result_to_db(result, db)
            resultados["procesados"] += 1
            resultados["detalles"].append({"archivo": pdf_file, "estado": "procesado"})
        except Exception as e:
            resultados["errores"] += 1
            resultados["detalles"].append({"archivo": pdf_file, "estado": "error", "detalle": str(e)})

    return {
        "mensaje": f"Procesamiento completado: {resultados['procesados']} procesados, {resultados['duplicados']} duplicados, {resultados['errores']} errores",
        **resultados
    }


# ============================================================
# API DE GESTIÓN (actualizar campos manuales)
# ============================================================

@app.put("/api/incidencia/{inc_id}/estado")
async def actualizar_estado(inc_id: str, request: Request, db: Session = Depends(get_db)):
    """Actualizar el estado de una incidencia."""
    body = await request.json()
    inc = db.query(Incidencia).filter(Incidencia.incidencia == inc_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    inc.estado = body.get("estado", inc.estado)
    db.commit()
    return {"mensaje": "Estado actualizado", "estado": inc.estado}


@app.put("/api/incidencia/{inc_id}/campos")
async def actualizar_campos(inc_id: str, request: Request, db: Session = Depends(get_db)):
    """Actualizar campos editables de una incidencia."""
    body = await request.json()
    inc = db.query(Incidencia).filter(Incidencia.incidencia == inc_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    # Campos que se pueden editar manualmente
    campos_editables = [
        'estado', 'observaciones', 'grupo', 'wr', 'orden_bodega',
        'fecha_planificado', 'hora_planificado', 'prioridad'
    ]
    for campo in campos_editables:
        if campo in body:
            setattr(inc, campo, body[campo])

    db.commit()
    return {"mensaje": "Campos actualizados"}


@app.get("/api/incidencias")
async def api_incidencias(db: Session = Depends(get_db)):
    """API JSON de todas las incidencias."""
    incidencias = db.query(Incidencia).order_by(Incidencia.id.desc()).all()
    return [{
        "id": i.id,
        "incidencia": i.incidencia,
        "estado": i.estado,
        "prioridad": i.prioridad,
        "alimentador_actual": i.alimentador_actual,
        "fecha_interrupcion": i.fecha_interrupcion,
        "trabajo_adicional": i.trabajo_adicional,
        "cuadrillas": i.cuadrillas,
        "afectados": i.afectados,
        "tipo_cuadrilla": i.tipo_cuadrilla,
    } for i in incidencias]


@app.get("/api/pdfs")
async def api_listar_pdfs():
    """Listar PDFs disponibles en la carpeta."""
    if not os.path.exists(PDF_FOLDER):
        return []
    return sorted([f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')])


@app.get("/pdf/{filename}")
async def descargar_pdf(filename: str):
    """Servir un PDF para visualización."""
    pdf_path = os.path.join(PDF_FOLDER, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(pdf_path, media_type="application/pdf")


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _extract_inc_from_filename(filename: str) -> str:
    """Extraer número de INC del nombre del archivo."""
    import re
    match = re.search(r'INC\s*(\d+)', filename, re.IGNORECASE)
    return match.group(1) if match else ''


def _save_result_to_db(result: dict, db: Session) -> dict:
    """Guardar resultado del procesamiento en la base de datos."""
    saved = {}

    # Guardar incidencia
    inc_data = result.get('incidencia', {})
    if inc_data and inc_data.get('incidencia'):
        # Verificar si ya existe
        existing = db.query(Incidencia).filter(Incidencia.incidencia == inc_data['incidencia']).first()
        if not existing:
            # Filtrar solo campos del modelo
            model_fields = {c.name for c in Incidencia.__table__.columns if c.name != 'id'}
            filtered = {k: v for k, v in inc_data.items() if k in model_fields}
            inc = Incidencia(**filtered)
            db.add(inc)
            db.flush()
            saved['incidencia_id'] = inc_data['incidencia']
        else:
            saved['incidencia_id'] = existing.incidencia

    # Guardar analizador si se detectó
    analizador_data = result.get('analizador')
    if analizador_data:
        existing_a = db.query(Analizador).filter(Analizador.inc == analizador_data.get('inc', '')).first()
        if not existing_a:
            analizador = Analizador(**analizador_data)
            db.add(analizador)

    # Guardar GIS si se detectó
    gis_data = result.get('gis')
    if gis_data:
        existing_g = db.query(GISEntry).filter(GISEntry.inc == gis_data.get('inc', '')).first()
        if not existing_g:
            gis = GISEntry(**gis_data)
            db.add(gis)

    db.commit()
    return saved