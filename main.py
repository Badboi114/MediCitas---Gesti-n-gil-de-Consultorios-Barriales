from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import database, models

# --- CONFIGURACIÓN INICIAL ---
# Creamos las tablas en la BD automáticamente al iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Sistema Integral MediCitas")
templates = Jinja2Templates(directory="templates")

# Dependencia para obtener la sesión de BD en cada petición
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. LANDING PAGE (La Entrada) ---
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Página de entrada con dos opciones: AdminMediCitas y MediCitas"""
    return templates.TemplateResponse("landing.html", {"request": request})

# --- 2. MEDICITAS (Lado Público/Recepción) ---
@app.get("/medicitas", response_class=HTMLResponse)
async def public_calendar(request: Request, db: Session = Depends(get_db)):
    """Calendario interactivo para recepción de pacientes"""
    # Obtener configuración
    config = db.query(models.Configuracion).first()
    if not config:
        config = models.Configuracion()  # Defaults
        db.add(config)
        db.commit()
        db.refresh(config)
    
    doctores = db.query(models.Doctor).all()
    
    # Si no hay doctores, creamos algunos de prueba
    if not doctores:
        doctores_prueba = [
            models.Doctor(nombre="Dr. Juan Pérez", especialidad="Medicina General", duracion_cita=30),
            models.Doctor(nombre="Dra. María López", especialidad="Cardiología", duracion_cita=45),
            models.Doctor(nombre="Dr. Carlos Rodríguez", especialidad="Pediatría", duracion_cita=30),
        ]
        for doc in doctores_prueba:
            db.add(doc)
        db.commit()
        doctores = db.query(models.Doctor).all()
        
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "doctores": doctores,
        "config": config  # Pasamos la configuración al calendario
    })

# --- 3. ADMIN MEDICITAS (Back Office) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Panel de Control Administrativo con Vista Tabular"""
    # Vista Tabular de Auditoría
    citas = db.query(models.Cita).order_by(models.Cita.fecha_inicio.desc()).all()
    config = db.query(models.Configuracion).first()
    if not config:
        config = models.Configuracion()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Resumen rápido
    total_citas = len(citas)
    total_doctores = db.query(models.Doctor).count()
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "citas": citas, 
        "config": config,
        "stats": {"total": total_citas, "docs": total_doctores}
    })

# API: Actualizar Configuración
@app.post("/admin/config")
async def update_config(
    hora_apertura: str = Form(...),
    hora_cierre: str = Form(...),
    db: Session = Depends(get_db)
):
    """Actualizar configuración global del consultorio"""
    config = db.query(models.Configuracion).first()
    if not config:
        config = models.Configuracion()
        db.add(config)
    
    config.hora_apertura = hora_apertura
    config.hora_cierre = hora_cierre
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# --- APIS EXISTENTES (Sin cambios mayores) ---

@app.get("/api/citas/{doctor_id}")
async def obtener_citas(doctor_id: int, db: Session = Depends(get_db)):
    """API que devuelve las citas para pintar el calendario"""
    try:
        citas = db.query(models.Cita).filter(
            models.Cita.doctor_id == doctor_id, 
            models.Cita.activo == True
        ).all()
        
        eventos = []
        for cita in citas:
            try:
                # Protección: Verificar que el paciente existe
                ci_paciente = ""
                nombre_paciente = "Sin Datos"
                
                if cita.paciente:
                    ci_paciente = str(cita.paciente.ci) if cita.paciente.ci else ""
                    nombre_paciente = str(cita.paciente.nombre) if cita.paciente.nombre else "Sin Nombre"
                
                eventos.append({
                    "id": str(cita.id),
                    "title": "Ocupado",
                    "start": cita.fecha_inicio.isoformat(),
                    "end": cita.fecha_fin.isoformat(),
                    "color": "#ef4444",
                    "extendedProps": {
                        "cita_id": cita.id,
                        "ci": ci_paciente,
                        "nombre": nombre_paciente,
                        "motivo": str(cita.motivo) if cita.motivo else ""
                    }
                })
            except Exception as e:
                print(f"Error procesando cita {cita.id}: {e}")
                continue
        
        print(f"✓ Devolviendo {len(eventos)} citas para doctor {doctor_id}")
        return eventos
    except Exception as e:
        print(f"✗ Error en obtener_citas: {e}")
        return []

@app.get("/api/buscar-paciente")
async def buscar_paciente(q: str, db: Session = Depends(get_db)):
    """API para búsqueda predictiva de pacientes por CI"""
    pacientes = db.query(models.Paciente).filter(
        models.Paciente.ci.like(f"{q}%")
    ).limit(5).all()
    
    resultados = []
    for p in pacientes:
        resultados.append({
            "id": p.id,
            "ci": p.ci,
            "nombre": p.nombre,
            "telefono": p.telefono
        })
    return resultados

