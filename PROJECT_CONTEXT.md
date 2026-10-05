# 📖 Contexto y Arquitectura del Proyecto: Alas del Viento

Este archivo sirve como **fuente de verdad y contexto técnico continuo** para los desarrolladores y la IA. Debe consultarse antes de escalar o implementar nuevas funcionalidades, y **debe actualizarse** tras cada cambio significativo en la arquitectura o en el código.

---

## 📌 1. Información General del Proyecto
* **Nombre:** Alas del Viento - Escuela de Música y Coro
* **Contexto:** Iniciativa cultural y educativa para el Coro y Escuela de Música Alas del Viento de General Alvear (Mendoza, Argentina) y sus distritos. Desarrollado dentro del programa *Conectados por Mendoza Futura (Episodio 4 2026)*.
* **Propósito:** Proporcionar una plataforma integral para la difusión de presentaciones musicales de la institución, inscripción a salas educativas de 0 a 5 años, 6 a 11 años y 12 a 17 años, y gestión de agenda de conciertos y eventos culturales.

---

## 🛠️ 2. Stack Tecnológico Actual

* **Lenguaje principal:** Python 3.12
* **Framework Backend:** Flask `3.0.0`
* **Servidor WSGI Prod:** Gunicorn `21.2.0`
* **Motor de Plantillas:** Jinja2
* **Frontend UI:**
  * HTML5 / CSS3 (Estilos customizados para badges y tarjetas de salas educativas y eventos)
  * Bootstrap `5.3.2` (Grid, Modales de preinscripción y creación de eventos, Dropdowns, Carrusel Hero)
  * Iconos: FontAwesome `6.4.0` y Bootstrap Icons `1.13.1`
  * JavaScript Vanilla (Preinscripción a sala con preselección dinámica, filtros de eventos por categoría en cliente, badge "Finalizado" en fechas pasadas)
* **Persistencia de Datos:** 
  * **Producción (Render):** Base de datos **PostgreSQL** gestionada con **Flask-SQLAlchemy** y **psycopg2-binary** conectada mediante la variable `DATABASE_URL`.
  * **Desarrollo Local:** Base de datos **MySQL** (`alvear365_db`) con **PyMySQL** y fallback de respaldo en memoria.
* **Plataforma de Despliegue Cloud:** **Render** (Web Service + Managed PostgreSQL Database).

---

## 📁 3. Estructura del Directorio

```text
app-eventos/
├── app.py                  # Servidor principal Flask (Modelos Evento y Preinscripcion, Rutas, Filtros)
├── eventos.py              # Datos iniciales de actuaciones del Coro Alas del Viento
├── Procfile                # Comando de ejecución para Gunicorn en Render (web: gunicorn app:app)
├── schema.sql              # Script SQL ejecutable en MySQL Workbench (Crea DB y tablas 'eventos' y 'preinscripciones')
├── init_db.py              # Script Python de migración e inicialización automática (PostgreSQL / MySQL)
├── requirements.txt        # Dependencias Python (Flask, Flask-SQLAlchemy, PyMySQL, psycopg2-binary, gunicorn)
├── requerimientos.txt      # Instrucciones de ejecución en español
├── PROJECT_CONTEXT.md      # Este archivo (Contexto y memoria del proyecto)
├── templates/              # Plantillas Jinja2 HTML
│   ├── index.html          # Vista principal (Hero Carrusel, Oferta Educativa 3 Cards, Formulario Preinscripción, Grilla Eventos)
│   ├── evento.html         # Vista detallada de evento individual con Mapa + Transporte
│   ├── contacto.html       # Página de contacto e información institucional
│   ├── admin_preinscripciones.html # Panel SuperAdmin de Alumnos Preinscriptos (Filtros en tiempo real, KPIs, CSV, Impresión)
│   └── admin_forbidden.html # Pantalla de Acceso Denegado 403 Forbidden con formulario de ingreso de clave
├── static/                 # Archivos estáticos de producción (CSS, JS, Fonts, Img)
└── assets/                 # Recursos multimedia estáticos locales (imágenes, logos)
```

---

## 🔍 4. Mapeo de Rutas y Lógica Existente

### Rutas en `app.py`:
1. `GET /`: Vista principal (`index.html`). Consulta los eventos en MySQL y renderiza la oferta educativa y la agenda cultural.
2. `POST /preinscribir`: Procesa el formulario de preinscripción para las salas de 0 a 5 años, 6 a 11 años y 12 a 17 años, guardando en BD MySQL (o fallback en memoria) y redirigiendo con alerta de éxito.
3. `GET /evento/<int:event_id>`: Vista de detalle (`evento.html`). Busca el evento por ID en la BD MySQL.
4. `POST /agregar_evento`: Recibe el formulario modal, crea una nueva instancia de `Evento(...)` y la persiste en la base de datos MySQL.
5. `GET /contacto`: Renderiza la página de contacto (`contacto.html`).
6. `GET /admin/preinscripciones`: **Ruta secreta de administración**. Consulta todas las preinscripciones ordenadas de forma descendente por fecha (`created_at.desc()`). Requiere autenticación por token en Query Parameter (`?key=alas_admin_2026`) o variable de entorno `ADMIN_SECRET_KEY`, respaldado por sesión segura. Si la clave es errónea o falta, devuelve código HTTP `403 Forbidden` (`admin_forbidden.html`).
7. `GET /admin/logout`: Cierra la sesión activa de administración y redirige al inicio.
8. **Filtro de Plantilla Custom (`format_date`)**: Convierte fechas (`date`, `datetime` o string) al formato argentino `DD-MM-YYYY` (y `DD-MM-YYYY HH:MM` para marcas de tiempo).

