"""
Script de Inicialización de la Base de Datos MySQL para Alas del Viento.
Este script:
 1. Se conecta a MySQL en localhost.
 2. Crea la base de datos `alvear365_db` si no existe.
 3. Crea las tablas `eventos` y `preinscripciones` usando SQLAlchemy.
 4. Pobla la tabla con los eventos iniciales del Coro Alas del Viento definidos en `eventos.py`.
"""

import sys
import os
import pymysql
from datetime import datetime

# NUEVO PARA CONEXION CON DB LOCAL MYSQL: Credenciales predeterminadas de MySQL
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")  # Contraseña por defecto para tu conexión local MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
DB_NAME = "alvear365_db"

def init_database():
    print("--------------------------------------------------")
    print("🚀 Iniciando migración e inicialización de Base de Datos...")
    print("--------------------------------------------------")

    # PARA RENDER DEPLOY: Si se detecta DATABASE_URL (PostgreSQL en Render), la base de datos ya está creada por Render
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # 1. Crear la Base de Datos en MySQL local usando pymysql directamente
        try:
            connection = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                port=MYSQL_PORT,
                charset='utf8mb4'
            )
            with connection.cursor() as cursor:
                print(f"📡 Conectado al servidor MySQL ({MYSQL_HOST}:{MYSQL_PORT})...")
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print(f"✅ Base de datos '{DB_NAME}' verificada/creada correctamente.")
            connection.close()
        except Exception as e:
            print(f"❌ Error al conectar con servidor MySQL: {e}")
            print("📌 Sugerencia: Revisa tus credenciales de MySQL (usuario y contraseña en init_db.py) y que el servicio de MySQL esté iniciado.")
            return False
    else:
        # PARA RENDER DEPLOY: Mensaje informativo en Render
        print("📡 Conectando a Base de Datos PostgreSQL en Render vía DATABASE_URL...")

    # 2. Inicializar SQLAlchemy y crear tablas + sembrar datos
    try:
        from app import app, db, Evento
        from eventos import eventos as datos_iniciales

        with app.app_context():
            # Crear la estructura de la tabla
            db.create_all()
            print("✅ Tablas SQLAlchemy creadas/verificadas en la base de datos.")

            # Comprobar si ya existen registros
            cantidad_actual = Evento.query.count()
            if cantidad_actual == 0:
                print(f"🌱 Poblando la tabla 'eventos' con {len(datos_iniciales)} eventos iniciales...")
                for item in datos_iniciales:
                    fecha_ini = datetime.strptime(item["fecha_inicio"], "%Y-%m-%d").date()
                    fecha_fi = datetime.strptime(item["fecha_fin"], "%Y-%m-%d").date()
                    
                    nuevo = Evento(
                        id=item.get("id"),
                        nombre=item.get("nombre"),
                        descripcion=item.get("descripcion"),
                        tipo=item.get("tipo"),
                        fecha_inicio=fecha_ini,
                        fecha_fin=fecha_fi,
                        hora=item.get("hora"),
                        costo=str(item.get("costo", "0")),
                        lugar=item.get("lugar"),
                        lugar_corto=item.get("lugar_corto", item.get("lugar")),
                        direccion=item.get("direccion", ""),
                        imagen=item.get("imagen")
                    )
                    db.session.add(nuevo)
                db.session.commit()
                print("🎉 Registros iniciales insertados con éxito.")
            else:
                print(f"ℹ️ La tabla 'eventos' ya contiene {cantidad_actual} registros. No se duplicaron datos.")

        print("--------------------------------------------------")
        print("✨ ¡Migración completada exitosamente!")
        print("--------------------------------------------------")
        return True
    except Exception as e:
        print(f"❌ Error durante la creación de tablas/sembrado: {e}")
        return False

if __name__ == "__main__":
    init_database()
