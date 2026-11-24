# Alas del Viento · Especificaciones del proyecto

> Documento de referencia para recordar cómo está armado el proyecto cada vez que se trabaje en él. Refleja el estado real del código (`app.py` y las plantillas de `templates/`).

## 1. Descripción general

Aplicación web de **agenda de eventos** de la escuela musical Alas del Viento, de General Alvear (Mendoza, Argentina). Muestra los eventos en tarjetas con filtro por **sala**, tiene una página de detalle por evento, una sección de **oferta educativa** con formulario de **preinscripción**, y una **versión de administrador** (sin usuario ni contraseña) para cargar eventos y ver los preinscriptos.

- **Título visible del sitio:** "Alas del Viento" (la pestaña de la página principal dice "Alas del Viento - Tu Agenda").
- **Base de datos:** MySQL, nombre `alas_del_viento`, tablas `eventos` y `preinscripciones`.
- **Idioma de la interfaz y del código (comentarios, variables, campos):** español.

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje backend | Python 3 |
| Framework backend | Flask (plantillas Jinja2) |
| Base de datos | MySQL (InnoDB, `utf8mb4` / `utf8mb4_unicode_ci`) |
| Driver BD | `pymysql` (con `pymysql.cursors.DictCursor`: cada fila es un `dict`) |
| Frontend | HTML5 + CSS + JavaScript vanilla |
| UI | Bootstrap 5.3.2, Font Awesome 6.4.0 (todas las páginas); Bootstrap Icons 1.13.1 (solo `index.html`). Todo por CDN |
| Servidor de desarrollo | `app.run(debug=True)` |

## 3. Estructura de archivos

```
proyecto/
├── app.py                      # Aplicación Flask (rutas, filtros, acceso a MySQL)
├── eventos.py                  # HEREDADO: lista de eventos en memoria; app.py ya NO lo importa
├── ESPECIFICACIONES.md         # Este documento
├── .gitignore
├── __pycache__/
├── assets/                     # Fotos .jpeg del equipo (las páginas usan URLs de GitHub, no esta carpeta)
└── templates/
    ├── index.html              # Página principal (pública y admin): hero, oferta educativa, eventos, modales
    ├── dashboard.html          # Dashboard admin: tabla de preinscriptos + resumen
    ├── _modal_nuevo_evento.html# Parcial: modal "Nuevo Evento" (lo incluyen index.html y dashboard.html)
    └── evento.html             # Detalle de un evento
```

## 4. Dos versiones del sitio (según el link)

No hay login. La versión depende de la **URL** que se abra:

| Link | Versión | Qué muestra |
|---|---|---|
| `/` | Pública | Sitio normal, sin botón "Nuevo Evento" ni dashboard |
| `/admin` | Administrador | El mismo `index.html` + botón "Nuevo Evento" + enlace "Dashboard" + "Ver versión pública" |
| `/admin/dashboard` | Administrador | Tabla de preinscriptos, filtros, paginación y tarjetas de resumen; también tiene el botón "Nuevo Evento" |

- El prefijo `/admin` se cambia con la variable de entorno `ADMIN_PATH` (ej. `ADMIN_PATH=panel-alas-x7k2` → `/panel-alas-x7k2`). Internamente: `ADMIN_PATH = "/" + valor.strip("/")`.
- Un *context processor* (`inyectar_rol`) inyecta en **todas** las plantillas `es_admin` (True si la ruta es `ADMIN_PATH` o empieza con `ADMIN_PATH + "/"`) y `admin_path`.
- `/evento/<id>` y `/preinscripcion` están fuera del prefijo admin, por lo que ahí `es_admin` es siempre False.
- **La única protección es que el link sea secreto.** La ruta `agregar_evento` y el dashboard solo existen bajo el prefijo admin.

## 5. Base de datos

El código no crea las tablas: hay que ejecutar este script antes de arrancar la app.

