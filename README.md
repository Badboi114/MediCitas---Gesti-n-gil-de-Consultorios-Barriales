# MediCitas - Sistema de Gestión de Citas Médicas

## 🏥 Descripción

MediCitas es una plataforma web integral para la modernización administrativa de Consultorios Médicos de Primer Nivel. Digitaliza el flujo de trabajo operativo desde el registro de pacientes hasta la concreción y seguimiento de consultas médicas.

**100% Código Personalizable** - Sin frameworks pesados ni "magia" oculta. Tú controlas cada línea de código.

## ✨ Características Principales

- **Gestión de Pacientes**: Registro y búsqueda predictiva por cédula de identidad
- **Directorio Médico**: Configuración de doctores con especialidades y tiempos personalizados
- **Agenda Interactiva**: Calendario visual con validación anti-choques de horarios
- **Historial de Atención**: Seguimiento automático de visitas por paciente
- **Validación Inteligente**: Prevención de citas superpuestas y horarios conflictivos (matemática pura)

## 🛠️ Tecnologías

- **Backend**: Python 3.12 + FastAPI (moderno, rápido, minimalista)
- **ORM**: SQLAlchemy (control total de la base de datos)
- **Base de Datos**: SQLite (escalable a PostgreSQL/MySQL)
- **Frontend**: HTML5 + TailwindCSS + FullCalendar.js
- **Servidor**: Uvicorn (ASGI de alto rendimiento)

## 🚀 Instalación y Configuración

### 1. Activar el Entorno Virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Las dependencias ya están instaladas

El proyecto incluye:
- FastAPI
- Uvicorn
- SQLAlchemy
- Jinja2
- Python-multipart

### 3. Ejecutar el Servidor

```powershell
uvicorn main:app --reload
```

El servidor se iniciará en: **http://127.0.0.1:8000/**

### 4. Primera Ejecución

Al iniciar por primera vez, el sistema:
- Crea automáticamente la base de datos `medicitas.db`
- Genera 4 doctores de prueba
- Está listo para usar inmediatamente

## 📖 Uso del Sistema

### Agendar una Cita

1. Accede a **http://127.0.0.1:8000/**
2. Selecciona un doctor del menú desplegable
3. Haz clic en un espacio vacío (blanco) del calendario
4. Ingresa la Cédula de Identidad del paciente
   - Si existe, se autocompletará su nombre
   - Si es nuevo, escribe su nombre completo
5. Ingresa el motivo de consulta
6. Confirma la reserva

### Validaciones Automáticas

El sistema previene:
- ✅ Citas superpuestas (anti-choques)
- ✅ Reservas en horarios ocupados
- ✅ Citas en fechas pasadas

## 📁 Estructura del Proyecto

```
pro2/
├── database.py          # Conexión a BD (100% manual)
├── models.py            # Definición de tablas (sin campos ocultos)
├── main.py              # Lógica de negocio y rutas API
├── templates/           # Templates HTML
│   └── index.html       # Interfaz principal
├── medicitas.db         # Base de datos SQLite (se crea automáticamente)
└── README.md            # Este archivo
```

## 🔧 Comandos Útiles

### Ejecutar el servidor
```powershell
uvicorn main:app --reload
```

### Ejecutar en otro puerto
```powershell
uvicorn main:app --reload --port 8080
```

### Ver logs detallados
```powershell
uvicorn main:app --reload --log-level debug
```

## 🎨 Personalización

### Modificar Horarios de Atención

Edita `templates/index.html`, busca la configuración del calendario:

```javascript
slotMinTime: '08:00:00', // Hora de apertura
slotMaxTime: '20:00:00', // Hora de cierre
hiddenDays: [0],         // Días ocultos (0 = Domingo)
slotDuration: '00:15:00', // 15 minutos por bloque
```

### Agregar Nuevos Doctores

Opción 1: Directamente en la BD usando un script Python:
```python
from database import SessionLocal
from models import Doctor

db = SessionLocal()
nuevo_doctor = Doctor(
    nombre="Ana Martínez",
    especialidad="Neurología",
    duracion_cita=60
)
db.add(nuevo_doctor)
db.commit()
```

Opción 2: Crear una interfaz de administración personalizada (tú decides cómo)

### Cambiar Colores del Tema

Edita `templates/index.html` y modifica las clases de TailwindCSS:
- `emerald-500` → `blue-500` (cambiar color principal)
- `bg-gradient-to-br from-gray-50 to-gray-100` → personalizar fondo

### Modificar Validación de Choques

Edita `main.py`, función `agendar_cita()`, sección de validación (línea ~95):

```python
# VALIDACIÓN CRÍTICA: Aquí TÚ controlas la lógica
choque = db.query(models.Cita).filter(
    models.Cita.doctor_id == doctor_id,
    models.Cita.activo == True,
    models.Cita.fecha_inicio < fecha_fin,
    models.Cita.fecha_fin > fecha_inicio
).first()
```

## 📊 Modelo de Datos

### Paciente
- CI (único)
- Nombre completo
- Fecha de nacimiento
- Teléfono
- Fecha de registro

### Doctor
- Nombre
- Especialidad (FK)
- Duración de cita (minutos)

### Cita
- Doctor (FK)
- Paciente (FK)
- Fecha/hora inicio
- Fecha/hora fin (calculada automáticamente)
- Motivo de consulta
- Estado (Pendiente/Atendido/Cancelado)

## 🔒 Seguridad

- Validación de datos en el backend
- Protección CSRF en formularios
- Prevención de SQL injection (ORM de Django)
- Validación anti-choques de horarios

## 📝 Notas Importantes

- **100% Código Abierto**: Sin dependencias pesadas, todo el código es tuyo
- **Sin ORM Mágico**: SQLAlchemy te da control total sin ocultar nada
- **Sin Admin Panel**: Tú decides cómo administrar (puedes crear tu propia interfaz)
- **Escalable**: Cambia SQLite por PostgreSQL editando una sola línea en `database.py`
- Las citas se calculan automáticamente según duración del doctor
- Validación de choques implementada con lógica matemática pura

## 🚀 Ventajas sobre Django

✅ **Más rápido**: FastAPI es 2-3x más rápido que Django  
✅ **Más ligero**: Sin código innecesario  
✅ **100% Transparente**: Ves y controlas toda la lógica  
✅ **Más moderno**: Async/await nativo  
✅ **API First**: Fácil integrar con apps móviles  
✅ **Sin migraciones complejas**: Control directo de la BD  

## 🚀 Próximas Mejoras Sugeridas

- [ ] Agregar autenticación con JWT
- [ ] Crear panel de administración personalizado
- [ ] Implementar WebSockets para actualizaciones en tiempo real
- [ ] Agregar exportación a PDF/Excel
- [ ] Sistema de notificaciones (SMS/Email)
- [ ] API REST completa para app móvil
- [ ] Dashboard con estadísticas visuales

## 📧 Soporte

Documentación FastAPI: https://fastapi.tiangolo.com/
Documentación SQLAlchemy: https://docs.sqlalchemy.org/

---

**MediCitas** - Sistema Profesional 100% Personalizable  
Desarrollado con ❤️ usando FastAPI + Python Puro
