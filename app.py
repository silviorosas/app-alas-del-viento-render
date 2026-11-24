# ==================================================================
# Alas del Viento · Aplicación Flask (backend)
# Agenda de eventos de General Alvear (Mendoza) + oferta educativa.
# VERSIÓN PÚBLICA:  /  ·  /evento/<id>  ·  /preinscripcion (POST)
# VERSIÓN ADMIN:    /admin (mismo sitio + botón Nuevo Evento)  ·  /admin/dashboard (preinscriptos)
#                   /admin/agregar_evento (POST)   [el prefijo /admin se puede cambiar con ADMIN_PATH]
# Base de datos MySQL `alas_del_viento`: tablas `eventos`, `preinscripciones` y `comentarios`.
# ==================================================================
import os
import json
# Flask: app web | render_template: renderiza plantillas Jinja2 | request: datos del formulario
# redirect/url_for: redirecciones | flash: mensajes temporales para el usuario
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
# datetime/date: se usan para validar fechas y para el filtro `format_date`
from datetime import datetime, date
# pymysql: driver para conectarse a MySQL (con manejo seguro por si no está instalado)
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

# Crea la aplicación Flask; las plantillas se buscan en la carpeta /templates
app = Flask(__name__)

# Necesario para usar flash() (mensajes al usuario)
app.secret_key = os.environ.get("SECRET_KEY", "cambiar-esta-clave-en-produccion")

# ------------------------------------------------------------------
# VERSIÓN ADMINISTRADOR (sin usuario ni contraseña)
# El sitio tiene dos versiones según el LINK que se abra:
#   - Link normal  (/)       -> versión pública
#   - Link admin   (/admin)  -> misma página + botón "Nuevo Evento" + dashboard de preinscriptos
# IMPORTANTE: como no hay contraseña, la única protección es que el link sea secreto.
# Conviene cambiar el prefijo por uno difícil de adivinar con la variable de entorno
# ADMIN_PATH (ej. ADMIN_PATH=panel-alas-x7k2 -> el link pasa a ser /panel-alas-x7k2).
# ------------------------------------------------------------------
ADMIN_PATH = "/" + os.environ.get("ADMIN_PATH", "admin").strip("/")

# ------------------------------------------------------------------
# Conexión a MySQL (base: alas_del_viento)
# Los datos se leen de variables de entorno; los valores por defecto
# son solo para desarrollo local.
# ------------------------------------------------------------------
# Parámetros de conexión. "cursorclass": DictCursor hace que cada fila sea un dict,
# así en las plantillas se accede como e.nombre, e.fecha_inicio, etc.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME", "alas_del_viento"),
    "charset": "utf8mb4",
    "cursorclass": (pymysql.cursors.DictCursor if pymysql else None),
}

# Imagen que se usa cuando el evento se crea sin URL de imagen
IMAGEN_POR_DEFECTO = (
    "/static/img/WhatsApp Image 2026-11-05 at 18.58.41.jpeg"
)

# LUGAR CORTO (visible) a partir del LUGAR LARGO (para Maps)
# `lugar` (largo) se guarda para Google Maps; `lugar_corto` es el texto visible.
# Si el lugar no está en este diccionario, lugar_corto = lugar.
MAPPING_LUGAR_CORTO = {
    "General Alvear Mendoza": "General Alvear",
    "Bowen General Alvear Mendoza": "Bowen",
    "San Pedro del Atuel General Alvear Mendoza": "San Pedro del Atuel",
    "Alvear Oeste General Alvear Mendoza": "Alvear Oeste",
}


# SALAS disponibles. Un evento puede pertenecer a varias; se guardan juntas, separadas por coma,
# en la columna `tipo` de la tabla `eventos` (ej. "Mini Alas, Orquesta Bach").
# Deben coincidir con las casillas del modal (_modal_nuevo_evento.html) y con index.html.
SALAS_VALIDAS = [
    "Mini Alas",
    "Minisinfónicos",
    "Orquesta Bach",
    "Orquesta Vivaldi",
    "Filarmónica/Avanzados",
]


