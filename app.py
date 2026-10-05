import os
import sys
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

# Asegurar codificación utf-8 en consola de Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Clave secreta para acceso administrativo al panel de preinscripciones
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "alas_admin_2026")

# Datos iniciales de respaldo en memoria si la BD no está activa aún
from eventos import eventos as eventos_fallback

preinscripciones_fallback = []

app = Flask(__name__)

# PARA RENDER DEPLOY: Configuración dinámica de Base de Datos (PostgreSQL en Render o MySQL en local)
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")  # Contraseña para conexión MySQL local
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "alvear365_db")

raw_database_url = os.getenv("DATABASE_URL")
if raw_database_url:
    # PARA RENDER DEPLOY: Render provee URLs con 'postgres://', SQLAlchemy requiere 'postgresql://'
    if raw_database_url.startswith("postgres://"):
        DATABASE_URI = raw_database_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URI = raw_database_url
else:
    # PARA RENDER DEPLOY: Fallback a MySQL local si no existe variable DATABASE_URL
    DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "alasdelviento-secret-key")

# NUEVO PARA CONEXION CON DB LOCAL MYSQL: Inicialización de la extensión SQLAlchemy
db = SQLAlchemy(app)


# NUEVO PARA CONEXION CON DB LOCAL MYSQL: Modelo ORM de SQLAlchemy para la tabla 'eventos'
class Evento(db.Model):
    __tablename__ = 'eventos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(10), nullable=False)
    costo = db.Column(db.String(50), default="0")
    lugar = db.Column(db.String(255), nullable=False)
    lugar_corto = db.Column(db.String(255), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    imagen = db.Column(db.Text, nullable=True)

    def __init__(self, nombre, descripcion, tipo, fecha_inicio, fecha_fin, hora, costo="0", lugar="", lugar_corto=None, direccion=None, imagen=None, id=None):
        if id is not None:
            self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.tipo = tipo
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.hora = hora
        self.costo = costo
        self.lugar = lugar
        self.lugar_corto = lugar_corto
        self.direccion = direccion
        self.imagen = imagen

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion or "",
            "tipo": self.tipo or "",
            "fecha_inicio": self.fecha_inicio.strftime("%Y-%m-%d") if isinstance(self.fecha_inicio, (datetime, date)) else str(self.fecha_inicio),
            "fecha_fin": self.fecha_fin.strftime("%Y-%m-%d") if isinstance(self.fecha_fin, (datetime, date)) else str(self.fecha_fin),
            "hora": self.hora or "",
            "costo": self.costo or "0",
            "lugar": self.lugar or "",
            "lugar_corto": self.lugar_corto or self.lugar or "",
            "direccion": self.direccion or "",
            "imagen": self.imagen or ""
        }


# NUEVO PARA CONEXION CON DB LOCAL MYSQL: Modelo ORM de SQLAlchemy para la tabla 'preinscripciones'
class Preinscripcion(db.Model):
    __tablename__ = 'preinscripciones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_apellido = db.Column(db.String(255), nullable=False)
    dni = db.Column(db.String(50), nullable=False)
    fecha_nacimiento = db.Column(db.String(50), nullable=False)
    edad = db.Column(db.Integer, nullable=False)
    domicilio = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    sala = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, nombre_apellido, dni, fecha_nacimiento, edad, domicilio, email, telefono, sala, created_at=None, id=None):
        if id is not None:
            self.id = id
        self.nombre_apellido = nombre_apellido
        self.dni = dni
        self.fecha_nacimiento = fecha_nacimiento
        self.edad = edad
        self.domicilio = domicilio
        self.email = email
        self.telefono = telefono
        self.sala = sala
        if created_at is not None:
            self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_apellido": self.nombre_apellido,
            "dni": self.dni,
            "fecha_nacimiento": self.fecha_nacimiento,
            "edad": self.edad,
            "domicilio": self.domicilio,
            "email": self.email,
            "telefono": self.telefono,
            "sala": self.sala,
            "created_at": self.created_at
        }


