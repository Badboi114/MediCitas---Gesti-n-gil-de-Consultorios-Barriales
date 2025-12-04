import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('medicitas.db')
cursor = conn.cursor()

# Verificar pacientes activos
print("=== PACIENTES ACTIVOS ===")
cursor.execute("SELECT id, ci, nombre, activo FROM pacientes WHERE activo = 1")
activos = cursor.fetchall()
for p in activos:
    print(f"ID: {p[0]}, CI: {p[1]}, Nombre: {p[2]}, Activo: {p[3]}")

# Verificar pacientes inactivos
print("\n=== PACIENTES INACTIVOS ===")
cursor.execute("SELECT id, ci, nombre, activo FROM pacientes WHERE activo = 0")
inactivos = cursor.fetchall()
if inactivos:
    for p in inactivos:
        print(f"ID: {p[0]}, CI: {p[1]}, Nombre: {p[2]}, Activo: {p[3]}")
else:
    print("No hay pacientes inactivos")

# Marcar el primer paciente como inactivo para prueba
if activos:
    primer_paciente = activos[0][0]
    print(f"\n🔴 Marcando paciente ID {primer_paciente} como inactivo...")
    cursor.execute("UPDATE pacientes SET activo = 0 WHERE id = ?", (primer_paciente,))
    conn.commit()
    print("✅ Paciente marcado como inactivo")
    
    # Verificar el cambio
    print("\n=== VERIFICACIÓN DESPUÉS DEL CAMBIO ===")
    cursor.execute("SELECT COUNT(*) FROM pacientes WHERE activo = 1")
    print(f"Pacientes activos: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM pacientes WHERE activo = 0")
    print(f"Pacientes inactivos: {cursor.fetchone()[0]}")

conn.close()
