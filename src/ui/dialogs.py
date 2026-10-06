"""Modal dialogs: account, grade mapping, settings and templates."""
import logging
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import credentials as credential_store
from src.core.job import MappingRequest, test_login
from src.credentials import Credentials
from src.diagnostics import export_diagnostics
from src.errors import OTECError, user_message
from src.paths import logs_dir
from src.report_export.templates import ATTENDANCE, FORMULA, MANUAL, TemplateCatalog
from src.settings import Settings
from src.ui.bridge import UiBridge
from src.ui.theme import FONT_SMALL, FONT_TITLE, MUTED, OK_COLOR, OUTLINE, ERROR_COLOR, open_path

logger = logging.getLogger(__name__)

EMPTY_CHOICE = '(dejar vacía)'


def describe_layout(layout) -> str:
    if layout is None:
        return 'Excel simple con todas las columnas y todas las pruebas del curso.'
    groups = {'Se llenan': [], 'Calcula Excel': [], 'A mano': []}
    for column in layout.columns:
        if column.role == FORMULA:
            groups['Calcula Excel'].append(column.header)
        elif column.role in (MANUAL, ATTENDANCE):
            groups['A mano'].append(column.header)
        else:
            groups['Se llenan'].append(column.header)
    lines = [f'{label}: {", ".join(headers)}' for label, headers in groups.items() if headers]
    if layout.has_attendance:
        lines.append('Asistencia: se puede quitar o marcar como Zoom / Presencial.')
    return '\n'.join(lines)


class ModalDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.bind('<Escape>', lambda _e: self.cancel())
        # CTkToplevel needs a moment before it can grab focus on Windows
        self.after(150, self._activate)

    def _activate(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def center_on(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f'+{max(x, 0)}+{max(y, 0)}')

    def show(self):
        self.center_on(self.master)
        self.wait_window()
        return self.result

    def cancel(self):
        self.result = None
        self.destroy()


class AccountDialog(ModalDialog):
    """Ask username/password, optionally test them and remember them in the Credential Manager."""

    def __init__(self, parent, bridge: UiBridge, settings: Settings, current: Credentials | None):
        super().__init__(parent, 'Cuenta de la plataforma')
        self.bridge = bridge
        self.settings = settings
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text='Cuenta de otecimpronta.cl', font=FONT_TITLE).grid(
            row=0, column=0, padx=24, pady=(20, 4), sticky='w')
        ctk.CTkLabel(self, text='Usa el mismo usuario y contraseña con que entras a la plataforma.',
                     text_color=MUTED).grid(row=1, column=0, padx=24, sticky='w')

        self.username = ctk.CTkEntry(self, width=340, placeholder_text='Usuario')
        self.username.grid(row=2, column=0, padx=24, pady=(16, 6), sticky='ew')
        password_row = ctk.CTkFrame(self, fg_color='transparent')
        password_row.grid(row=3, column=0, padx=24, pady=6, sticky='ew')
        password_row.grid_columnconfigure(0, weight=1)
        self.password = ctk.CTkEntry(password_row, show='•', placeholder_text='Contraseña')
        self.password.grid(row=0, column=0, sticky='ew')
        self.show_button = ctk.CTkButton(password_row, text='👁', width=36, command=self._toggle_password)
        self.show_button.grid(row=0, column=1, padx=(6, 0))

        self.remember = ctk.CTkCheckBox(self, text='Recordar en este equipo')
        self.remember.grid(row=4, column=0, padx=24, pady=(8, 0), sticky='w')
        ctk.CTkLabel(self, text='Se guarda cifrada en el Administrador de credenciales de Windows.',
                     text_color=MUTED, font=FONT_SMALL).grid(row=5, column=0, padx=52, sticky='w')

        self.status = ctk.CTkLabel(self, text='', wraplength=340, justify='left')
        self.status.grid(row=6, column=0, padx=24, pady=(10, 0), sticky='w')

        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.grid(row=7, column=0, padx=24, pady=(12, 20), sticky='ew')
        buttons.grid_columnconfigure(1, weight=1)
        self.test_button = ctk.CTkButton(buttons, text='Probar conexión', **OUTLINE, command=self._test)
        self.test_button.grid(row=0, column=0)
        ctk.CTkButton(buttons, text='Guardar', width=110, command=self._save).grid(row=0, column=2)
        if settings.username:
            ctk.CTkButton(self, text='Olvidar la cuenta guardada', fg_color='transparent', text_color=ERROR_COLOR,
                          hover=False, command=self._forget).grid(row=8, column=0, pady=(0, 14))

        if current:
            self.username.insert(0, current.username)
            self.password.insert(0, current.password)
        elif settings.username:
            self.username.insert(0, settings.username)
        self.remember.select()
        self.username.bind('<Return>', lambda _e: self.password.focus_set())
        self.password.bind('<Return>', lambda _e: self._save())
        self.after(200, (self.password if self.username.get() else self.username).focus_set)

    def _toggle_password(self):
        self.password.configure(show='' if self.password.cget('show') else '•')

    def _read(self) -> Credentials | None:
        username, password = self.username.get().strip(), self.password.get()
        if not username or not password:
            self.status.configure(text='Completa el usuario y la contraseña.', text_color=ERROR_COLOR)
            return None
        return Credentials(username, password)

    def _test(self):
        creds = self._read()
        if not creds:
            return
        self.test_button.configure(state='disabled', text='Probando...')
        self.status.configure(text='Conectando con la plataforma (puede tardar unos segundos)...', text_color=MUTED)

        def done(_):
            self.test_button.configure(state='normal', text='Probar conexión')
            self.status.configure(text='✓ Conexión correcta.', text_color=OK_COLOR)

        def failed(error):
            self.test_button.configure(state='normal', text='Probar conexión')
            self.status.configure(text=f'✗ {user_message(error)}', text_color=ERROR_COLOR)

        self.bridge.run(lambda: test_login(creds, self.settings), done, failed, name='login-test')

    def _save(self):
        creds = self._read()
        if not creds:
            return
        if self.remember.get():
            try:
                if self.settings.username and self.settings.username != creds.username:
                    credential_store.delete(self.settings.username)
                credential_store.save(creds)
            except Exception:
                logger.exception('Could not save credentials')
                messagebox.showwarning('Cuenta', 'No se pudo guardar la contraseña en Windows. '
                                                 'Se usará solo mientras el programa esté abierto.', parent=self)
            self.settings.username = creds.username
        else:
            credential_store.delete(self.settings.username)
            self.settings.username = creds.username
        self.settings.save()
        self.result = creds
        self.destroy()

    def _forget(self):
        if messagebox.askyesno('Cuenta', '¿Borrar la contraseña guardada en este equipo?', parent=self):
            credential_store.delete(self.settings.username)
            self.settings.username = ''
            self.settings.save()
            self.result = 'forgotten'
            self.destroy()