@app.post("/agendar")
async def agendar_cita(
    cita_id: Optional[int] = Form(None),  # <--- Nuevo campo opcional para edición
    doctor_id: int = Form(...),
    fecha_inicio_str: str = Form(...),
    fecha_fin_str: str = Form(...),
    paciente_ci: str = Form(...),
    paciente_nombre: str = Form(...),
    paciente_telefono: str = Form(default=""),
    motivo: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agendar cita con hora de fin manual (soporta creación y edición)"""
    
    # 1. Convertir fechas
    try:
        fecha_inicio = datetime.fromisoformat(fecha_inicio_str.replace('Z', '+00:00'))
        fecha_fin = datetime.fromisoformat(fecha_fin_str.replace('Z', '+00:00'))
    except ValueError:
        return JSONResponse(content={"status": "error", "msg": "Formato de fecha inválido"}, status_code=400)

    # 2. VALIDACIÓN: ¿Hay choque de horario? (Excluyendo la cita actual si es edición)
    query_choque = db.query(models.Cita).filter(
        models.Cita.doctor_id == doctor_id,
        models.Cita.activo == True,
        models.Cita.fecha_inicio < fecha_fin,
        models.Cita.fecha_fin > fecha_inicio
    )
    if cita_id:
        query_choque = query_choque.filter(models.Cita.id != cita_id)  # Ignorarse a sí misma

    if query_choque.first():
        return JSONResponse(content={"status": "error", "msg": "⛔ HORARIO OCUPADO"}, status_code=400)

    # 3. Gestionar Paciente (Buscar o Crear)
    paciente = db.query(models.Paciente).filter(models.Paciente.ci == paciente_ci).first()
    if not paciente:
        # No existe: Crear nuevo paciente
        paciente = models.Paciente(ci=paciente_ci, nombre=paciente_nombre, telefono=paciente_telefono)
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    else:
        # Ya existe: Actualizar nombre por si lo corrigieron
        paciente.nombre = paciente_nombre
        paciente.telefono = paciente_telefono
        db.commit()

    if cita_id:
        # --- MODO EDICIÓN ---
        cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
        if not cita:
            return JSONResponse(content={"status": "error", "msg": "Cita no encontrada"}, status_code=404)
        cita.fecha_inicio = fecha_inicio
        cita.fecha_fin = fecha_fin
        cita.motivo = motivo
        cita.paciente_id = paciente.id  # CLAVE: Vincular correctamente al paciente
        mensaje = "✅ Cita actualizada correctamente"
    else:
        # --- MODO CREACIÓN ---
        nueva_cita = models.Cita(
            doctor_id=doctor_id,
            paciente_id=paciente.id,  # CLAVE: Vincular correctamente al paciente
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            motivo=motivo
        )
        db.add(nueva_cita)
        mensaje = "✅ Cita agendada con éxito"

    db.commit()
    return JSONResponse(content={"status": "ok", "msg": mensaje})

# Nueva API para Borrar - VERSIÓN SIMPLIFICADA
@app.post("/borrar")
async def borrar_cita(request: Request, db: Session = Depends(get_db)):
    """Eliminar una cita permanentemente"""
    print(f"==> [BORRAR] Request recibido")
    
    try:
        # Intentar leer como FormData
        form_data = await request.form()
        print(f"==> [BORRAR] Form keys: {list(form_data.keys())}")
        
        cita_id = form_data.get('cita_id')
        print(f"==> [BORRAR] cita_id extraído: {cita_id} (tipo: {type(cita_id)})")
        
        if cita_id:
            cita_id = int(cita_id)
            print(f"==> [BORRAR] cita_id convertido: {cita_id}")
    except Exception as e:
        print(f"==> [BORRAR] Error leyendo form: {e}")
        return JSONResponse(
            content={"status": "error", "msg": f"Error al procesar: {str(e)}"}, 
            status_code=400
        )
    
    if not cita_id:
        print("--> [BORRAR] ERROR: No se recibió cita_id")
        return JSONResponse(
            content={"status": "error", "msg": "ID no proporcionado"}, 
            status_code=400
        )
    
    print(f"--> [BORRAR] Buscando cita con ID: {cita_id}")
    cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    
    if cita:
        db.delete(cita)
        db.commit()
        print(f"--> [BORRAR] ✓ Cita {cita_id} eliminada con éxito")
        return JSONResponse(content={"status": "ok", "msg": "Eliminado"})
    
    print(f"--> [BORRAR] ✗ Cita {cita_id} no encontrada en BD")
    return JSONResponse(content={"status": "error", "msg": "No encontrada"}, status_code=404)

@app.delete("/api/cita/{cita_id}")
async def cancelar_cita(cita_id: int, db: Session = Depends(get_db)):
    """Cancelar una cita (soft delete)"""
    cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    if not cita:
        return JSONResponse(
            content={"status": "error", "msg": "Cita no encontrada"}, 
            status_code=404
        )
    
    cita.activo = False
    db.commit()
    return JSONResponse(content={"status": "ok", "msg": "Cita cancelada"})

@app.get("/api/estadisticas")
async def estadisticas(db: Session = Depends(get_db)):
    """Dashboard simple con estadísticas"""
    total_doctores = db.query(models.Doctor).count()
    total_pacientes = db.query(models.Paciente).count()
    total_citas = db.query(models.Cita).filter(models.Cita.activo == True).count()
    
    return {
        "doctores": total_doctores,
        "pacientes": total_pacientes,
        "citas_activas": total_citas
    }