def get_db_connection():
    """Abre una conexión nueva a la base de datos si pymysql está disponible."""
    if pymysql is None:
        raise Exception("El paquete pymysql no está disponible en este entorno.")
    return pymysql.connect(**DB_CONFIG)


# ------------------------------------------------------------------
# FILTRO JINJA
# ------------------------------------------------------------------
# Se usa en las plantillas así: {{ e.fecha_inicio | format_date }}
@app.template_filter("format_date")
def format_date_filter(value):
    """Convierte la fecha (YYYY-MM-DD o date de MySQL) a DD-MM-YYYY."""
    try:
        if isinstance(value, (date, datetime)):
            return value.strftime("%d-%m-%Y")
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return value  # Devuelve el valor original si hay un error


# Filtro para mostrar el campo `created_at` (datetime de MySQL) como DD-MM-YYYY HH:MM
@app.template_filter("format_datetime")
def format_datetime_filter(value):
    try:
        return value.strftime("%d-%m-%Y %H:%M")
    except AttributeError:
        return value


# ------------------------------------------------------------------
# VERSIÓN SEGÚN EL LINK
# ------------------------------------------------------------------
@app.context_processor
def inyectar_rol():
    """Hace que la variable `es_admin` esté disponible en TODAS las plantillas.
    Es True solo cuando la URL visitada empieza con el prefijo de administrador
    (ADMIN_PATH). index.html usa esa variable para mostrar u ocultar el botón
    "Nuevo Evento", el enlace al dashboard, etc."""
    ruta = request.path
    return {"es_admin": ruta == ADMIN_PATH or ruta.startswith(ADMIN_PATH + "/"),
            "admin_path": ADMIN_PATH}


def volver_admin():
    """Después de guardar (o rechazar) un evento, vuelve a la página de administrador desde la
    que se envió el formulario: el dashboard (campo `desde_dashboard`) o la página principal."""
    if request.form.get("desde_dashboard"):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("admin_home"))


def volver_inicio(ancla=""):
    """Redirige a la página principal conservando la versión desde la que se envió el
    formulario (el formulario de index.html manda `desde_admin` cuando es la versión admin)."""
    destino = url_for("admin_home") if request.form.get("desde_admin") else url_for("index")
    return redirect(destino + ancla)


# ------------------------------------------------------------------
# ALMACENAMIENTO EN MEMORIA / LOCAL STORAGE DE EVENTOS
# ------------------------------------------------------------------
EVENTOS_FILE = os.path.join(os.path.dirname(__file__), "eventos_storage.json")


