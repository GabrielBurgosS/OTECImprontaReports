"""App errors. Each one carries a technical message (for the log) and a plain-Spanish
message for the person using the app (user_message)."""


class OTECError(Exception):
    user_message = 'Ocurrió un error inesperado. Exporta el diagnóstico y envíalo a soporte.'

    def __init__(self, message: str | None = None, user_message: str | None = None):
        super().__init__(message or self.user_message)
        if user_message:
            self.user_message = user_message


class NoCredentialsError(OTECError):
    user_message = 'Falta ingresar el usuario y la contraseña de la plataforma. Complétalos en "Cuenta".'


class LoginError(OTECError):
    user_message = 'No se pudo iniciar sesión: usuario o contraseña incorrectos. Revísalos en "Cuenta".'


class NoInternetError(OTECError):
    user_message = 'No hay conexión a internet o la plataforma otecimpronta.cl no responde. Revisa tu conexión e intenta de nuevo.'


class BrowserError(OTECError):
    user_message = ('No se pudo abrir Google Chrome. Verifica que esté instalado '
                    '(google.com/chrome) y que haya internet la primera vez que usas el programa.')


class CourseNotFoundError(OTECError):
    def __init__(self, course_id: int):
        super().__init__(f'Course {course_id} not found or not accessible',
                         f'No se encontró el curso {course_id}. Verifica que el número sea correcto y que tu cuenta tenga acceso.')


class DownloadButtonNotFoundError(OTECError):
    def __init__(self, course_id: int, report: str):
        super().__init__(f'Download button for {report} not found in course {course_id}',
                         f'No se encontró el reporte de {report} del curso {course_id}. '
                         'Verifica que el número sea correcto y que tu cuenta tenga acceso.')


class DownloadTimeoutError(OTECError):
    def __init__(self, timeout: float):
        super().__init__(f'Download did not finish after {timeout} seconds',
                         'La plataforma tardó demasiado en entregar el archivo. Intenta de nuevo en unos minutos.')


class EmptyCourseError(OTECError):
    def __init__(self, course_id: int):
        super().__init__(f'Course {course_id} has no participants',
                         f'El curso {course_id} no tiene participantes inscritos.')


class TemplateError(OTECError):
    user_message = 'La plantilla seleccionada no es válida. Revisa la sección "Plantillas" en Ajustes.'


class ExcelError(OTECError):
    user_message = ('No se pudo generar el Excel. Verifica que Microsoft Excel esté instalado y '
                    'que no tengas abierto un archivo con el mismo nombre.')


class GradeMappingCancelled(OTECError):
    user_message = 'Se canceló la selección de pruebas para este curso.'


class Cancelled(OTECError):
    user_message = 'Proceso cancelado.'


def user_message(error: BaseException) -> str:
    if isinstance(error, OTECError):
        return error.user_message
    return OTECError.user_message
