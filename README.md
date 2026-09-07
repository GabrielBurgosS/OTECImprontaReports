# OTEC Impronta Reports

Herramienta de automatización en Python que inicia sesión en la plataforma web de un OTEC (Organismo Técnico de Capacitación), descarga los reportes de participación y notas de los cursos indicados, y genera automáticamente reportes en Excel con el formato final listo para entregar.

Construido para eliminar el trabajo manual repetitivo de: entrar a la plataforma, buscar cada curso, descargar CSVs de participación/notas, y armar planillas finales combinando ambas fuentes.

## Características

- **Descarga automatizada** vía Selenium: login, navegación por curso y descarga de reportes sin intervención manual.
- **Soporte para dos tipos de reporte**:
  - `weekly` (semanal): reporte de participación solo.
  - `final`: combina participación + notas en un único reporte.
- **Generación de nombres de archivo** automática a partir del nombre real del curso y la fecha.
- **Procesamiento de datos** con pandas: limpieza, orden y formato de columnas (nombres, IDs, porcentajes de participación, etc.).
- **Configuración centralizada** en [config.json](config.json) (carpeta de descargas temporales, carpeta de salida, modo headless).
- Manejo de errores por curso: si un curso falla, el resto de la lista sigue procesándose y al final se muestra un resumen.

## Estructura del proyecto

```
main.py                     # Punto de entrada: define los cursos a descargar y dispara el proceso
config.json                 # Configuración (carpetas, modo headless, etc.)
src/
  downloader/                # Automatización con Selenium (login, navegación, descargas, opciones del driver)
  data_process/               # Limpieza y combinación de datos de participación/notas con pandas
  other_functions/            # Utilidades: fechas, manejo de archivos, generación de nombres, conexión a internet
  ui/                          # Prototipo de interfaz gráfica (customtkinter) — en desarrollo, no integrado a main.py
  read_config.py               # Lectura de config.json y variables de entorno
```

## Requisitos

- Python 3.13+
- Google Chrome instalado (el proyecto usa Selenium con ChromeDriver)

## Instalación

```bash
git clone https://github.com/<tu-usuario>/OTECImprontaReports.git
cd OTECImprontaReports
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Configuración

1. Copia `.env.example` a `.env` y completa tus credenciales de la plataforma:

   ```
   OTEC_USERNAME=tu_usuario
   OTEC_PASSWORD=tu_contraseña
   ```

   > `.env` está en `.gitignore`: tus credenciales nunca se suben al repositorio.

2. Ajusta [config.json](config.json) si lo necesitas:

   ```json
   {
     "download-folder": "download_temp",
     "output-folder": "salida",
     "no-ui": true,
     "eager": true
   }
   ```

   - `download-folder`: carpeta temporal donde Selenium descarga los CSV crudos.
   - `output-folder`: carpeta donde se guardan los reportes Excel finales (se crea automáticamente si no existe).
   - `no-ui`: `true` para ejecutar el navegador en modo headless.

## Uso

Edita la lista de cursos a procesar en [main.py](main.py). Cada curso es una tupla `(id_curso, es_reporte_final)`:

```python
download_list = [
    (17, True),   # curso 17: reporte final (participación + notas)
    (20, False),  # curso 20: reporte semanal (solo participación)
]
```

Luego ejecuta:

```bash
python main.py
```

Los reportes generados quedarán en la carpeta configurada en `output-folder` (por defecto, `salida/`).

## Nota sobre datos

Este repositorio no incluye ningún reporte generado, dato de cursos ni credenciales reales: todos los archivos de salida (`*.xlsx`, `*.csv`) y notebooks de prueba están excluidos vía `.gitignore`, ya que corresponden a información real de participantes de los cursos.

## Estado del proyecto

Proyecto personal usado en producción para automatizar la generación de reportes de una OTEC real. El módulo de interfaz gráfica (`src/ui`) es un prototipo en desarrollo, aún no integrado al flujo principal.