class GradeMappingDialog(ModalDialog):
    """Let the user choose which platform quiz goes in each grade column of the template."""

    def __init__(self, parent, request: MappingRequest):
        super().__init__(parent, 'Elegir pruebas')
        self.request = request
        ctk.CTkLabel(self, text='¿Qué prueba va en cada columna?', font=FONT_TITLE).grid(
            row=0, column=0, columnspan=2, padx=24, pady=(20, 4), sticky='w')
        ctk.CTkLabel(self, text=f'Curso {request.course_id} · {request.course_name}\n'
                                f'Plantilla "{request.template_name}". Tu elección se recordará para este curso.',
                     text_color=MUTED, justify='left', wraplength=420).grid(
            row=1, column=0, columnspan=2, padx=24, pady=(0, 12), sticky='w')
        choices = [EMPTY_CHOICE] + request.quizzes
        self.menus = {}
        for row, header in enumerate(request.headers, start=2):
            ctk.CTkLabel(self, text=header, font=ctk.CTkFont(weight='bold')).grid(
                row=row, column=0, padx=(24, 12), pady=6, sticky='w')
            menu = ctk.CTkOptionMenu(self, values=choices, width=300, dynamic_resizing=False)
            menu.set(request.suggestion.get(header) or EMPTY_CHOICE)
            menu.grid(row=row, column=1, padx=(0, 24), pady=6, sticky='ew')
            self.menus[header] = menu
        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.grid(row=len(request.headers) + 2, column=0, columnspan=2, padx=24, pady=(14, 20), sticky='e')
        ctk.CTkButton(buttons, text='Omitir este curso', **OUTLINE,
                      command=self.cancel).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(buttons, text='Continuar', command=self._accept).grid(row=0, column=1)

    def _accept(self):
        self.result = {h: (None if m.get() == EMPTY_CHOICE else m.get()) for h, m in self.menus.items()}
        self.destroy()


