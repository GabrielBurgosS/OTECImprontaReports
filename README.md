# OTEC Impronta Reports

Aplicación de escritorio para Windows que entra a la plataforma Moodle de **otecimpronta.cl**, descarga la participación y las notas de los cursos indicados, y genera reportes en Excel **llenando las plantillas de la OTEC**. Las plantillas conservan sus tablas, fórmulas, formato condicional y gráficos.

- **Para usuarios:** [docs/MANUAL_DE_USUARIO.md](docs/MANUAL_DE_USUARIO.md) (también en PDF).
- **Para desarrollo:** este documento.

![Ventana principal](docs/capturas/2_resultados.png)

## Características

- Interfaz gráfica (customtkinter) pensada para personas no técnicas. El trabajo corre en un hilo aparte, se puede cancelar y muestra el progreso.
- Credenciales en el **Administrador de credenciales de Windows** (`keyring`). La contraseña nunca se escribe en disco ni en los logs.
- **Plantillas seleccionables por curso.** Se detecta automáticamente qué columna recibe qué dato; se pueden agregar plantillas propias.
- **Asistencia por curso:** sin asistencia (se eliminan las columnas y su bloque de resumen), Zoom o Presencial.
- Las pruebas de la plataforma se asocian a las columnas de nota de la plantilla. Si hay ambigüedad, se pregunta al usuario y la elección se recuerda por curso.
- **Logs** por ejecución con secretos redactados, capturas de pantalla y HTML cuando Selenium falla, y exportación de un zip de diagnóstico.
- Ejecutable único con PyInstaller y autoprueba de instalación (`--self-test`).

## Arquitectura

```
app.py                         Entrada gráfica (logging, instancia única, --self-test)
main.py                        Entrada por línea de comandos (uso técnico)
src/
  paths.py                     Rutas: recursos empaquetados vs. %LOCALAPPDATA%\OTECImpronta
  settings.py                  settings.json del usuario (sin contraseña)
  credentials.py               Administrador de credenciales de Windows (+ .env como respaldo en desarrollo)
  logging_setup.py             Un log por ejecución, filtro de secretos, excepthooks, cola para la UI
  errors.py                    Errores con mensaje técnico + mensaje para el usuario
  diagnostics.py               Zip de diagnóstico
  selftest.py                  Autoprueba de Excel/plantillas, keyring y Chrome
  core/job.py                  ReportJob: login → nombre → participación → notas → Excel, por curso
  downloader/platform_session.py  Sesión Selenium contra Moodle (carpeta de descarga por ejecución)
  data_process/                Limpieza de CSV (participación, notas 1–7) y CourseData
  report_export/templates.py   Catálogo de plantillas y detección de roles de columna
  report_export/template_writer.py  Llenado de plantillas vía Excel COM (pywin32)
  ui/                          Ventana principal, lista de cursos, diálogos, puente hilo↔UI
assets/plantillas/             Plantillas originales empaquetadas (sin datos)
tests/                         pytest (fixtures anonimizados; tests de Excel se omiten si no hay Excel)
tools/                         Ícono, capturas para el manual, PDF del manual
```

### Decisiones técnicas

- **Excel COM con pywin32 en vez de openpyxl:** openpyxl elimina gráficos, conjuntos de íconos y barras de datos al guardar. Con Excel real, el resultado es idéntico a llenar la plantilla a mano.
- **Sin xlwings:** su `quit()`/`kill()` y su handler de `atexit` llaman a `Apps.cleanup()`, que mata *cualquier* Excel que no pueda enumerar (por ejemplo, uno abierto por el usuario en la pantalla de inicio). `ExcelWriter` crea su propio proceso con `DispatchEx` y solo cierra ese PID. Lo cubre el test `test_other_excel_instances_survive`.
- **Tamaño de la tabla:** se agregan filas con `ListRows.Add` y se eliminan con `ListRows(i).Delete`, porque insertar o borrar celdas falla con filas de totales y desplazaría el panel de resumen.
- **COM en hilos:** `CoInitialize`/`CoUninitialize` solo en hilos secundarios; en el hilo principal desconectaría otros objetos COM.
- **Descargas:** una carpeta por ejecución; una descarga termina cuando aparece un `.csv` nuevo y no queda ningún `.crdownload`.

## Desarrollo

Requisitos: Python 3.13, Google Chrome, Microsoft Excel (para los tests de plantillas).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py          # interfaz gráfica
python main.py         # CLI: edita download_list en main.py
python -m pytest       # tests (los de Excel se omiten si Excel no está instalado)
```

Para desarrollo, las credenciales también se pueden poner en un `.env` (ver `.env.example`); ese archivo está en `.gitignore` y no se empaqueta. Con `OTEC_DATA_DIR=<carpeta>` se usa otra carpeta de datos en lugar de `%LOCALAPPDATA%\OTECImpronta` (los tests lo hacen automáticamente).

## Compilar

```powershell
.\build.ps1              # tests → dist\OTEC Reportes.exe + dist\OTEC Reportes 1.0.0.zip (+ .sha256)
.\build.ps1 -Installer   # versión carpeta + instalador con Inno Setup 6 (installer\OTECReportes.iss)
```

Para regenerar las capturas y el PDF del manual:

```powershell
python tools\screenshot_ui.py docs\capturas light
python tools\build_manual.py
```

### Checklist de versión

1. `.\build.ps1` termina con todos los tests en verde.
2. `"dist\OTEC Reportes.exe" --self-test C:\autoprueba` → `RESULTADO: TODO CORRECTO`.
3. Prueba en vivo con una cuenta real (no se puede automatizar sin credenciales):
   - [ ] Probar conexión con la contraseña correcta, y luego con una incorrecta.
   - [ ] Nombre automático de un curso existente y de uno inexistente.
   - [ ] Un curso con cada plantilla y cada tipo de asistencia; abrir los Excel y revisarlos.
   - [ ] Un curso con varias pruebas (aparece el diálogo de pruebas una sola vez).
   - [ ] Cancelar a mitad de camino; cerrar la ventana mientras trabaja.
   - [ ] Desconectar internet a mitad de camino.
4. Probar el `.exe` en un equipo (o Windows Sandbox) sin Python.

## Nota sobre datos

El repositorio no incluye reportes, datos de cursos ni credenciales. Los `*.xlsx`/`*.csv` están excluidos por `.gitignore`, salvo las plantillas vacías de `assets/plantillas/` y los fixtures **anonimizados** de `tests/fixtures/`.