```sql
CREATE DATABASE alas_del_viento;
USE alas_del_viento;

CREATE TABLE IF NOT EXISTS eventos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(100) NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    hora VARCHAR(10) NOT NULL,
    costo VARCHAR(50) DEFAULT '0',
    lugar VARCHAR(255) NOT NULL,
    lugar_corto VARCHAR(255),
    direccion VARCHAR(255),
    imagen TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS preinscripciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_apellido VARCHAR(255) NOT NULL,
    dni VARCHAR(50) NOT NULL,
    fecha_nacimiento VARCHAR(50) NOT NULL,
    edad INT NOT NULL,
    domicilio VARCHAR(255) NOT NULL,
    email VARCHAR(150) NOT NULL,
    telefono VARCHAR(50) NOT NULL,
    sala VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Campos de `eventos`

| Campo | Significado |
|---|---|
| `nombre` | Nombre del evento (obligatorio) |
| `descripcion` | Texto libre; si no se completa se guarda como texto vacío |
| `tipo` | **Salas** del evento, unidas con `", "` (ej. `Mini Alas, Orquesta Bach`). Un evento puede tener varias. Máximo posible con las 5 salas: 81 caracteres (entra en `VARCHAR(100)`) |
| `fecha_inicio` / `fecha_fin` | `DATE` (formato `YYYY-MM-DD`); `fecha_fin` no puede ser anterior a `fecha_inicio` |
| `hora` | Texto `HH:MM` (viene del `<input type="time">`) |
| `costo` | Texto; si el formulario viene vacío se guarda `"0"`. `"0"` o `""` se muestra como "Gratis" |
| `lugar` | Texto **largo**, pensado para Google Maps (ej. `Bowen General Alvear Mendoza`) |
| `lugar_corto` | Texto **corto** visible (ej. `Bowen`); se calcula en el servidor con `MAPPING_LUGAR_CORTO` |
| `direccion` | Calle y número o ruta; opcional (texto vacío si no se completa) |
| `imagen` | URL; si no se envía se usa `IMAGEN_POR_DEFECTO` (`multievento.png` en GitHub) |
| `created_at` | Fecha de carga (automática) |

### Campos de `preinscripciones`

`nombre_apellido`, `dni`, `fecha_nacimiento` (texto `YYYY-MM-DD`; se muestra como `DD-MM-YYYY`), `edad` (entero), `domicilio`, `email`, `telefono`, `sala` (texto libre, ver sección 7.1), `created_at` (automática).

## 6. Backend (`app.py`)

### 6.1 Configuración (variables de entorno)

| Variable | Uso | Valor por defecto (solo desarrollo) |
|---|---|---|
| `SECRET_KEY` | Clave de Flask (necesaria para `flash()`) | `cambiar-esta-clave-en-produccion` |
| `ADMIN_PATH` | Prefijo del link de administrador | `admin` |
| `DB_HOST` | Host de MySQL | `localhost` |
| `DB_USER` | Usuario | `root` |
| `DB_PASSWORD` | Contraseña | `root` |
| `DB_NAME` | Base de datos | `alas_del_viento` |

`DB_CONFIG` también fija `charset=utf8mb4` y `cursorclass=DictCursor`. `get_db_connection()` abre una conexión nueva por consulta y cada ruta la cierra en un `finally`.

### 6.2 Constantes

- `IMAGEN_POR_DEFECTO`: URL de `multievento.png` (repo `silviorosas/app-eventos` en GitHub).
- `MAPPING_LUGAR_CORTO` (si el valor no está, `lugar_corto = lugar`):

| `lugar` (largo, valor del `<select>`) | `lugar_corto` |
|---|---|
| General Alvear Mendoza | General Alvear |
| Bowen General Alvear Mendoza | Bowen |
| San Pedro del Atuel General Alvear Mendoza | San Pedro del Atuel |
| Alvear Oeste General Alvear Mendoza | Alvear Oeste |

- `SALAS_VALIDAS` (deben coincidir con las casillas de `_modal_nuevo_evento.html` y con el filtro de `index.html`): `Mini Alas`, `Minisinfónicos`, `Orquesta Bach`, `Orquesta Vivaldi`, `Filarmónica/Avanzados`.
- `PREINSCRIPTOS_RESUMIDOS = 5` (filas visibles al entrar al dashboard) y `PREINSCRIPTOS_POR_PAGINA = 10`.

### 6.3 Filtros Jinja

- `format_date`: `date`/`datetime` o texto `YYYY-MM-DD` → `DD-MM-YYYY`. Si falla, devuelve el valor original.
- `format_datetime`: `datetime` → `DD-MM-YYYY HH:MM` (se usa con `created_at`). Si falla, devuelve el valor original.

### 6.4 Funciones auxiliares

- `leer_eventos()`: `SELECT * FROM eventos ORDER BY fecha_inicio ASC, hora ASC`. Si la consulta falla, devuelve lista vacía y hace `flash(..., "danger")`.
- `volver_admin()`: tras guardar o rechazar un evento redirige al dashboard (si el formulario trae `desde_dashboard`) o a `admin_home`.
- `volver_inicio(ancla)`: redirige a `admin_home` (si el formulario trae `desde_admin`) o a `index`, agregando el ancla.

### 6.5 Rutas

(con `ADMIN_PATH` por defecto `/admin`)

| Ruta | Método | Función | Descripción |
|---|---|---|---|
| `/` | GET | `index` | Versión pública: `index.html` con `eventos=leer_eventos()` |
| `/admin` | GET | `admin_home` | Mismo `index.html`; `es_admin=True` por la URL |
| `/evento/<int:event_id>` | GET | `evento_detalle` | Detalle del evento (`evento.html`). 404 `"Evento no encontrado"` si no existe; 500 `"Error al consultar la base de datos"` si falla la BD |
| `/admin/agregar_evento` | POST | `agregar_evento` | Crea un evento desde el modal. Solo existe bajo el prefijo admin |
| `/preinscripcion` | POST | `preinscripcion` | Guarda una preinscripción en `preinscripciones` |
| `/admin/dashboard` | GET | `admin_dashboard` | Dashboard de preinscriptos (con filtros y paginación) |

Todas las consultas usan parámetros (`%s`).

### 6.6 `agregar_evento` (detalle)

1. Lee `nombre`, `descripcion`, `fecha_inicio`, `fecha_fin`, `hora`, `costo`, `lugar`, `direccion`, `imagen` (con `.strip()`).
2. Salas: `request.form.getlist("salas")`; descarta valores que no estén en `SALAS_VALIDAS`, respeta el orden de `SALAS_VALIDAS` y las une con `", "` en `tipo`.
3. `costo` vacío → `"0"`. `imagen` vacía → `IMAGEN_POR_DEFECTO`. `lugar_corto = MAPPING_LUGAR_CORTO.get(lugar, lugar)`.
4. Validaciones (flash `warning` y vuelve con `volver_admin()`): son obligatorios `nombre`, `tipo` (al menos una sala), `fecha_inicio`, `fecha_fin`, `hora` y `lugar`; las fechas deben ser válidas (`%Y-%m-%d`); `fecha_fin` no puede ser anterior a `fecha_inicio`.
5. `INSERT` en `eventos`, `commit()`, flash `success` ("¡Evento guardado con éxito!"). Ante error de MySQL: `rollback()` y flash `danger`.

### 6.7 `preinscripcion` (detalle)

1. Lee `nombre_apellido`, `dni`, `fecha_nacimiento`, `edad`, `domicilio`, `email`, `telefono`, `sala`.
2. Todos son obligatorios (flash `warning`); `edad` debe poder convertirse a entero (flash `warning`).
3. `INSERT` en `preinscripciones`; flash `success` o, si falla MySQL, `rollback()` y flash `danger`.
4. Siempre redirige con `volver_inicio("#oferta-educativa")`.

### 6.8 `admin_dashboard` (detalle)

- Parámetros GET: `q` (búsqueda), `sala` (igualdad exacta), `pagina`.
- `q` busca con `LIKE` (escapando `%` y `_`) en `nombre_apellido`, `dni`, `email`, `telefono` y `domicilio`.
- Consultas: cantidad por sala **sin filtros** (`GROUP BY sala`); total filtrado (para calcular páginas); y la página pedida con `ORDER BY created_at DESC, id DESC LIMIT 10 OFFSET ...`. Si la página pedida no existe, se corrige a la última.
- Variables enviadas a `dashboard.html`: `preinscriptos`, `por_sala` (lista de tuplas `(sala, cantidad)`), `total` (sin filtros), `total_filtrado`, `pagina`, `total_paginas`, `desde`, `resumidos`, `q`, `sala`.

## 7. Frontend

### 7.1 `index.html`

1. **Navbar:** logo (imagen incrustada en base64), enlace "Inicio"; solo con `es_admin`: "Dashboard" y "Ver versión pública".
2. **Mensajes flash:** alertas de Bootstrap con la categoría como color (`success`, `warning`, `danger`), descartables.
3. **Hero:** carrusel Bootstrap `#heroCarousel` de 500 px con 4 imágenes de Unsplash, capa de degradado y el texto "Alas del Viento" / "tu agenda".
4. **Oferta educativa** (`#oferta-educativa`): **5 tarjetas escritas a mano en el HTML** (no vienen de la BD), con una imagen de Unsplash de ejemplo en todas:

