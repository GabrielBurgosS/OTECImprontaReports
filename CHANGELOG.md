# Changelog

## 1.0.0 (2026-10-06)

Primera versión con interfaz gráfica.

### Nuevo
- Interfaz gráfica: cuenta, lista de cursos con plantilla y asistencia por curso, carpeta de salida, progreso, cancelación, resultados con botones para abrir los archivos y panel de actividad.
- Nombre del curso obtenido automáticamente de la plataforma y guardado en caché.
- Contraseña guardada en el Administrador de credenciales de Windows, con botón "Probar conexión".
- Plantillas seleccionables (Inicial, Semanal, Participación, Final y Datos completos), llenadas con Excel para conservar gráficos, íconos y fórmulas. Se pueden agregar plantillas propias.
- Asistencia por curso: sin asistencia (se eliminan las columnas y su resumen), Zoom o Presencial.
- Diálogo para elegir qué prueba va en cada columna de nota, recordado por curso.
- Logs por ejecución con contraseña redactada, capturas en caso de error y exportación de diagnóstico.
- Ejecutable único `OTEC Reportes.exe`, manual de usuario en PDF y autoprueba `--self-test`.

### Corregido
- El programa podía quedarse esperando para siempre una descarga o un botón inexistente.
- El inicio de sesión no comprobaba si había funcionado.
- La verificación de internet siempre respondía "conectado".
- El reporte final descartaba sin aviso a quienes estaban en solo uno de los dos CSV.
- ChromeDriver quedaba abierto al terminar.
- La descarga se detectaba contando archivos, lo que podía tomar un archivo equivocado.
