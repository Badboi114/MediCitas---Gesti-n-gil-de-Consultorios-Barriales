from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import database, models

# --- CONFIGURACIÓN INICIAL ---
# Creamos las tablas en la BD automáticamente al iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="MediCitas Pro - 100% Personalizable")
templates = Jinja2Templates(directory="templates")

# Dependencia para obtener la sesión de BD en cada petición
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- RUTAS DE LA APLICACIÓN ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Renderiza la página principal"""
    doctores = db.query(models.Doctor).all()
    
    # Si no hay doctores, creamos algunos de prueba para que no se vea vacío
    if not doctores:
        doctores_prueba = [
            models.Doctor(nombre="Juan Pérez", especialidad="Medicina General", duracion_cita=30),
            models.Doctor(nombre="María López", especialidad="Cardiología", duracion_cita=45),
            models.Doctor(nombre="Carlos Rodríguez", especialidad="Pediatría", duracion_cita=30),
            models.Doctor(nombre="Ana García", especialidad="Odontología", duracion_cita=40),
        ]
        for doc in doctores_prueba:
            db.add(doc)
        db.commit()
        doctores = db.query(models.Doctor).all()
        
    return templates.TemplateResponse("index.html", {"request": request, "doctores": doctores})

@app.get("/api/citas/{doctor_id}")
async def obtener_citas(doctor_id: int, db: Session = Depends(get_db)):
    """API que devuelve las citas para pintar el calendario"""
    citas = db.query(models.Cita).filter(
        models.Cita.doctor_id == doctor_id, 
        models.Cita.activo == True
    ).all()
    
    eventos = []
    for cita in citas:
        eventos.append({
            "title": f"{cita.paciente.nombre}",
            "start": cita.fecha_inicio.isoformat(),
            "end": cita.fecha_fin.isoformat(),
            "color": "#e74c3c",  # Rojo para ocupado
            "extendedProps": {
                "motivo": cita.motivo,
                "ci": cita.paciente.ci
            }
        })
    return eventos

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
    doctor_id: int = Form(...),
    fecha_inicio_str: str = Form(...),
    paciente_ci: str = Form(...),
    paciente_nombre: str = Form(...),
    paciente_telefono: str = Form(default=""),
    motivo: str = Form(...),
    db: Session = Depends(get_db)
):
    """Lógica Maestra: Agendar con validación de choques"""
    
    # 1. Convertir fecha (viene del calendario JS en formato ISO)
    try:
        fecha_inicio = datetime.fromisoformat(fecha_inicio_str.replace('Z', '+00:00'))
    except ValueError:
        return JSONResponse(
            content={"status": "error", "msg": "Formato de fecha inválido"}, 
            status_code=400
        )

    # 2. Buscar el doctor y calcular fin de cita según su duración
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        return JSONResponse(
            content={"status": "error", "msg": "Doctor no encontrado"}, 
            status_code=404
        )
    
    fecha_fin = fecha_inicio + timedelta(minutes=doctor.duracion_cita)

    # 3. VALIDACIÓN CRÍTICA: ¿Hay choque de horario? (Matemática pura - TÚ controlas la lógica)
    # Buscamos citas del mismo doctor que se solapen con el nuevo horario
    choque = db.query(models.Cita).filter(
        models.Cita.doctor_id == doctor_id,
        models.Cita.activo == True,
        models.Cita.fecha_inicio < fecha_fin,
        models.Cita.fecha_fin > fecha_inicio
    ).first()

    if choque:
        return JSONResponse(
            content={
                "status": "error", 
                "msg": "⛔ HORARIO OCUPADO: Ya existe una cita en ese lapso."
            }, 
            status_code=400
        )

    # 4. Buscar o Crear Paciente (Registro Express)
    paciente = db.query(models.Paciente).filter(models.Paciente.ci == paciente_ci).first()
    if not paciente:
        paciente = models.Paciente(
            ci=paciente_ci, 
            nombre=paciente_nombre, 
            telefono=paciente_telefono
        )
        db.add(paciente)
        db.commit()
        db.refresh(paciente)

    # 5. Guardar la Cita
    nueva_cita = models.Cita(
        doctor_id=doctor_id,
        paciente_id=paciente.id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        motivo=motivo
    )
    db.add(nueva_cita)
    db.commit()

    return JSONResponse(content={"status": "ok", "msg": "✅ Cita agendada con éxito"})

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