| Título en la tarjeta | Edad |
|---|---|
| Mini Alas | 0 a 3 años |
| Minifónicos | 4 a 5 años |
| Orquesta Bach | 6 a 10 años |
| Orquesta Vivaldi | 10 años en adelante |
| Filarmónica Músicos avanzados | 13 años en adelante |

   La descripción se recorta a 2 líneas; el enlace "Ver más" aparece solo si el texto desborda y abre `#detalleEducativoModal`. Cada tarjeta tiene un botón "Preinscripción" que abre `#preinscripcionModal`.
5. **Eventos:**
   - Dropdown "Salas" (`#categoryDropdown`) con opciones `data-category`: `todos`, `mini alas`, `minisinfonicos`, `orquesta bach`, `orquesta vivaldi`, `filarmonica/avanzados`.
   - Botón verde "Nuevo Evento" (solo `es_admin`), que abre `#nuevoEventoModal`.
   - Grilla `#eventsContainer`: una columna `.event-card-column` por evento (`{% for e in eventos %}`) con `data-tipo="{{ e.tipo | lower }}"` y `data-fecha="{{ e.fecha_fin }}"`.
   - Cada tarjeta muestra: imagen y cinta "Finalizado"; un badge por sala; fechas (una sola si inicio = fin, si no "inicio al fin") y hora; nombre; descripción (2 líneas); `e.lugar` (el texto **largo**); precio ("Gratis" si `costo` es `"0"` o vacío, si no `$costo`); y botón "Ver más" hacia `/evento/<id>`.
   - Si no hay eventos aparece `#sinEventos` ("Todavía no hay eventos cargados").
