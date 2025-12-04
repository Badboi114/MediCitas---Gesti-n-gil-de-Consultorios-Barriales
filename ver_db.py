import sqlite3

conn = sqlite3.connect('medicitas.db')
cursor = conn.cursor()

# Ver tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("=" * 60)
print("TABLAS EN LA BASE DE DATOS")
print("=" * 60)
for table in tables:
    print(f"\n📋 {table[0]}")

# Ver doctores
print("\n" + "=" * 60)
print("DOCTORES")
print("=" * 60)
cursor.execute("SELECT * FROM doctores")
for row in cursor.fetchall():
    print(row)

# Ver pacientes
print("\n" + "=" * 60)
print("PACIENTES")
print("=" * 60)
cursor.execute("SELECT * FROM pacientes")
for row in cursor.fetchall():
    print(row)

# Ver citas
print("\n" + "=" * 60)
print("CITAS")
print("=" * 60)
cursor.execute("SELECT * FROM citas")
for row in cursor.fetchall():
    print(row)

# Ver admin
print("\n" + "=" * 60)
print("ADMIN")
print("=" * 60)
cursor.execute("SELECT * FROM admin")
for row in cursor.fetchall():
    print(row)

# Ver configuracion
print("\n" + "=" * 60)
print("CONFIGURACION")
print("=" * 60)
cursor.execute("SELECT * FROM configuracion")
for row in cursor.fetchall():
    print(row)

conn.close()
print("\n" + "=" * 60)
