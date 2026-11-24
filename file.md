# Documentación de Arquitectura, Stack y Flujo - Orquesta Escuela Alas del Viento

**Rol:** Especialista Senior en Python + Flask + HTML5 + CSS3 + JavaScript.

Este documento formaliza la estructura técnica, componentes y flujo funcional del proyecto de la **Orquesta Escuela Alas del Viento** (General Alvear, Mendoza).

---

## 1. Stack Tecnológico

El proyecto está construido bajo una arquitectura web clásica cliente-servidor, ligera y desacoplada:

### Backend
- **Lenguaje:** Python 3.x
- **Framework Web:** Flask (Microframework WSGI)
- **Motor de Plantillas:** Jinja2 (para renderizado de componentes dinámicos del lado del servidor)
- **Conector de Base de Datos:** `PyMySQL` (`pymysql.cursors.DictCursor` para manipulación de resultados relacionales como diccionarios)
- **Manejo de Fechas y Entorno:** Módulos estándar `datetime`, `os`

### Frontend
- **Estructura y Maquetación:** HTML5 semántico
- **Estilos y Diseño:** CSS3 personalizado con variables CSS (`:root`), gradientes (`bg-blue-gradient`) y diseño responsivo para móviles y escritorio.
- **Framework de Estilos y Componentes:** Bootstrap 5.3.2 (Grid System, Modales, Navbars, Cards, Dropdowns, Badges, Alertas flash)
- **Iconografía:** Bootstrap Icons 1.13.1 y Font Awesome 6.4.0
- **Lógica e Interactividad:** JavaScript moderno (ES6+ vanilla) para:
  - Filtrado reactivo de eventos sin recargar la página.
  - Cálculo dinámico de eventos vencidos/finalizados en base a fecha local (`.event-finished`).
  - Envío asíncrono (`fetch` API) del panel flotante de comentarios hacia `/comentario`.
  - Paginación y búsqueda interactiva en el panel del administrador.

### Base de Datos
- **Motor:** MySQL / MariaDB (Base de datos: `alas_del_viento`)
- **Tablas y Almacenamiento:**
  1. `eventos`: Registro de agenda cultural. Cuenta con almacenamiento híbrido en memoria y persistencia local (`eventos_storage.json`) con respaldo opcional en MySQL.
  2. `preinscripciones`: Registro de aspirantes a la orquesta. Cuenta con almacenamiento híbrido en memoria y persistencia local (`preinscripciones_storage.json`) con respaldo opcional en MySQL.
  3. `comentarios`: Mensajes o sugerencias comunitarias. Cuenta con almacenamiento híbrido en memoria y persistencia local (`comentarios_storage.json`) con respaldo opcional en MySQL.

---

## 2. Flujo Funcional del Sistema

La aplicación cuenta con dos entornos claramente diferenciados: la **Experiencia Pública** y el **Panel de Administración Exclusivo para la Escuela**.

```
[ Usuario Público / ]
       │
       ├───> 1. Hero / Presentación Institucional
       │
       ├───> 2. Oferta Educativa (Salas formativas + Modal de Preinscripción)
       │
       ├───> 3. Agenda de Eventos (Eventos propios y participación institucional + Detalle /evento/<id>)
       │
       └───> 4. Canales de Contacto, Redes y Feedback
       
[ Panel Exclusivo Escuela /admin ]
       │
       ├───> Vista Principal Admin (/admin): Habilita botón "Nuevo Evento"
       │
       └───> Dashboard Exclusivo (http://127.0.0.1:5000/admin/dashboard):
             - Estadísticas y conteo por sala formativa
             - Listado paginado y búsqueda de aspirantes preinscriptos
             - Bandeja de comentarios recibidos
             - Acceso al alta de nuevos eventos
```

### 2.1. Primera Sección: Oferta Educativa de la Institución
La primera sección del portal institucional expone el trayecto formativo musical que brinda la Orquesta Escuela Alas del Viento, organizado por niveles y salas pedagógicas:
- **Mini Alas:** Estimulación musical temprana e iniciación en las infancias.
- **Minisinfónicos:** Primer contacto con la práctica instrumental orquestal y lectura musical básica.
- **Orquesta Bach:** Nivel intermedio para desarrollo técnico-artístico de cuerdas y vientos.
- **Orquesta Vivaldi:** Nivel avanzado que profundiza en repertorio sinfónico y de cámara.
- **Filarmónica / Avanzados:** Músicos consolidados con preparación para carreras superiores y conciertos de alta exigencia.

Cada sala incluye información detallada y un llamado a la acción directo que abre el formulario de **Preinscripción**, el cual persiste los datos en la tabla `preinscripciones`.

### 2.2. Segunda Sección: Eventos que Realiza y en los que Participa la Institución
La sección subsiguiente presenta la agenda viva de presentaciones, galas, festivales comunitarios y conciertos didácticos:
- Muestra tarjetas de eventos con título, fechas, horarios, lugar de presentación y costo de acceso.
- Los eventos finalizados son detectados dinámicamente mediante JavaScript y destacados con la etiqueta "Finalizado".
- Cuenta con filtros por categoría/sala e integración con Google Maps para cada evento individual a través de la ruta `/evento/<id>`.

### 2.3. Dashboard de Administración Exclusivo de la Escuela
Ubicado en la ruta:
**`http://127.0.0.1:5000/admin/dashboard`**
- Proporciona a los directivos y docentes una visión consolidada del ciclo lectivo.
- Permite buscar aspirantes por nombre, DNI, teléfono, email o domicilio, así como filtrar preinscriptos por sala formativa.
- Incluye métricas totales y subtotales por sala.
- Contiene la bandeja de comentarios ciudadanos.
- Ofrece acceso centralizado para dar de alta nuevos eventos culturales mediante el modal interactivo.

---

## 3. Compromiso y Alcance
Con este entendimiento cabal del proyecto, su stack y su flujo, se establece que **la estructura medular, oferta educativa, sección de eventos y dashboard no serán modificados salvo requerimiento o instrucción expresa del usuario**.