6. **Modales:**
   - `#nuevoEventoModal`: solo con `es_admin`, vía `{% include '_modal_nuevo_evento.html' %}`.
   - `#preinscripcionModal`: formulario POST a `/preinscripcion`. Con `es_admin` agrega `<input type="hidden" name="desde_admin" value="1">`. El campo **Sala es un `<input type="text">` libre y obligatorio** (no un `<select>`).
   - `#detalleEducativoModal`: título, edad y descripción completa se rellenan por JS desde la tarjeta elegida; tiene botón "Preinscripción".
7. **Footer fijo** con "Alas del Viento" y redes (Facebook, Instagram, X) con enlaces `#` (sin URL real todavía).

**Colores de badge por sala:**

| Sala (`tipo`) | Clase |
|---|---|
| Mini Alas | `badge-pink` |
| Minisinfónicos | `badge-orange` |
| Orquesta Bach | `badge-blue` |
| Orquesta Vivaldi | `badge-purple` |
| Filarmónica/Avanzados | `badge-magenta` |
| Cualquier otro valor | `bg-primary` |

(`badge-green` está definida en el CSS pero no se usa.)

**JavaScript:**
- `updateEventStatuses()`: agrega la clase `event-finished` (cinta "Finalizado" e imagen oscurecida) a las tarjetas cuya `data-fecha` es anterior a hoy. Se ejecuta al cargar y después de filtrar.
- **Filtro por sala:** separa `data-tipo` por coma y compara **sin tildes** (normalización NFD) con la opción elegida; actualiza el texto del botón a "Salas: …".
- Detección de desborde en la oferta educativa para mostrar "Ver más" y rellenar `#detalleEducativoModal`.
- **No hay scroll infinito** (fue eliminado).

**Variables de color (CSS):** `--primary-blue: #2563eb` · `--primary-cyan: #06b6d4` · `--primary-teal: #14b8a6` · `--dark-blue: #1e40af`.

### 7.2 `_modal_nuevo_evento.html`