---

## 📋 5. Esquema de Base de Datos MySQL

```sql
CREATE TABLE `eventos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `tipo` VARCHAR(100) NOT NULL,
  `fecha_inicio` DATE NOT NULL,
  `fecha_fin` DATE NOT NULL,
  `hora` VARCHAR(10) NOT NULL,
  `costo` VARCHAR(50) DEFAULT '0',
  `lugar` VARCHAR(255) NOT NULL,
  `lugar_corto` VARCHAR(255),
  `direccion` VARCHAR(255),
  `imagen` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `preinscripciones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre_apellido` VARCHAR(255) NOT NULL,
  `dni` VARCHAR(50) NOT NULL,
  `fecha_nacimiento` VARCHAR(50) NOT NULL,
  `edad` INT NOT NULL,
  `domicilio` VARCHAR(255) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `telefono` VARCHAR(50) NOT NULL,
  `sala` VARCHAR(100) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📝 7. Bitácora de Cambios (Changelog)

* **2026-10-05 (Render Deploy)**: Preparación y configuración integral para despliegue en **Render** con base de datos **PostgreSQL**.
  - **Soporte Dual de Base de Datos (`app.py`)**: Detección automática de `DATABASE_URL` para PostgreSQL en Render (con corrección de dialecto `postgres://` a `postgresql://` para SQLAlchemy) y fallback transparente a MySQL local.
  - **Auto-inicialización y sembrado en Render**: Al conectarse por primera vez a PostgreSQL en Render, la aplicación crea automáticamente las tablas `eventos` y `preinscripciones` y siembra los eventos institucionales de la escuela sin requerir migraciones manuales.
  - **Dependencias y Producción**: Incorporación de `psycopg2-binary` en `requirements.txt` y creación de `Procfile` para el servidor WSGI `gunicorn`.
* **2026-10-05**: Implementación del **Panel SuperAdmin de Visualización y Gestión de Preinscripciones**.
  - **Seguridad y Rutas (`app.py`)**: Creación de la ruta administrativa secreta `GET /admin/preinscripciones` protegida mediante validación de clave secreta (`?key=...` o variable de entorno `ADMIN_SECRET_KEY`, por defecto `alas_admin_2026`) y control de sesión `session['admin_authenticated']`. Si la clave es incorrecta o falta, responde con error HTTP `403 Forbidden` renderizando `admin_forbidden.html`.
  - **Consulta SQLAlchemy**: Consulta ordenada descendentemente por `created_at.desc()` sobre el modelo `Preinscripcion`, con fallback robusto en memoria ante eventual desconexión de MySQL.
  - **Plantilla SuperAdmin (`templates/admin_preinscripciones.html`)**:
    - Encabezado institucional con totalizador dinámico de inscriptos, botón de recarga y regreso al portal.
    - 4 tarjetas KPI de resumen estadístico (Total General, 0 a 5 años, 6 a 11 años, 12 a 17 años) con filtrado instantáneo al hacer click.
    - Filtros rápidos en tiempo real (Vanilla JS) por Nombre/DNI y selector por Sala (0 a 5 años, 6 a 11 años, 12 a 17 años).
    - Tabla responsiva con badges diferenciados por sala, enlaces directos para correo (`mailto:`), teléfono (`tel:`) y enlace dinámico de WhatsApp Web.
    - Modal de Ficha Individual de Alumno para visualización detallada de solicitud y contacto directo.
    - Exportación a CSV con codificación UTF-8 BOM (compatible con acentos en Microsoft Excel en español).
    - Soporte completo para impresión en PDF/papel con vista limpia mediante `@media print`.
  - **Mejora del filtro `format_date`**: Soporta objetos `datetime`, `date` y cadenas de texto con o sin hora.
* **2026-08-30**: Transformación integral de la plataforma de eventos a la plataforma oficial para el **Coro y Escuela de Música Alas del Viento** de General Alvear (Mendoza), desarrollado por **Conectados por Mendoza Futura - Episodio 4 2026**.
  - Actualización de marca, header y carrusel hero con 3 imágenes alusivas a coros y orquestas infantiles/juveniles.
  - Implementación de la sección **Oferta Educativa** con 3 cards (Sala de 0 a 5 años, Sala de 6 a 11 años y Sala de 12 a 17 años) con botón "Preinscribirse".
  - Creación del **Formulario Modal de Preinscripción** con los campos: Nombre y Apellido, DNI, Fecha de Nacimiento, Edad, Domicilio, Email, Teléfono de contacto y Select de Sala, integrado con el modelo SQLAlchemy `Preinscripcion`.
  - Configuración de 3 eventos iniciales hardcodeados sobre conciertos y encuentros del Coro Alas del Viento, preservando el scroll infinito y la funcionalidad para agregar nuevos eventos.
  - Actualización del footer institucional y firmas del desarrollador: *Conectados por Mendoza Futura - Episodio 4 2026*.