# PARA RENDER DEPLOY: Creación automática de tablas en PostgreSQL/MySQL y sembrado de eventos iniciales
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de Datos conectada: Tablas 'eventos' y 'preinscripciones' verificadas/creadas.")

        # PARA RENDER DEPLOY: Si es la primera vez que corre en PostgreSQL (Render) y la BD está vacía, sembrar eventos del coro
        if Evento.query.count() == 0:
            print("🌱 Base de datos vacía. Sembrando eventos iniciales del Coro Alas del Viento...")
            for item in eventos_fallback:
                fecha_ini = datetime.strptime(item["fecha_inicio"], "%Y-%m-%d").date()
                fecha_fi = datetime.strptime(item["fecha_fin"], "%Y-%m-%d").date()
                nuevo_ev = Evento(
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
                db.session.add(nuevo_ev)
            db.session.commit()
            print("🎉 Eventos iniciales sembrados exitosamente.")
    except Exception as _e:
        print(f"⚠️ Alerta BD: No se pudieron verificar/crear tablas en BD ({_e}). Usando modo seguro en memoria.")


def get_all_eventos():
    """NUEVO PARA CONEXION CON DB LOCAL MYSQL: Obtiene los eventos desde la base de datos MySQL."""
    try:
        eventos_db = Evento.query.order_by(Evento.fecha_inicio.asc()).all()
        if eventos_db:
            return [e.to_dict() for e in eventos_db]
    except Exception as err:
        print(f"⚠️ Alerta BD: No se pudo consultar la base de datos MySQL ({err}). Usando datos temporales.")
    
    return sorted(eventos_fallback, key=lambda e: datetime.strptime(e["fecha_inicio"], "%Y-%m-%d"))


@app.route("/")
def index():
    lista_eventos = get_all_eventos()
    preinscripto = request.args.get("preinscripto")
    sala_registrada = request.args.get("sala", "")
    return render_template("index.html", eventos=lista_eventos, preinscripto=preinscripto, sala_registrada=sala_registrada)


@app.template_filter('format_date')
def format_date_filter(date_val):
    """Convierte fechas (date, datetime o string) a formato legible DD-MM-YYYY (con HH:MM si corresponde)."""
    if not date_val:
        return "-"
    if isinstance(date_val, (datetime, date)):
        if isinstance(date_val, datetime) and (date_val.hour != 0 or date_val.minute != 0):
            return date_val.strftime("%d-%m-%Y %H:%M")
        return date_val.strftime("%d-%m-%Y")
    val_str = str(date_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(val_str, fmt)
            if "%H" in fmt and (dt.hour != 0 or dt.minute != 0):
                return dt.strftime("%d-%m-%Y %H:%M")
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue
    return val_str


@app.route("/evento/<int:event_id>")
def evento_detalle(event_id):
    try:
        # NUEVO PARA CONEXION CON DB LOCAL MYSQL: Búsqueda en MySQL
        evento_obj = Evento.query.get(event_id)
        if evento_obj:
            return render_template("evento.html", evento=evento_obj.to_dict())
    except Exception:
        pass
    
    # Fallback en lista temporal
    evento = next((e for e in eventos_fallback if e["id"] == event_id), None)
    if not evento:
        return "Evento no encontrado", 404
    return render_template("evento.html", evento=evento)


@app.route("/agregar_evento", methods=["POST"])
def agregar_evento():
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")
    tipo = request.form.get("tipo")
    fecha_inicio_str = request.form.get("fecha_inicio")
    fecha_fin_str = request.form.get("fecha_fin")
    hora = request.form.get("hora")
    costo = request.form.get("costo") or "0"
    lugar = request.form.get("lugar")

    mapping_corto = {
        "General Alvear Mendoza": "General Alvear",
        "Bowen General Alvear Mendoza": "Bowen",
        "San Pedro del Atuel General Alvear Mendoza": "San Pedro del Atuel",
        "Alvear Oeste General Alvear Mendoza": "Alvear Oeste"
    }
    lugar_corto = mapping_corto.get(lugar, lugar)
    direccion = request.form.get("direccion")
    imagen = request.form.get("imagen") or \
        "/static/img/carrusel1.png"

    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()

        # NUEVO PARA CONEXION CON DB LOCAL MYSQL: Guardar nuevo evento en MySQL
        nuevo_evento = Evento(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            fecha_inicio=fecha_inicio_dt,
            fecha_fin=fecha_fin_dt,
            hora=hora,
            costo=costo,
            lugar=lugar,
            lugar_corto=lugar_corto,
            direccion=direccion,
            imagen=imagen
        )

        db.session.add(nuevo_evento)
        db.session.commit()
        print("✅ Evento guardado con éxito en la base de datos MySQL.")
    except Exception as err:
        print(f"❌ Error al guardar evento en MySQL: {err}")
        db.session.rollback()

        # Respaldo en memoria si falla la base de datos
        nuevo_evento_dict = {
            "id": len(eventos_fallback),
            "nombre": nombre,
            "descripcion": descripcion,
            "tipo": tipo,
            "fecha_inicio": fecha_inicio_str,
            "fecha_fin": fecha_fin_str,
            "hora": hora,
            "costo": costo,
            "lugar": lugar,
            "lugar_corto": lugar_corto,
            "direccion": direccion,
            "imagen": imagen
        }
        eventos_fallback.append(nuevo_evento_dict)

    return redirect(url_for("index"))


@app.route("/preinscribir", methods=["POST"])
def preinscribir():
    nombre_apellido = request.form.get("nombre_apellido")
    dni = request.form.get("dni")
    fecha_nacimiento = request.form.get("fecha_nacimiento")
    edad = request.form.get("edad")
    domicilio = request.form.get("domicilio")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    sala = request.form.get("sala")

    try:
        # NUEVO PARA CONEXION CON DB LOCAL MYSQL: Guardar preinscripción en MySQL
        nueva_prein = Preinscripcion(
            nombre_apellido=nombre_apellido,
            dni=dni,
            fecha_nacimiento=str(fecha_nacimiento),
            edad=int(edad) if edad else 0,
            domicilio=domicilio,
            email=email,
            telefono=telefono,
            sala=sala
        )
        db.session.add(nueva_prein)
        db.session.commit()
        print("✅ Preinscripción registrada con éxito en la base de datos MySQL.")
    except Exception as err:
        print(f"⚠️ Alerta BD preinscripción ({err}). Guardando en memoria.")
        db.session.rollback()

        # Respaldo en memoria si falla la base de datos
        preinscripciones_fallback.insert(0, {
            "id": len(preinscripciones_fallback) + 1,
            "nombre_apellido": nombre_apellido,
            "dni": dni,
            "fecha_nacimiento": fecha_nacimiento,
            "edad": int(edad) if edad else 0,
            "domicilio": domicilio,
            "email": email,
            "telefono": telefono,
            "sala": sala,
            "created_at": datetime.utcnow()
        })

    return redirect(url_for("index", preinscripto="success", sala=sala))


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


# ==============================================================================
# PANEL SUPERADMIN - PREINSCRIPCIONES DE ALUMNOS (ALAS DEL VIENTO)
# ==============================================================================
@app.route("/admin/preinscripciones")
def admin_preinscripciones():
    """
    Ruta administrativa secreta para visualización de preinscripciones.
    Seguridad: Autenticación por query parameter (?key=...) o sesión activa.
    Si la clave no es válida o falta, responde HTTP 403 Forbidden.
    """
    key_param = request.args.get("key")

    # Autenticación mediante parámetro query 'key' o sesión activa
    if key_param:
        if key_param == ADMIN_SECRET_KEY:
            session["admin_authenticated"] = True
        else:
            session.pop("admin_authenticated", None)
            return render_template("admin_forbidden.html", mensaje="Clave de administración incorrecta."), 403

    if not session.get("admin_authenticated"):
        return render_template(
            "admin_forbidden.html",
            mensaje="Acceso denegado. Se requiere clave de autorización para acceder al Panel SuperAdmin."
        ), 403

    # Consulta a Base de Datos MySQL con Flask-SQLAlchemy ordenada por created_at.desc()
    try:
        preinscripciones = Preinscripcion.query.order_by(Preinscripcion.created_at.desc()).all()
    except Exception as err:
        print(f"⚠️ Alerta BD admin ({err}). Usando datos de respaldo en memoria.")
        preinscripciones = sorted(
            preinscripciones_fallback,
            key=lambda x: x.get("created_at", datetime.min) if isinstance(x, dict) else (x.created_at or datetime.min),
            reverse=True
        )

    # Cálculo de métricas y contadores por sala
    total_inscriptos = len(preinscripciones)
    
    def extraer_sala(p):
        if isinstance(p, dict):
            return p.get("sala", "") or ""
        return getattr(p, "sala", "") or ""

    total_sala_0_5 = sum(1 for p in preinscripciones if "0 a 5" in extraer_sala(p))
    total_sala_6_11 = sum(1 for p in preinscripciones if "6 a 11" in extraer_sala(p))
    total_sala_12_17 = sum(1 for p in preinscripciones if "12 a 17" in extraer_sala(p))

    return render_template(
        "admin_preinscripciones.html",
        preinscripciones=preinscripciones,
        total_inscriptos=total_inscriptos,
        total_sala_0_5=total_sala_0_5,
        total_sala_6_11=total_sala_6_11,
        total_sala_12_17=total_sala_12_17
    )


@app.route("/admin/logout")
def admin_logout():
    """Cierra la sesión administrativa."""
    session.pop("admin_authenticated", None)
    return redirect(url_for("index"))


# PARA RENDER DEPLOY: Ejecución con puerto dinámico asignado por Render ($PORT) o 5000 por defecto
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")