Parcial incluido en `index.html` (solo admin) y en `dashboard.html`, para que ambos usen el mismo formulario. Hace `POST` a `url_for('agregar_evento')`. Si el endpoint actual es `admin_dashboard`, agrega `<input type="hidden" name="desde_dashboard" value="1">`. Un script exige marcar al menos una sala (`setCustomValidity("Elegí al menos una sala")` sobre la primera casilla).

### 7.3 `dashboard.html`

- Navbar admin: logo (enlaza a `admin_home`), badge "Administrador", "Inicio (admin)" y "Ver versión pública".
- Título "Preinscripciones" + botón "Nuevo Evento" (abre el modal parcial).
- Filtros por GET: búsqueda `q` ("Buscar por nombre, DNI, email, teléfono o domicilio...") y `<select name="sala">` con "Todas las salas" y las salas que existen en la BD; botón "Buscar" y "Limpiar" (si hay filtros activos).
- Tabla con columnas: #, Nombre y apellido, DNI, Nacimiento, Edad, Domicilio, Email (enlace `mailto:`), Teléfono, Sala (badge `bg-info text-dark`) y "Preinscripto el".
- **Vista resumida:** en la página 1, si hay más de 5 filas, las filas 6 a 10 se ocultan (`.fila-extra d-none`) y un botón "Ver más / Ver menos" las muestra u oculta; el texto "Mostrando X–Y de N (los más recientes primero)" cambia con él.
- **Paginación** (si hay más de 10 resultados): "« Anterior", primera, última, ±2 páginas alrededor de la actual y "…"; conserva `q` y `sala`. En la página 1 queda oculta hasta hacer "Ver más".
- Estados vacíos: "Ningún registro coincide con la búsqueda" y "Todavía no hay preinscripciones".
- **Resumen al fondo:** tarjeta "Total de preinscriptos" y una tarjeta por cada sala con su cantidad (siempre sin filtros).

### 7.4 `evento.html`

- Sin navbar ni footer. `<title>`: `{{ evento.nombre }} - Alvear 365` (ver sección 10).
- Muestra: nombre; **un único badge** con todo el texto de `evento.tipo`; fechas y hora; descripción; `evento.lugar_corto`; `evento.direccion` (si existe); precio ("Gratis" o `$ costo`); imagen.
- **Mapa:** iframe de Google Maps con la búsqueda `direccion + ", " + lugar` (o solo `lugar` si no hay dirección), `https://www.google.com/maps?q=...&output=embed`.
- Tarjeta "Transporte" **fija en el HTML**: Línea La Unión, Línea Iselín y parada de taxis a 200 m.
- Botón "Volver" a `url_for('index')` (siempre la versión pública).

### 7.5 `eventos.py` (heredado)

Lista `eventos` en memoria con 7 eventos de ejemplo del esquema anterior (tipos Música, Arte, Fiesta, Educación, Vendimia, Cine; sin `lugar_corto` ni `direccion`). **`app.py` no lo importa**: hoy los eventos salen únicamente de MySQL.

## 8. Formularios y nombres de campos

**Nuevo evento** (`_modal_nuevo_evento.html`):

| Campo (`name`) | Control | Obligatorio |
|---|---|---|
| `nombre` | text | Sí |
| `descripcion` | textarea | No |
| `salas` (varias casillas con el mismo name) | checkbox × 5 | Al menos una |
| `fecha_inicio` | date | Sí |
| `fecha_fin` | date | Sí |
| `hora` | time | Sí |
| `costo` | number (placeholder `0`) | No (vacío = 0 = gratis) |
| `lugar` | select "Localidad" (valor = lugar largo) | Sí |
| `direccion` | text | No |
| `imagen` | url | No (si falta, imagen por defecto) |
| `desde_dashboard` | hidden (solo desde el dashboard) | — |

**Preinscripción** (`index.html`; todos obligatorios):

| Campo (`name`) | Etiqueta | Control |
|---|---|---|
| `nombre_apellido` | Nombre y Apellido | text |
| `dni` | DNI | number |
| `fecha_nacimiento` | Fecha de Nacimiento | date |
| `edad` | Edad | number (1–120) |
| `domicilio` | Domicilio | text |
| `email` | Email de contacto | email |
| `telefono` | Telefono de contacto | number |
| `sala` | Sala | text (libre) |
| `desde_admin` | — | hidden (solo en versión admin) |

