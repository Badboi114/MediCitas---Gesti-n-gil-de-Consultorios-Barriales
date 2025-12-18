from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import re
import database, models

# --- CONFIGURACIÓN INICIAL ---
# Creamos las tablas en la BD automáticamente al iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Sistema Integral MediCitas")

# MIDDLEWARE DE SESIONES PARA LOGIN
app.add_middleware(SessionMiddleware, secret_key="medicitas_secret_key_2025_seguro")

templates = Jinja2Templates(directory="templates")

# Dependencia para obtener la sesión de BD en cada petición
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FUNCIONES DE AUTENTICACIÓN ---
def verificar_sesion(request: Request):
    """Verifica si el usuario está logueado"""
    return request.session.get("user") is not None

# --- EVENTO DE INICIO: CREAR ADMIN POR DEFECTO ---
@app.on_event("startup")
def startup_event():
    """Crea el usuario admin/admin si no existe"""
    db = database.SessionLocal()
    try:
        admin = db.query(models.Admin).first()
        if not admin:
            db.add(models.Admin(username="admin", password="admin"))
            db.commit()
            print("✓ Usuario admin creado: admin/admin")
    finally:
        db.close()

# --- 1. LANDING PAGE (La Entrada) ---
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Página de entrada con dos opciones: AdminMediCitas y MediCitas"""
    return templates.TemplateResponse("landing.html", {"request": request})

# --- 2. SISTEMA DE LOGIN ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login para administradores"""
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login_process(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    """Procesar login del administrador"""
    admin = db.query(models.Admin).filter(models.Admin.username == username).first()
    
    if admin and admin.password == password:
        # Guardar sesión
        request.session["user"] = admin.username
        return RedirectResponse(url="/admin", status_code=303)
    
    # Login fallido
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "Usuario o contraseña incorrectos"
    })

@app.get("/logout")
async def logout(request: Request):
    """Cerrar sesión del administrador"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# --- 3. MEDICITAS (Lado Público/Recepción) ---
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
    
    doctores = db.query(models.Doctor).filter(models.Doctor.activo == True).all()
    
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
        doctores = db.query(models.Doctor).filter(models.Doctor.activo == True).all()
    
    # Verificamos si es admin para mostrar el botón de "Volver al Panel"
    es_admin = verificar_sesion(request)
        
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "doctores": doctores,
        "config": config,  # Pasamos la configuración al calendario
        "es_admin": es_admin
    })

# --- 4. ADMIN MEDICITAS (Back Office) - PROTEGIDO ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Panel de Control Administrativo con Vista Tabular"""
    # PROTECCIÓN: Verificar login
    if not verificar_sesion(request):
        return RedirectResponse(url="/login", status_code=303)
    
    # Vista Tabular de Auditoría
    citas = db.query(models.Cita).order_by(models.Cita.fecha_inicio.desc()).all()
    config = db.query(models.Configuracion).first()
    if not config:
        config = models.Configuracion()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Obtener lista de pacientes para el admin (solo activos)
    pacientes = db.query(models.Paciente).filter(models.Paciente.activo == True).all()
    
    # Obtener lista de doctores (solo activos)
    doctores = db.query(models.Doctor).filter(models.Doctor.activo == True).all()
    
    # Obtener INACTIVOS para la papelera
    pacientes_inactivos = db.query(models.Paciente).filter(models.Paciente.activo == False).all()
    doctores_inactivos = db.query(models.Doctor).filter(models.Doctor.activo == False).all()
    citas_inactivas = db.query(models.Cita).filter(models.Cita.activo == False).all()
    
    # Obtener datos del admin actual
    admin_data = db.query(models.Admin).first()
    
    # Resumen rápido
    total_citas = len(citas)
    total_doctores = db.query(models.Doctor).filter(models.Doctor.activo == True).count()
    total_pacientes = len(pacientes)
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "citas": citas,
        "pacientes": pacientes,
        "doctores": doctores,
        "pacientes_inactivos": pacientes_inactivos,
        "doctores_inactivos": doctores_inactivos,
        "citas_inactivas": citas_inactivas,
        "config": config,
        "admin": admin_data,
        "stats": {"total": total_citas, "docs": total_doctores, "pacs": total_pacientes}
    })

# --- APIS ADMIN: Perfil y Configuración ---