class SettingsDialog(ModalDialog):
    def __init__(self, parent, bridge: UiBridge, settings: Settings, catalog: TemplateCatalog):
        super().__init__(parent, 'Ajustes')
        self.settings = settings
        self.catalog = catalog
        self.changed_templates = False
        self.grid_columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self, width=620, height=430)
        tabs.grid(row=0, column=0, padx=16, pady=(8, 0), sticky='nsew')
        general, templates, support = tabs.add('General'), tabs.add('Plantillas'), tabs.add('Registros y soporte')

        # General
        self.show_browser = ctk.CTkCheckBox(general, text='Mostrar el navegador mientras trabaja')
        self.show_browser.grid(row=0, column=0, padx=12, pady=(16, 2), sticky='w')
        ctk.CTkLabel(general, text='Útil para ver qué está pasando si algo falla. Normalmente va oculto.',
                     text_color=MUTED, font=FONT_SMALL).grid(row=1, column=0, padx=40, sticky='w')
        if settings.show_browser:
            self.show_browser.select()
        timeout_row = ctk.CTkFrame(general, fg_color='transparent')
        timeout_row.grid(row=2, column=0, padx=12, pady=(18, 0), sticky='w')
        ctk.CTkLabel(timeout_row, text='Tiempo máximo de espera por descarga (segundos):').grid(row=0, column=0)
        self.timeout = ctk.CTkEntry(timeout_row, width=70)
        self.timeout.insert(0, str(settings.download_timeout))
        self.timeout.grid(row=0, column=1, padx=8)

        # Templates
        templates.grid_columnconfigure(0, weight=1)
        templates.grid_rowconfigure(0, weight=1)
        self.template_list = ctk.CTkScrollableFrame(templates, height=330, width=560)
        self.template_list.grid(row=0, column=0, sticky='nsew', padx=4, pady=(4, 8))
        self.template_list.grid_columnconfigure(0, weight=1)
        template_buttons = ctk.CTkFrame(templates, fg_color='transparent')
        template_buttons.grid(row=1, column=0, sticky='ew')
        ctk.CTkButton(template_buttons, text='+ Agregar plantilla', command=self._add_template).grid(
            row=0, column=0, padx=4)
        ctk.CTkButton(template_buttons, text='Restaurar originales', **OUTLINE,
                      command=self._restore_templates).grid(row=0, column=1, padx=4)
        self._render_templates()

        # Support
        ctk.CTkLabel(support, text='Si algo falla, exporta el diagnóstico y envíalo a soporte.\n'
                                   'Incluye los últimos registros y capturas, nunca tu contraseña.',
                     justify='left').grid(row=0, column=0, padx=12, pady=(16, 12), sticky='w')
        ctk.CTkButton(support, text='Exportar diagnóstico', command=self._export).grid(
            row=1, column=0, padx=12, pady=4, sticky='w')
        ctk.CTkButton(support, text='Abrir carpeta de registros', **OUTLINE,
                      command=lambda: open_path(logs_dir())).grid(row=2, column=0, padx=12, pady=4, sticky='w')

        ctk.CTkButton(self, text='Guardar y cerrar', command=self._save).grid(
            row=1, column=0, padx=16, pady=16, sticky='e')

    def _render_templates(self):
        for child in self.template_list.winfo_children():
            child.destroy()
        for row, template in enumerate(self.catalog.templates):
            card = ctk.CTkFrame(self.template_list)
            card.grid(row=row, column=0, sticky='ew', pady=4, padx=(0, 14))
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=template.name, font=ctk.CTkFont(weight='bold')).grid(
                row=0, column=0, padx=10, pady=(6, 0), sticky='w')
            try:
                detail = describe_layout(self.catalog.layout(template.id))
            except OTECError as e:
                detail = f'⚠ {e.user_message}'
            ctk.CTkLabel(card, text=detail, text_color=MUTED, font=FONT_SMALL, wraplength=380,
                         justify='left').grid(row=1, column=0, padx=10, pady=(0, 6), sticky='w')
            if template.is_plain and template.builtin:
                continue
            actions = ctk.CTkFrame(card, fg_color='transparent', width=10, height=10)
            actions.grid(row=0, column=1, rowspan=2, padx=6)
            if not template.is_plain:
                ctk.CTkButton(actions, text='Abrir', width=60,
                              command=lambda t=template: open_path(t.path)).grid(row=0, column=0, padx=2)
            if not template.builtin:
                ctk.CTkButton(actions, text='Eliminar', width=70, **{**OUTLINE, 'text_color': ERROR_COLOR},
                              command=lambda t=template: self._remove_template(t.id)).grid(row=0, column=1, padx=2)

    def _add_template(self):
        path = filedialog.askopenfilename(parent=self, title='Elige la plantilla de Excel',
                                          filetypes=[('Excel', '*.xlsx')])
        if not path:
            return
        name = ctk.CTkInputDialog(title='Nombre de la plantilla',
                                  text='¿Cómo quieres llamar a esta plantilla?\n'
                                       '(se usará también al inicio del nombre de cada reporte)').get_input()
        if not name or not name.strip():
            return
        try:
            self.catalog.add(Path(path), name)
        except OTECError as e:
            messagebox.showerror('Plantilla', e.user_message, parent=self)
            return
        self.changed_templates = True
        self._render_templates()

    def _remove_template(self, template_id):
        if messagebox.askyesno('Plantilla', '¿Eliminar esta plantilla?', parent=self):
            self.catalog.remove(template_id)
            self.changed_templates = True
            self._render_templates()

    def _restore_templates(self):
        if messagebox.askyesno('Plantillas', 'Se volverán a copiar las plantillas originales '
                                             '(se pierden los cambios que les hayas hecho). ¿Continuar?', parent=self):
            self.catalog.restore_builtin()
            self.changed_templates = True
            self._render_templates()

    def _export(self):
        folder = filedialog.askdirectory(parent=self, title='¿Dónde guardar el diagnóstico?',
                                         initialdir=str(Path.home() / 'Desktop'))
        if not folder:
            return
        zip_path = export_diagnostics(Path(folder))
        messagebox.showinfo('Diagnóstico', f'Se creó el archivo:\n{zip_path.name}\n\nEnvíalo a soporte.', parent=self)
        open_path(zip_path.parent)

    def _save(self):
        try:
            timeout = int(self.timeout.get())
            if not 10 <= timeout <= 600:
                raise ValueError
        except ValueError:
            messagebox.showerror('Ajustes', 'El tiempo de espera debe ser un número entre 10 y 600.', parent=self)
            return
        self.settings.download_timeout = timeout
        self.settings.show_browser = bool(self.show_browser.get())
        self.settings.save()
        self.result = True
        self.destroy()

    def cancel(self):
        self.result = self.changed_templates or None
        self.destroy()
