from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Doctor(Base):
    """Tabla de Doctores - 100% personalizable"""
    __tablename__ = "doctores"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    especialidad = Column(String)
    duracion_cita = Column(Integer, default=30)  # Minutos por cita

    # Relación con citas
    citas = relationship("Cita", back_populates="doctor")

class Paciente(Base):
    """Tabla de Pacientes - Sin campos ocultos"""
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    ci = Column(String, unique=True, index=True)
    nombre = Column(String)
    telefono = Column(String)

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