## 9. Estado de la persistencia

La migración a MySQL está **completa**: listar eventos, detalle, agregar evento, guardar preinscripciones y leer preinscripciones desde el dashboard usan la base `alas_del_viento`. Los `id` los asigna `AUTO_INCREMENT`. Los eventos de ejemplo de `eventos.py` ya no se cargan.

## 10. Problemas conocidos / a revisar

1. **Resto del nombre "Alvear 365":** `evento.html` (título de la pestaña). El resto del sitio ya dice "Alas del Viento".
2. **Sala de preinscripción como texto libre:** puede escribirse cualquier cosa y no se valida contra `SALAS_VALIDAS`; el dashboard filtra y cuenta por los valores tal como se guardaron.
3. **Oferta educativa escrita a mano en `index.html`:** títulos distintos de `SALAS_VALIDAS` ("Minifónicos" vs "Minisinfónicos"; "Filarmónica Músicos avanzados" vs "Filarmónica/Avanzados"); la tarjeta de Filarmónica tiene un texto de relleno sobre programación y ofimática; todas las imágenes son una foto de ejemplo ("Sala de ejemplo").
4. **`dni` y `telefono` son `type="number"`:** pueden perder ceros iniciales (hay un TODO en el HTML). Conviene `type="text"` con `inputmode="numeric"`.
5. **`fecha_nacimiento` es `VARCHAR(50)`** en la tabla aunque el formulario envía una fecha; sería mejor `DATE`.
6. **Lugar en la tarjeta:** `index.html` muestra `e.lugar` (el texto largo, ej. "Bowen General Alvear Mendoza"), mientras que `evento.html` muestra `lugar_corto`.
7. **Badges inconsistentes:** `index.html` dibuja un badge de color por sala; `evento.html` muestra todo `tipo` en un único badge azul.
8. **`evento.html`:** el botón "Volver" lleva siempre a la versión pública, no tiene navbar/footer y el bloque de transporte es fijo para todos los eventos.
9. **Sin autenticación:** el panel admin y el dashboard (que muestra DNI, email, teléfono y domicilio) se protegen solo con el link; el valor por defecto `/admin` es fácil de adivinar. Definir `ADMIN_PATH`.
10. **Valores por defecto inseguros:** `SECRET_KEY`, `DB_USER=root` y `DB_PASSWORD=root` están pensados solo para desarrollo; definirlos por variables de entorno en producción.
11. **`debug=True`** en `app.run(...)`: desactivarlo en producción.
12. **Validación incompleta en el servidor:** no se valida el formato de email, DNI, teléfono, fecha de nacimiento ni el rango de edad (solo el navegador); `costo` e `imagen` no se validan.
13. **`eventos.py` sin uso:** se puede borrar o conservar como referencia.
14. **Redes sociales** del footer (`index.html`) apuntan a `#`.

## 11. Cómo ejecutar

```bash
pip install flask pymysql
# Ejecutar antes el script SQL de la sección 5 en MySQL
# (opcional) definir variables: SECRET_KEY, ADMIN_PATH, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
python app.py
# Público:        http://127.0.0.1:5000/
# Administrador:  http://127.0.0.1:5000/admin   (o el valor de ADMIN_PATH)
```

## 12. Convenciones a mantener

- Nombres de variables, campos y comentarios en **español**.
- Fechas guardadas en formato `YYYY-MM-DD`; mostradas como `DD-MM-YYYY` con `format_date` (y `DD-MM-YYYY HH:MM` con `format_datetime`).
- `lugar` (largo, para Maps) y `lugar_corto` (visible) siempre se guardan por separado.
- Las salas se guardan juntas, separadas por coma, en la columna `tipo`; la lista `SALAS_VALIDAS`, las casillas de `_modal_nuevo_evento.html` y el filtro de `index.html` deben mantenerse iguales.
- Consultas SQL siempre parametrizadas (`cursor.execute(sql, params)`).
- Estilos con Bootstrap 5 y la paleta azul/cian/verde azulado definida en `:root`.
- Todo lo exclusivo del administrador cuelga del prefijo `ADMIN_PATH`.