def cargar_eventos_memoria():
    if os.path.exists(EVENTOS_FILE):
        try:
            with open(EVENTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Aviso al cargar eventos de memoria:", e)

    # 3 eventos institucionales provistos
    eventos_iniciales = [
        {
            "id": 1,
            "nombre": "Concierto: Coro, Guitarra y Piano",
            "descripcion": "Presentación especial de fin de año de los ensambles de Coro, Guitarra y Piano de la institución en el Polo Educativo - IES.",
            "tipo": "Coro, Guitarra y Piano",
            "fecha_inicio": "2026-11-27",
            "fecha_fin": "2026-11-27",
            "hora": "20:00",
            "costo": "0",
            "lugar": "General Alvear Mendoza",
            "lugar_corto": "General Alvear",
            "direccion": "RN 188 y Silvio Tricherri, Polo Educativo - IES",
            "imagen": "/static/img/evento_coro_guitarra_piano.jpg"
        },
        {
            "id": 2,
            "nombre": "Acordes de Navidad - La música que nos abraza",
            "descripcion": "Gran concierto navideño bajo el lema 'La música que nos abraza', interpretado conjuntamente por la Orquesta Vivaldi y la Orquesta Bach.",
            "tipo": "Orquesta Vivaldi, Orquesta Bach",
            "fecha_inicio": "2026-11-28",
            "fecha_fin": "2026-11-28",
            "hora": "20:30",
            "costo": "8000",
            "lugar": "General Alvear Mendoza",
            "lugar_corto": "General Alvear",
            "direccion": "Escuela Carlos María de Alvear",
            "imagen": "/static/img/evento_acordes_navidad.jpg"
        },
        {
            "id": 3,
            "nombre": "Miniorquesta en Concierto",
            "descripcion": "Concierto de fin de año de la Miniorquesta con repertorio festivo y familiar en la Escuela Carlos María.",
            "tipo": "Mini Alas",
            "fecha_inicio": "2026-12-03",
            "fecha_fin": "2026-12-03",
            "hora": "20:30",
            "costo": "8000",
            "lugar": "General Alvear Mendoza",
            "lugar_corto": "General Alvear",
            "direccion": "Escuela Carlos María de Alvear",
            "imagen": "/static/img/evento_miniorquesta.jpg"
        }
    ]
    try:
        with open(EVENTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(eventos_iniciales, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Aviso al guardar eventos iniciales:", e)
    return eventos_iniciales


def guardar_evento_memoria(nombre, descripcion, tipo, fecha_inicio, fecha_fin, hora, costo, lugar, lugar_corto, direccion, imagen):
    global EVENTOS_STORAGE
    nuevo_id = max([e.get("id", 0) for e in EVENTOS_STORAGE], default=0) + 1
    nuevo = {
        "id": nuevo_id,
        "nombre": nombre,
        "descripcion": descripcion,
        "tipo": tipo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "hora": hora,
        "costo": costo,
        "lugar": lugar,
        "lugar_corto": lugar_corto,
        "direccion": direccion,
        "imagen": imagen
    }
    EVENTOS_STORAGE.append(nuevo)
    EVENTOS_STORAGE.sort(key=lambda x: (x.get("fecha_inicio", ""), x.get("hora", "")))
    try:
        with open(EVENTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(EVENTOS_STORAGE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Aviso al guardar evento en storage:", e)
    return nuevo


EVENTOS_STORAGE = cargar_eventos_memoria()


# ------------------------------------------------------------------
# PÁGINA PRINCIPAL -> lista de eventos desde la tabla `eventos` o storage
# ------------------------------------------------------------------
def leer_eventos():
    """Lee todos los eventos de la tabla `eventos` (los más próximos primero).
    Si MySQL no responde o no devuelve filas, utiliza el almacenamiento local (EVENTOS_STORAGE)."""
    eventos = []
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM eventos ORDER BY fecha_inicio ASC, hora ASC")
            eventos = cursor.fetchall()
    except Exception as error:
        print("Aviso al leer los eventos de MySQL (usando storage local):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass
    if eventos:
        return eventos
    return EVENTOS_STORAGE


# Versión PÚBLICA: link normal
@app.route("/")
def index():
    return render_template("index.html", eventos=leer_eventos())


# Versión ADMINISTRADOR: mismo index.html, pero es_admin=True (por la URL) muestra el
# botón "Nuevo Evento" y el acceso al dashboard
@app.route(ADMIN_PATH)
def admin_home():
    return render_template("index.html", eventos=leer_eventos())


# ------------------------------------------------------------------
# DETALLE DE UN EVENTO
# ------------------------------------------------------------------
@app.route("/evento/<int:event_id>")
def evento_detalle(event_id):
    evento = None
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            # Consulta parametrizada (%s): evita inyección SQL. fetchone() devuelve un solo evento o None
            cursor.execute("SELECT * FROM eventos WHERE id = %s", (event_id,))
            evento = cursor.fetchone()
    except Exception as error:
        print("Aviso al leer evento de MySQL (buscando en storage local):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    if not evento:
        evento = next((e for e in EVENTOS_STORAGE if e.get("id") == event_id), None)

    # Si el id no existe ni en la base ni en storage, responde 404
    if not evento:
        return "Evento no encontrado", 404
    return render_template("evento.html", evento=evento)


# ------------------------------------------------------------------
# NUEVO EVENTO -> tabla `eventos`
# ------------------------------------------------------------------
# Solo existe bajo el prefijo de administrador: la versión pública no tiene esta ruta
@app.route(ADMIN_PATH + "/agregar_evento", methods=["POST"])
def agregar_evento():
    # Lectura de los campos del modal "Nuevo Evento" (index.html). .strip() quita espacios sobrantes;
    # "or ''" evita errores si el campo no llega en el formulario
    nombre = (request.form.get("nombre") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()
    # Salas marcadas (si se envían). Si no se seleccionan salas, se asigna "General".
    salas_marcadas = {x.strip() for x in request.form.getlist("salas")}
    tipo = ", ".join(sala for sala in SALAS_VALIDAS if sala in salas_marcadas)
    if not tipo:
        tipo = (request.form.get("tipo") or "").strip() or "General"

    fecha_inicio = (request.form.get("fecha_inicio") or "").strip()
    fecha_fin = (request.form.get("fecha_fin") or "").strip()
    hora = (request.form.get("hora") or "").strip()
    # Si el costo viene vacío o con 0 se guarda "0" (en la interfaz se muestra como "Gratis")
    costo_raw = (request.form.get("costo") or "").strip()
    if not costo_raw or costo_raw == "0" or costo_raw.lower() == "gratis":
        costo = "0"
    else:
        try:
            val_costo = float(costo_raw)
            costo = "0" if val_costo <= 0 else (str(int(val_costo)) if val_costo.is_integer() else costo_raw)
        except ValueError:
            costo = costo_raw

    # LUGAR LARGO PARA MAPS y LUGAR CORTO (visible)
    # El <select> envía el lugar LARGO (para Maps); de él se obtiene el corto con el mapeo de arriba
    lugar = (request.form.get("lugar") or "").strip()
    lugar_corto = MAPPING_LUGAR_CORTO.get(lugar, lugar)

    direccion = (request.form.get("direccion") or "").strip()
    imagen = (request.form.get("imagen") or "").strip() or IMAGEN_POR_DEFECTO

    # Validación básica en el servidor
    # Validación en el servidor (por si se saltean la validación del navegador)
    if not all([nombre, fecha_inicio, fecha_fin, hora, lugar]):
        flash("Completá todos los campos obligatorios del evento.", "warning")
        # Vuelve a la página principal de administrador; el mensaje flash se muestra arriba (alert de Bootstrap)
        return volver_admin()

    try:
        # Convierte los textos YYYY-MM-DD a fechas reales para poder compararlas
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        flash("Las fechas del evento no son válidas.", "warning")
        return volver_admin()

    # La fecha de fin no puede ser anterior a la de inicio
    if fin < inicio:
        flash("La fecha de fin no puede ser anterior a la fecha de inicio.", "warning")
        return volver_admin()

    # Guardar siempre en storage local
    guardar_evento_memoria(nombre, descripcion, tipo, fecha_inicio, fecha_fin, hora,
                           costo, lugar, lugar_corto, direccion, imagen)

    # Intento opcional en MySQL si está disponible
    sql = """
        INSERT INTO eventos
            (nombre, descripcion, tipo, fecha_inicio, fecha_fin, hora,
             costo, lugar, lugar_corto, direccion, imagen)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    valores = (nombre, descripcion, tipo, fecha_inicio, fecha_fin, hora,
               costo, lugar, lugar_corto, direccion, imagen)

    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
        conexion.commit()
    except Exception as error:
        if conexion:
            try:
                conexion.rollback()
            except Exception:
                pass
        print("Aviso: MySQL no disponible para evento (se guardó en storage local):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    flash("¡Evento guardado con éxito!", "success")
    return volver_admin()


# ------------------------------------------------------------------
# ALMACENAMIENTO EN MEMORIA / LOCAL STORAGE DE PREINSCRIPCIONES
# Permite guardar y consultar preinscriptos sin depender obligatoriamente de MySQL.
# ------------------------------------------------------------------
PREINSCRIPCIONES_FILE = os.path.join(os.path.dirname(__file__), "preinscripciones_storage.json")


def cargar_preinscripciones_memoria():
    if os.path.exists(PREINSCRIPCIONES_FILE):
        try:
            with open(PREINSCRIPCIONES_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
                for d in datos:
                    if isinstance(d.get("created_at"), str):
                        try:
                            d["created_at"] = datetime.fromisoformat(d["created_at"])
                        except Exception:
                            d["created_at"] = datetime.now()
                return datos
        except Exception as e:
            print("Aviso al cargar preinscripciones de memoria:", e)

    # Datos demostrativos iniciales de respaldo para visualización inmediata en dashboard
    ahora = datetime.now()
    ejemplos = [
        {
            "id": 1,
            "nombre_apellido": "Sofía Martínez",
            "dni": "48123456",
            "fecha_nacimiento": "2015-06-12",
            "edad": 9,
            "domicilio": "Av. Alvear Oeste 450",
            "email": "sofia.martinez@email.com",
            "telefono": "2625-451234",
            "sala": "Mini Alas",
            "created_at": ahora
        },
        {
            "id": 2,
            "nombre_apellido": "Joaquín Gómez",
            "dni": "47987654",
            "fecha_nacimiento": "2014-03-22",
            "edad": 10,
            "domicilio": "Calle Zeballos 120, Bowen",
            "email": "joaquin.gomez@email.com",
            "telefono": "2625-567890",
            "sala": "Minisinfónicos",
            "created_at": ahora
        },
        {
            "id": 3,
            "nombre_apellido": "Mateo Fernández",
            "dni": "45234567",
            "fecha_nacimiento": "2011-09-18",
            "edad": 13,
            "domicilio": "San Pedro del Atuel s/n",
            "email": "mateo.fernandez@email.com",
            "telefono": "2625-678901",
            "sala": "Orquesta Bach",
            "created_at": ahora
        },
        {
            "id": 4,
            "nombre_apellido": "Lucía Morales",
            "dni": "43567890",
            "fecha_nacimiento": "2009-11-05",
            "edad": 15,
            "domicilio": "Paso de los Andes 320",
            "email": "lucia.morales@email.com",
            "telefono": "2625-789012",
            "sala": "Orquesta Vivaldi",
            "created_at": ahora
        },
        {
            "id": 5,
            "nombre_apellido": "Valentín Castro",
            "dni": "42112233",
            "fecha_nacimiento": "2007-04-14",
            "edad": 17,
            "domicilio": "Ruta 188 km 22",
            "email": "valentin.castro@email.com",
            "telefono": "2625-890123",
            "sala": "Filarmónica/Avanzados",
            "created_at": ahora
        }
    ]
    return ejemplos


def guardar_preinscripcion_memoria(nombre_apellido, dni, fecha_nacimiento, edad, domicilio, email, telefono, sala):
    global PREINSCRIPCIONES_STORAGE
    nuevo_id = max([p.get("id", 0) for p in PREINSCRIPCIONES_STORAGE], default=0) + 1
    nuevo = {
        "id": nuevo_id,
        "nombre_apellido": nombre_apellido,
        "dni": dni,
        "fecha_nacimiento": fecha_nacimiento,
        "edad": edad,
        "domicilio": domicilio,
        "email": email,
        "telefono": telefono,
        "sala": sala,
        "created_at": datetime.now()
    }
    PREINSCRIPCIONES_STORAGE.insert(0, nuevo)
    try:
        datos_guardar = []
        for p in PREINSCRIPCIONES_STORAGE:
            item = dict(p)
            c_at = item.get("created_at")
            item["created_at"] = c_at.isoformat() if isinstance(c_at, (datetime, date)) else str(c_at)
            datos_guardar.append(item)
        with open(PREINSCRIPCIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(datos_guardar, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Aviso al guardar preinscripción en memoria:", e)
    return nuevo


PREINSCRIPCIONES_STORAGE = cargar_preinscripciones_memoria()


# ------------------------------------------------------------------
# PREINSCRIPCIÓN -> tabla `preinscripciones` y storage en memoria
# ------------------------------------------------------------------
# Recibe el formulario del modal de preinscripción (index.html, campos con el mismo name que aquí)
@app.route("/preinscripcion", methods=["POST"])
def preinscripcion():
    # Lectura de los campos del formulario de preinscripción
    nombre_apellido = (request.form.get("nombre_apellido") or "").strip()
    dni = (request.form.get("dni") or "").strip()
    fecha_nacimiento = (request.form.get("fecha_nacimiento") or "").strip()
    edad = (request.form.get("edad") or "").strip()
    domicilio = (request.form.get("domicilio") or "").strip()
    email = (request.form.get("email") or "").strip()
    telefono = (request.form.get("telefono") or "").strip()
    sala = (request.form.get("sala") or "").strip()

    # Validación básica en el servidor
    # Validación en el servidor: todos los campos son obligatorios
    if not all([nombre_apellido, dni, fecha_nacimiento, edad,
                domicilio, email, telefono, sala]):
        flash("Por favor completá todos los campos de la preinscripción.", "warning")
        # Redirige a la sección de oferta educativa usando el ancla #oferta-educativa
        return volver_inicio("#oferta-educativa")

    try:
        # La edad llega como texto; se convierte a entero para la columna INT de la tabla
        edad = int(edad)
    except ValueError:
        flash("La edad debe ser un número válido.", "warning")
        return volver_inicio("#oferta-educativa")

    # Guardar siempre en almacenamiento en memoria / storage local
    guardar_preinscripcion_memoria(
        nombre_apellido, dni, fecha_nacimiento, edad,
        domicilio, email, telefono, sala
    )

    # Intento opcional en MySQL si está disponible (sin fallar si MySQL no está activa)
    sql = """
        INSERT INTO preinscripciones
            (nombre_apellido, dni, fecha_nacimiento, edad,
             domicilio, email, telefono, sala)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    valores = (nombre_apellido, dni, fecha_nacimiento, edad,
               domicilio, email, telefono, sala)

    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
        conexion.commit()
    except Exception as error:
        if conexion:
            try:
                conexion.rollback()
            except Exception:
                pass
        print("Aviso: MySQL no disponible para preinscripción (se guardó en memoria/storage):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    flash("¡Preinscripción enviada con éxito! Nos pondremos en contacto con vos.", "success")
    return volver_inicio("#oferta-educativa")


# ------------------------------------------------------------------
# DASHBOARD DEL ADMINISTRADOR -> registros de `preinscripciones`
# Orden de la página: navbar -> tabla -> tarjetas de resumen (al fondo)
# La tabla muestra primero los 5 más recientes; "Ver más" despliega los 10 de la página
# y, si hay más de 10, el resto se reparte en otras páginas de 10 (paginación).
# ------------------------------------------------------------------
PREINSCRIPTOS_RESUMIDOS = 5      # filas visibles al entrar a la tabla
PREINSCRIPTOS_POR_PAGINA = 10    # filas por página al hacer "Ver más"


@app.route(ADMIN_PATH + "/dashboard")
def admin_dashboard():
    # Filtros opcionales (vienen por la URL: ?q=...&sala=...&pagina=2)
    q = (request.args.get("q") or "").strip()
    sala = (request.args.get("sala") or "").strip()
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        pagina = 1

    preinscriptos_db = None
    por_sala_db = None
    total_filtrado_db = 0

    # Intento de lectura desde MySQL
    conexion = None
    try:
        conexion = get_db_connection()
        condiciones, params = [], []
        if q:
            # Se escapan % y _ para que el texto buscado se tome literal
            patron = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            condiciones.append("(nombre_apellido LIKE %s OR dni LIKE %s OR email LIKE %s "
                               "OR telefono LIKE %s OR domicilio LIKE %s)")
            params += [patron] * 5
        if sala:
            condiciones.append("sala = %s")
            params.append(sala)
        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        with conexion.cursor() as cursor:
            # Cantidad por sala, sin filtros (alimenta las tarjetas y el selector de sala)
            cursor.execute("SELECT sala, COUNT(*) AS cantidad FROM preinscripciones "
                           "GROUP BY sala ORDER BY sala")
            por_sala_db = [(f["sala"], f["cantidad"]) for f in cursor.fetchall()]

            # Cuántos registros cumplen los filtros (para calcular las páginas)
            cursor.execute("SELECT COUNT(*) AS n FROM preinscripciones " + where, params)
            total_filtrado_db = cursor.fetchone()["n"]

            total_paginas = max(1, -(-total_filtrado_db // PREINSCRIPTOS_POR_PAGINA))
            pag_val = min(pagina, total_paginas)

            # Los más recientes primero; LIMIT/OFFSET traen solo la página pedida
            cursor.execute("SELECT * FROM preinscripciones " + where +
                           " ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
                           params + [PREINSCRIPTOS_POR_PAGINA,
                                     (pag_val - 1) * PREINSCRIPTOS_POR_PAGINA])
            preinscriptos_db = cursor.fetchall()
    except Exception as error:
        print("Aviso al leer las preinscripciones de MySQL (usando memoria):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    if preinscriptos_db is not None and len(preinscriptos_db) > 0:
        preinscriptos = preinscriptos_db
        por_sala = por_sala_db or []
        total_filtrado = total_filtrado_db
    else:
        # Fallback a almacenamiento en memoria / storage
        # 1. Conteo total por sala (sin filtros)
        conteos = {}
        for p in PREINSCRIPCIONES_STORAGE:
            s = p.get("sala") or "Sin asignar"
            conteos[s] = conteos.get(s, 0) + 1
        por_sala = sorted(list(conteos.items()), key=lambda x: x[0])

        # 2. Filtrado
        filtrados = PREINSCRIPCIONES_STORAGE
        if q:
            q_lower = q.lower()
            filtrados = [
                p for p in filtrados
                if q_lower in str(p.get("nombre_apellido", "")).lower()
                or q_lower in str(p.get("dni", "")).lower()
                or q_lower in str(p.get("email", "")).lower()
                or q_lower in str(p.get("telefono", "")).lower()
                or q_lower in str(p.get("domicilio", "")).lower()
            ]
        if sala:
            filtrados = [p for p in filtrados if p.get("sala") == sala]

        total_filtrado = len(filtrados)
        total_paginas = max(1, -(-total_filtrado // PREINSCRIPTOS_POR_PAGINA))
        pagina = min(pagina, total_paginas)

        offset = (pagina - 1) * PREINSCRIPTOS_POR_PAGINA
        preinscriptos = filtrados[offset:offset + PREINSCRIPTOS_POR_PAGINA]

    total_paginas = max(1, -(-total_filtrado // PREINSCRIPTOS_POR_PAGINA))
    desde = (pagina - 1) * PREINSCRIPTOS_POR_PAGINA + 1 if preinscriptos else 0

    return render_template("dashboard.html",
                           preinscriptos=preinscriptos,
                           por_sala=por_sala,
                           total=sum(c for _, c in por_sala),   # total sin filtros
                           total_filtrado=total_filtrado,
                           pagina=pagina, total_paginas=total_paginas,
                           desde=desde,
                           resumidos=PREINSCRIPTOS_RESUMIDOS,
                           q=q, sala=sala,
                           comentarios=leer_comentarios())


# ------------------------------------------------------------------
# ALMACENAMIENTO EN MEMORIA / LOCAL STORAGE DE COMENTARIOS
# Permite guardar y visualizar comentarios sin depender obligatoriamente de MySQL.
# ------------------------------------------------------------------
COMENTARIOS_FILE = os.path.join(os.path.dirname(__file__), "comentarios_storage.json")


def cargar_comentarios_memoria():
    """Carga los comentarios del archivo de respaldo local si existe, o devuelve una lista vacía."""
    if os.path.exists(COMENTARIOS_FILE):
        try:
            with open(COMENTARIOS_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
                for d in datos:
                    if isinstance(d.get("created_at"), str):
                        try:
                            d["created_at"] = datetime.fromisoformat(d["created_at"])
                        except Exception:
                            d["created_at"] = datetime.now()
                return datos
        except Exception as e:
            print("Aviso al cargar comentarios de memoria:", e)
    return []


def guardar_comentario_memoria(texto):
    """Guarda el comentario en la lista en memoria y en el archivo de respaldo local."""
    global COMENTARIOS_STORAGE
    nuevo = {
        "id": len(COMENTARIOS_STORAGE) + 1,
        "comentario": texto,
        "created_at": datetime.now()
    }
    COMENTARIOS_STORAGE.insert(0, nuevo)
    try:
        datos_guardar = [
            {
                "id": c["id"],
                "comentario": c["comentario"],
                "created_at": c["created_at"].isoformat() if isinstance(c["created_at"], (datetime, date)) else str(c["created_at"])
            }
            for c in COMENTARIOS_STORAGE
        ]
        with open(COMENTARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump(datos_guardar, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Aviso al guardar comentario en memoria:", e)
    return nuevo


COMENTARIOS_STORAGE = cargar_comentarios_memoria()


# ------------------------------------------------------------------
# COMENTARIOS -> tabla `comentarios` y storage en memoria
# Los envía el menú "Comentarios" de index.html con fetch (JSON); responde JSON:
#   {"ok": true}  si se guardó  |  {"ok": false, "error": "..."} si hubo un problema
# ------------------------------------------------------------------
COMENTARIO_MAX = 100   # largo máximo; coincide con VARCHAR(100) de la tabla


@app.route("/comentario", methods=["POST"])
def comentario():
    datos = request.get_json(silent=True) or {}
    # " ".join(split()) quita espacios sobrantes y saltos de línea
    texto = " ".join(str(datos.get("comentario") or "").split())

    # Validación en el servidor (el navegador también limita, pero no es suficiente)
    if not texto:
        return jsonify(ok=False, error="Escribí un comentario antes de enviar."), 400
    if len(texto) > COMENTARIO_MAX:
        return jsonify(ok=False, error="El comentario es demasiado largo."), 400

    # Se guarda siempre en almacenamiento en memoria / storage local
    guardar_comentario_memoria(texto)

    # Intento opcional en base de datos si está disponible (sin fallar si MySQL no está activa)
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            cursor.execute("INSERT INTO comentarios (comentario) VALUES (%s)", (texto,))
        conexion.commit()
    except Exception as error:
        if conexion:
            try:
                conexion.rollback()
            except Exception:
                pass
        print("Aviso: MySQL no disponible para comentarios (se conservó en memoria/storage):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    return jsonify(ok=True)


# ------------------------------------------------------------------
# COMENTARIOS PARA EL DASHBOARD -> lee de MySQL o almacenamiento en memoria
# ------------------------------------------------------------------
def leer_comentarios():
    """Lee todos los comentarios (los más recientes primero).
    Intenta leer de MySQL; si falla o no hay registros en la base, recurre al almacenamiento en memoria."""
    comentarios = []
    conexion = None
    try:
        conexion = get_db_connection()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, comentario, created_at FROM comentarios "
                           "ORDER BY created_at DESC, id DESC")
            comentarios = cursor.fetchall()
    except Exception as error:
        print("Aviso al leer comentarios de MySQL (usando memoria):", error)
    finally:
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass

    if comentarios:
        return comentarios
    return COMENTARIOS_STORAGE


# Solo se ejecuta al correr `python app.py` (servidor de desarrollo en http://127.0.0.1:5000).
# debug=True es solo para desarrollo: desactivarlo en producción.
if __name__ == "__main__":
    app.run(debug=True)