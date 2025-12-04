from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from database import Base

class Doctor(Base):
    """Tabla de Doctores - 100% personalizable"""
    __tablename__ = "doctores"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    especialidad = Column(String)
    duracion_cita = Column(Integer, default=30)  # Minutos por cita
    
    # --- NUEVOS CAMPOS ---
    ci = Column(String, default="")
    telefono = Column(String, default="")
    correo = Column(String, default="")
    
    # Horarios Personalizados (Si están vacíos, usa el global)
    hora_entrada = Column(String, nullable=True)  # Ej: "09:00"
    hora_salida = Column(String, nullable=True)   # Ej: "16:00"
    
    # Soft Delete
    activo = Column(Boolean, default=True)

    # Relación con citas
    citas = relationship("Cita", back_populates="doctor")

class Paciente(Base):
    """Tabla de Pacientes con Historial Clínico"""
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    ci = Column(String, unique=True, index=True)
    nombre = Column(String)
    telefono = Column(String)
    
    # Soft Delete
    activo = Column(Boolean, default=True)
    
    # --- CAMPOS DE HISTORIAL MÉDICO ---
    alergias = Column(Text, default="Ninguna conocida")
    cirugias = Column(Text, default="Ninguna")
    notas_medicas = Column(Text, default="")

    # Relación con citas
    citas = relationship("Cita", back_populates="paciente")

class Cita(Base):
    """Tabla de Citas - Con validación manual de choques"""
    __tablename__ = "citas"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctores.id"))
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    motivo = Column(String)
    activo = Column(Boolean, default=True)

    # Relaciones
    doctor = relationship("Doctor", back_populates="citas")
    paciente = relationship("Paciente", back_populates="citas")

class Configuracion(Base):
    """Tabla de Configuración Global - Panel Administrativo"""
    __tablename__ = "configuracion"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_consultorio = Column(String, default="MediCitas")
    hora_apertura = Column(String, default="08:00")  # Formato "HH:MM"
    hora_cierre = Column(String, default="20:00")    # Formato "HH:MM"
    # Días laborales: String separado por comas (0=Domingo, 1=Lunes...)
    dias_laborales = Column(String, default="1,2,3,4,5")

class Admin(Base):
    """Tabla de Administrador - Sistema de Login"""
    __tablename__ = "admin"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, default="admin")
    password = Column(String, default="admin")  # En producción usar hash (bcrypt)