@app.post("/admin/perfil")
async def update_admin_profile(
    request: Request,
    username: str = Form(...),
    password: str = Form(""),  # Puede estar vacío si no se quiere cambiar
    current_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Actualizar credenciales del administrador"""
    if not verificar_sesion(request):
        return RedirectResponse(url="/login", status_code=303)
    
    admin = db.query(models.Admin).first()
    if admin:
        # VALIDACIÓN CRÍTICA: Verificar contraseña actual
        if admin.password != current_password:
            # La contraseña actual NO coincide - RECHAZAR
            request.session["error_message"] = "Contraseña actual incorrecta"
            return RedirectResponse(url="/admin", status_code=303)
        
        # Actualizar username
        admin.username = username
        
        # Solo actualizar contraseña si se proporcionó una nueva
        if password and password.strip():
            admin.password = password
        
        db.commit()
        
        # Actualizar sesión con nuevo username
        request.session["user"] = username
    
    return RedirectResponse(url="/admin", status_code=303)

# API: Actualizar Configuración
@app.post("/admin/config")
async def update_config(
    hora_apertura: str = Form(...),
    hora_cierre: str = Form(...),
    dias: List[str] = Form([]),  # Recibe lista de checkboxes (ej: ["1", "2", "3"])
    db: Session = Depends(get_db)
):
    """Actualizar configuración global del consultorio"""
    config = db.query(models.Configuracion).first()
    if not config:
        config = models.Configuracion()
        db.add(config)
    
    config.hora_apertura = hora_apertura
    config.hora_cierre = hora_cierre
    config.dias_laborales = ",".join(dias)  # Guardamos como "1,2,3"
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# --- APIS GESTIÓN DE DOCTORES (ELEMENTOS) ---

@app.post("/admin/doctor/guardar")
async def guardar_doctor(
    doc_id: Optional[int] = Form(None),
    nombre: str = Form(...),
    especialidad: str = Form(...),
    duracion: int = Form(...),
    ci: str = Form(...),
    telefono: str = Form(...),
    correo: str = Form(...),
    hora_entrada: Optional[str] = Form(None),
    hora_salida: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Crear o editar un doctor"""
    if doc_id:
        # Editar doctor existente
        doc = db.query(models.Doctor).filter(models.Doctor.id == doc_id).first()
        if doc:
            doc.nombre = nombre
            doc.especialidad = especialidad
            doc.duracion_cita = duracion
            doc.ci = ci
            doc.telefono = telefono
            doc.correo = correo
            doc.hora_entrada = hora_entrada if hora_entrada else None
            doc.hora_salida = hora_salida if hora_salida else None
            db.commit()
    else:
        # Crear nuevo doctor
        nuevo = models.Doctor(
            nombre=nombre,
            especialidad=especialidad,
            duracion_cita=duracion,
            ci=ci,
            telefono=telefono,
            correo=correo,
            hora_entrada=hora_entrada if hora_entrada else None,
            hora_salida=hora_salida if hora_salida else None
        )
        db.add(nuevo)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/doctor/borrar")
async def borrar_doctor(doc_id: int = Form(...), db: Session = Depends(get_db)):
    """Soft delete: Marcar doctor como inactivo"""
    doc = db.query(models.Doctor).filter(models.Doctor.id == doc_id).first()
    if doc:
        # Soft delete: marcar como inactivo
        doc.activo = False
        db.commit()
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error", "msg": "Doctor no encontrado"}, status_code=404)

# --- APIS GESTIÓN DE PACIENTES ---

@app.post("/admin/paciente/guardar")
async def guardar_paciente(
    pac_id: int = Form(...),
    ci: str = Form(...),
    nombre: str = Form(...),
    telefono: str = Form(...),
    alergias: str = Form(default="Ninguna conocida"),
    cirugias: str = Form(default="Ninguna"),
    notas: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """Editar datos de un paciente existente"""
    # Validar formato boliviano
    if not re.match(r"^[67]\d{7}$", telefono):
        return JSONResponse({
            "status": "error", 
            "msg": "El celular debe ser boliviano (8 dígitos, empieza con 6 o 7)"
        }, status_code=400)
    
    if not re.match(r"^\d{5,10}$", ci):
        return JSONResponse({
            "status": "error", 
            "msg": "El C.I. no es válido (solo números, 5-10 dígitos)"
        }, status_code=400)
    
    pac = db.query(models.Paciente).filter(models.Paciente.id == pac_id).first()
    if pac:
        pac.ci = ci
        pac.nombre = nombre
        pac.telefono = telefono
        pac.alergias = alergias if alergias else "Ninguna conocida"
        pac.cirugias = cirugias if cirugias else "Ninguna"
        pac.notas_medicas = notas
        db.commit()
        return RedirectResponse(url="/admin", status_code=303)
    return JSONResponse({"status": "error", "msg": "Paciente no encontrado"}, status_code=404)

# --- NUEVA RUTA: CREAR PACIENTE DESDE ADMIN ---
@app.post("/admin/paciente/crear")
async def crear_paciente_admin(
    ci: str = Form(...),
    nombre: str = Form(...),
    telefono: str = Form(...),
    alergias: str = Form(default="Ninguna conocida"),
    cirugias: str = Form(default="Ninguna"),
    notas: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """Crear un nuevo paciente desde el panel de administración"""
    # Validar formato boliviano
    if not re.match(r"^[67]\d{7}$", telefono):
        return RedirectResponse(url="/admin?error=telefono_invalido", status_code=303)
    
    if not re.match(r"^\d{5,10}$", ci):
        return RedirectResponse(url="/admin?error=ci_invalido", status_code=303)
    
    # Verificar si ya existe
    pac_existente = db.query(models.Paciente).filter(models.Paciente.ci == ci).first()
    if pac_existente:
        return RedirectResponse(url="/admin?error=paciente_existe", status_code=303)
    
    # Crear nuevo paciente
    nuevo_paciente = models.Paciente(
        ci=ci,
        nombre=nombre,
        telefono=telefono,
        alergias=alergias if alergias else "Ninguna conocida",
        cirugias=cirugias if cirugias else "Ninguna",
        notas_medicas=notas
    )
    db.add(nuevo_paciente)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# --- NUEVA API: BÚSQUEDA DE PACIENTE POR CI ---
@app.get("/api/paciente/{ci}")
async def get_paciente(ci: str, db: Session = Depends(get_db)):
    """API para buscar paciente por CI (autocompletado en agenda)"""
    p = db.query(models.Paciente).filter(
        models.Paciente.ci == ci, 
        models.Paciente.activo == True
    ).first()
    
    if p:
        return JSONResponse({
            "encontrado": True,
            "nombre": p.nombre,
            "telefono": p.telefono,
            "alergias": p.alergias,
            "cirugias": p.cirugias,
            "notas": p.notas_medicas
        })
    return JSONResponse({"encontrado": False})

# --- ACTUALIZADO: SOFT DELETE DE PACIENTE ---
@app.post("/admin/paciente/borrar")
async def borrar_paciente(pac_id: int = Form(...), db: Session = Depends(get_db)):
    """Soft delete: Marcar paciente como inactivo en lugar de eliminarlo"""
    print(f"🔴 BORRAR PACIENTE - ID recibido: {pac_id}")
    pac = db.query(models.Paciente).filter(models.Paciente.id == pac_id).first()
    if pac:
        print(f"🔴 Paciente encontrado: {pac.nombre} (CI: {pac.ci})")
        # Soft delete: marcar como inactivo
        pac.activo = False
        # También desactivar sus citas
        db.query(models.Cita).filter(models.Cita.paciente_id == pac_id).update({"activo": False})
        db.commit()
        print(f"✅ Paciente {pac_id} marcado como inactivo")
        return JSONResponse({"status": "ok"})
    print(f"❌ Paciente {pac_id} NO encontrado")
    return JSONResponse({"status": "error", "msg": "Paciente no encontrado"}, status_code=404)

@app.post("/admin/paciente/restaurar")
async def restaurar_paciente(pac_id: int = Form(...), db: Session = Depends(get_db)):
    """Restaurar paciente inactivo"""
    pac = db.query(models.Paciente).filter(models.Paciente.id == pac_id).first()
    if pac:
        pac.activo = True
        db.commit()
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error", "msg": "Paciente no encontrado"}, status_code=404)

@app.post("/admin/doctor/restaurar")
async def restaurar_doctor(doc_id: int = Form(...), db: Session = Depends(get_db)):
    """Restaurar doctor inactivo"""
    doc = db.query(models.Doctor).filter(models.Doctor.id == doc_id).first()
    if doc:
        doc.activo = True
        db.commit()
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error", "msg": "Doctor no encontrado"}, status_code=404)

@app.post("/admin/cita/restaurar")
async def restaurar_cita(cita_id: int = Form(...), db: Session = Depends(get_db)):
    """Restaurar cita inactiva"""
    cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    if cita:
        cita.activo = True
        db.commit()
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error", "msg": "Cita no encontrada"}, status_code=404)

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
                        "telefono": str(cita.paciente.telefono) if cita.paciente and cita.paciente.telefono else "",
                        "motivo": str(cita.motivo) if cita.motivo else "",
                        # Datos del historial médico
                        "alergias": str(cita.paciente.alergias) if cita.paciente and cita.paciente.alergias else "Ninguna conocida",
                        "cirugias": str(cita.paciente.cirugias) if cita.paciente and cita.paciente.cirugias else "Ninguna",
                        "notas": str(cita.paciente.notas_medicas) if cita.paciente and cita.paciente.notas_medicas else ""
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

# API: Buscar Paciente por CI Exacto (Para autocompletado en formulario)
@app.get("/api/buscar-paciente")
async def buscar_paciente(q: str, db: Session = Depends(get_db)):
    """API para búsqueda predictiva de pacientes por CI (solo activos)"""
    pacientes = db.query(models.Paciente).filter(
        models.Paciente.ci.like(f"{q}%"),
        models.Paciente.activo == True
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
    cita_id: Optional[int] = Form(None),
    doctor_id: int = Form(...),
    fecha_inicio_str: str = Form(...),
    fecha_fin_str: str = Form(...),
    paciente_ci: str = Form(...),
    paciente_nombre: str = Form(...),
    paciente_telefono: str = Form(...),
    # Campos de historial médico
    paciente_alergias: str = Form(default="Ninguna conocida"),
    paciente_cirugias: str = Form(default="Ninguna"),
    paciente_notas: str = Form(default=""),
    motivo: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agendar cita con hora de fin manual (soporta creación y edición) + Historial Médico"""
    
    print(f"🔵 AGENDAR CITA - Recibido: doctor_id={doctor_id}, ci={paciente_ci}, nombre={paciente_nombre}")
    
    # 1. VALIDACIONES BOLIVIANAS (Seguridad Backend)
    
    # Validar Celular: Empieza con 6 o 7, y tiene 8 dígitos en total
    if not re.match(r"^[67]\d{7}$", paciente_telefono):
        return JSONResponse(
            content={"status": "error", "msg": "El celular debe ser boliviano (8 dígitos, empieza con 6 o 7)"}, 
            status_code=400
        )

    # Validar CI: Solo números, entre 5 y 10 dígitos (Formato estándar Bolivia)
    if not re.match(r"^\d{5,10}$", paciente_ci):
        return JSONResponse(
            content={"status": "error", "msg": "El C.I. no es válido (solo números, 5-10 dígitos)"}, 
            status_code=400
        )
    
    # 2. Convertir fechas
    try:
        fecha_inicio = datetime.fromisoformat(fecha_inicio_str.replace('Z', '+00:00'))
        fecha_fin = datetime.fromisoformat(fecha_fin_str.replace('Z', '+00:00'))
    except ValueError:
        return JSONResponse(content={"status": "error", "msg": "Formato de fecha inválido"}, status_code=400)

    # 3. VALIDACIÓN: ¿Hay choque de horario? (Excluyendo la cita actual si es edición)
    query_choque = db.query(models.Cita).filter(
        models.Cita.doctor_id == doctor_id,
        models.Cita.activo == True,
        models.Cita.fecha_inicio < fecha_fin,
        models.Cita.fecha_fin > fecha_inicio
    )
    if cita_id:
        query_choque = query_choque.filter(models.Cita.id != cita_id)

    if query_choque.first():
        return JSONResponse(content={"status": "error", "msg": "⛔ HORARIO OCUPADO"}, status_code=400)

    # 4. Gestionar Paciente (Buscar o Crear) + Guardar Historial Médico
    paciente = db.query(models.Paciente).filter(models.Paciente.ci == paciente_ci).first()
    if not paciente:
        # No existe: Crear nuevo paciente con historial
        paciente = models.Paciente(
            ci=paciente_ci, 
            nombre=paciente_nombre, 
            telefono=paciente_telefono,
            alergias=paciente_alergias,
            cirugias=paciente_cirugias,
            notas_medicas=paciente_notas
        )
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    else:
        # Ya existe: Actualizar todos los datos incluyendo historial
        paciente.nombre = paciente_nombre
        paciente.telefono = paciente_telefono
        paciente.alergias = paciente_alergias
        paciente.cirugias = paciente_cirugias
        paciente.notas_medicas = paciente_notas
        # Reactivar si estaba inactivo
        if not paciente.activo:
            paciente.activo = True
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
    
    print(f"🟢 Guardando cita en BD...")
    db.commit()
    print(f"✅ Cita guardada exitosamente. Paciente ID: {paciente.id}, Cita modo: {'edición' if cita_id else 'nueva'}")
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
        # Soft delete: marcar como inactivo en lugar de eliminar
        cita.activo = False
        db.commit()
        print(f"--> [BORRAR] ✓ Cita {cita_id} marcada como inactiva")
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
