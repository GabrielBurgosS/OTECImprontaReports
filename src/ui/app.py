"""Main window of OTEC Impronta Reports."""
import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import credentials as credential_store
from src.core.job import CourseResult, MappingRequest, Progress, ReportJob, fetch_course_names
from src.credentials import Credentials
from src.errors import LoginError, OTECError, user_message
from src.logging_setup import attach_queue
from src.paths import APP_DISPLAY_NAME, APP_VERSION, icon_file
from src.report_export.templates import TemplateCatalog
from src.settings import Settings
from src.ui.bridge import UiBridge
from src.ui.course_list import CourseList
from src.ui.dialogs import AccountDialog, GradeMappingDialog, SettingsDialog
from src.ui.theme import (ERROR_COLOR, FONT_HEADER, FONT_SMALL, MUTED, OK_COLOR, WARN_COLOR, apply_theme,
                          open_path, reveal_in_explorer)

logger = logging.getLogger(__name__)

NAME_LOOKUP_DELAY_MS = 1200
MAX_ACTIVITY_LINES = 500


class MainWindow(ctk.CTk):
    def __init__(self, settings: Settings, catalog: TemplateCatalog):
        apply_theme()
        super().__init__()
        self.settings = settings
        self.catalog = catalog
        self.bridge = UiBridge(self)
        self.credentials: Credentials | None = credential_store.load(settings.username)
        self.cancel_event: threading.Event | None = None
        self.lookup_cancel = threading.Event()
        self.workers: list[threading.Thread] = []
        self.running = False
        self.lookup_running = False
        self._lookup_after = None

        self.title(f'{APP_DISPLAY_NAME}')
        self.geometry('1080x840')
        self.minsize(980, 680)
        if icon_file().exists():
            self.iconbitmap(str(icon_file()))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_header()
        self._build_account()
        self.courses = CourseList(self, settings, catalog, self._schedule_name_lookup, self._can_lookup)
        self.courses.grid(row=2, column=0, sticky='nsew', padx=16, pady=(8, 0))
        self._build_output()
        self._build_actions()
        self._build_bottom()

        self.log_queue: queue.Queue = queue.Queue()
        attach_queue(self.log_queue)
        self.after(150, self._drain_log)
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self._refresh_account()
        self._schedule_name_lookup()

    # -- layout -------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=16, pady=(14, 0))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text='Generador de Reportes', font=FONT_HEADER).grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(header, text=f'OTEC Impronta · v{APP_VERSION}', text_color=MUTED).grid(row=1, column=0, sticky='w')
        self.settings_button = ctk.CTkButton(header, text='⚙  Ajustes', width=110, fg_color='transparent',
                                             border_width=1, text_color=('gray10', 'gray90'),
                                             command=self._open_settings)
        self.settings_button.grid(row=0, column=1, rowspan=2)

    def _build_account(self):
        bar = ctk.CTkFrame(self)
        bar.grid(row=1, column=0, sticky='ew', padx=16, pady=(12, 0))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text='Cuenta:', font=ctk.CTkFont(weight='bold')).grid(row=0, column=0, padx=(12, 6), pady=10)
        self.account_label = ctk.CTkLabel(bar, text='', anchor='w')
        self.account_label.grid(row=0, column=1, sticky='w')
        self.account_button = ctk.CTkButton(bar, text='Configurar', width=110, command=self._open_account)
        self.account_button.grid(row=0, column=2, padx=12)

    def _build_output(self):
        bar = ctk.CTkFrame(self)
        bar.grid(row=3, column=0, sticky='ew', padx=16, pady=(8, 0))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text='Guardar en:', font=ctk.CTkFont(weight='bold')).grid(row=0, column=0, padx=(12, 6), pady=10)
        self.output_label = ctk.CTkLabel(bar, text=self.settings.output_dir, anchor='w')
        self.output_label.grid(row=0, column=1, sticky='w')
        self.output_button = ctk.CTkButton(bar, text='Cambiar...', width=100, fg_color='transparent', border_width=1,
                                           text_color=('gray10', 'gray90'), command=self._choose_output)
        self.output_button.grid(row=0, column=2, padx=4)
        ctk.CTkButton(bar, text='Abrir carpeta', width=110, fg_color='transparent', border_width=1,
                      text_color=('gray10', 'gray90'), command=self._open_output).grid(row=0, column=3, padx=(4, 12))

    def _build_actions(self):
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.grid(row=4, column=0, sticky='ew', padx=16, pady=(12, 0))
        bar.grid_columnconfigure(2, weight=1)
        self.generate_button = ctk.CTkButton(bar, text='▶  Generar reportes', height=42, width=200,
                                             font=('Segoe UI', 15, 'bold'), command=self._generate)
        self.generate_button.grid(row=0, column=0, rowspan=2)
        self.cancel_button = ctk.CTkButton(bar, text='■  Cancelar', height=42, width=120, state='disabled',
                                           fg_color=('gray70', 'gray30'), hover_color=ERROR_COLOR,
                                           command=self._cancel)
        self.cancel_button.grid(row=0, column=1, rowspan=2, padx=10)
        self.progress = ctk.CTkProgressBar(bar)
        self.progress.set(0)
        self.progress.grid(row=0, column=2, sticky='ew', padx=(10, 0), pady=(6, 2))
        self.status = ctk.CTkLabel(bar, text='Listo.', anchor='w', text_color=MUTED)
        self.status.grid(row=1, column=2, sticky='w', padx=(10, 0))

    def _build_bottom(self):
        tabs = ctk.CTkTabview(self, height=200)
        tabs.grid(row=5, column=0, sticky='nsew', padx=16, pady=(4, 14))
        self.tabs = tabs
        results_tab, activity_tab = tabs.add('Resultados'), tabs.add('Actividad')
        results_tab.grid_columnconfigure(0, weight=1)
        results_tab.grid_rowconfigure(0, weight=1)
        self.results = ctk.CTkScrollableFrame(results_tab, fg_color='transparent')
        self.results.grid(row=0, column=0, sticky='nsew')
        self.results.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.results, text='Aquí aparecerán los reportes generados.', text_color=MUTED).grid(
            row=0, column=0, sticky='w', padx=8, pady=8)
        activity_tab.grid_columnconfigure(0, weight=1)
        activity_tab.grid_rowconfigure(0, weight=1)
        self.activity = ctk.CTkTextbox(activity_tab, font=('Consolas', 11), state='disabled', wrap='word')
        self.activity.grid(row=0, column=0, sticky='nsew')

    # -- account ----------------------------------------------------------------
    def _refresh_account(self):
        if self.credentials:
            saved = bool(self.settings.username) and self.settings.username == self.credentials.username
            note = 'guardada en este equipo' if saved else 'solo durante esta sesión'
            self.account_label.configure(text=f'{self.credentials.username}  ·  ✓ {note}', text_color=OK_COLOR)
            self.account_button.configure(text='Cambiar')
        else:
            self.account_label.configure(text='No configurada: ingresa tu usuario y contraseña de la plataforma.',
                                         text_color=WARN_COLOR)
            self.account_button.configure(text='Configurar')

    def _open_account(self) -> bool:
        result = AccountDialog(self, self.bridge, self.settings, self.credentials).show()
        if result == 'forgotten':
            self.credentials = None
        elif result:
            self.credentials = result
            self._schedule_name_lookup()
        self._refresh_account()
        self.courses.refresh_names()
        return self.credentials is not None

    def _can_lookup(self) -> bool:
        return self.credentials is not None

    # -- course names -----------------------------------------------------------
    def _schedule_name_lookup(self):
        if self._lookup_after is not None:
            self.after_cancel(self._lookup_after)
        self._lookup_after = self.after(NAME_LOOKUP_DELAY_MS, self._lookup_names)

    def _lookup_names(self):
        self._lookup_after = None
        ids = self.courses.ids_without_name()
        if not ids or not self.credentials or self.running or self.lookup_running:
            return
        self.lookup_running = True
        self.status.configure(text=f'Buscando el nombre de {len(ids)} curso(s) en la plataforma...')
        creds = self.credentials

        def done(names):
            self.lookup_running = False
            errors = {cid: e.user_message for cid, e in names.items() if isinstance(e, OTECError)}
            self.courses.refresh_names(errors)
            if not self.running:
                self.status.configure(text='Listo.')
            if self.courses.ids_without_name() and set(self.courses.ids_without_name()) - set(errors):
                self._schedule_name_lookup()

        def failed(error):
            self.lookup_running = False
            self.courses.refresh_names({cid: user_message(error) for cid in ids})
            self.status.configure(text='No se pudo buscar el nombre de los cursos.')
            if isinstance(error, LoginError):
                self.account_label.configure(text='La contraseña guardada no funciona. Presiona "Cambiar".',
                                             text_color=ERROR_COLOR)

        self.workers.append(self.bridge.run(
            lambda: fetch_course_names(creds, self.settings, ids, self.lookup_cancel), done, failed, name='names'))

    # -- output folder -------------------------------------------------------------
    def _choose_output(self):
        folder = filedialog.askdirectory(parent=self, title='¿Dónde guardar los reportes?',
                                         initialdir=self.settings.output_dir)
        if folder:
            self.settings.output_dir = str(Path(folder))
            self.settings.save()
            self.output_label.configure(text=self.settings.output_dir)

    def _open_output(self):
        folder = Path(self.settings.output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        open_path(folder)

    # -- generation -------------------------------------------------------------
    def _generate(self):
        requests, problems = self.courses.requests()
        if problems:
            messagebox.showwarning('Revisa la lista de cursos', '\n'.join(problems), parent=self)
            return
        if not self.credentials and not self._open_account():
            return
        self.courses.changed()
        self._set_running(True)
        self._clear_results()
        self.tabs.set('Actividad')
        self.cancel_event = threading.Event()
        job = ReportJob(self.credentials, self.settings, self.catalog,
                        on_progress=lambda p: self.bridge.call_soon(self._on_progress, p),
                        cancel_event=self.cancel_event,
                        resolve_mapping=lambda req: self.bridge.ask(self._ask_mapping, req))
        self.workers.append(self.bridge.run(lambda: job.run(requests), self._on_finished, self._on_failed,
                                            name='reports'))

    def _cancel(self):
        if self.cancel_event and not self.cancel_event.is_set():
            self.cancel_event.set()
            self.status.configure(text='Cancelando... (termina el paso en curso)')
            self.cancel_button.configure(state='disabled')

    def _ask_mapping(self, request: MappingRequest) -> dict | None:
        return GradeMappingDialog(self, request).show()

    def _on_progress(self, progress: Progress):
        self.progress.set(progress.fraction)
        self.status.configure(text=progress.message)

    def _on_finished(self, results: list[CourseResult]):
        self._set_running(False)
        ok = sum(r.success for r in results)
        failed = len(results) - ok
        self.progress.set(1)
        summary = f'✓ {ok} reporte(s) generado(s)' + (f'  ·  ✗ {failed} con error' if failed else '')
        self.status.configure(text=summary)
        self._show_results(results)
        self.tabs.set('Resultados')
        self.courses.refresh_names()

    def _on_failed(self, error: BaseException):
        self._set_running(False)
        self.progress.set(0)
        message = user_message(error)
        self.status.configure(text=f'✗ {message}')
        if not isinstance(error, OTECError):
            logger.error('Error inesperado', exc_info=error)
        if isinstance(error, LoginError):
            self.account_label.configure(text='Usuario o contraseña incorrectos. Presiona "Cambiar".',
                                         text_color=ERROR_COLOR)
        messagebox.showerror('No se pudieron generar los reportes',
                             message + '\n\nSi el problema continúa, ve a Ajustes → Registros y soporte → '
                                       'Exportar diagnóstico.', parent=self)

    def _set_running(self, running: bool):
        self.running = running
        state = 'disabled' if running else 'normal'
        for widget in (self.generate_button, self.account_button, self.settings_button, self.output_button):
            widget.configure(state=state)
        self.cancel_button.configure(state='normal' if running else 'disabled')
        self.courses.set_enabled(not running)
        if running:
            self.progress.set(0)

    # -- results ----------------------------------------------------------------
    def _clear_results(self):
        for child in self.results.winfo_children():
            child.destroy()

    def _show_results(self, results: list[CourseResult]):
        self._clear_results()
        row = 0
        for result in results:
            cid = result.request.course_id
            name = result.course_name or self.settings.course_name(cid) or ''
            icon, color = ('✓', OK_COLOR) if result.success else ('✗', ERROR_COLOR)
            ctk.CTkLabel(self.results, text=icon, text_color=color, font=('Segoe UI', 16, 'bold')).grid(
                row=row, column=0, padx=(8, 4), sticky='n')
            title = f'Curso {cid}' + (f' · {name}' if name else '')
            detail = result.output_path.name if result.success else result.error_message
            text = ctk.CTkFrame(self.results, fg_color='transparent')
            text.grid(row=row, column=1, sticky='ew', pady=3)
            ctk.CTkLabel(text, text=title, font=ctk.CTkFont(weight='bold'), anchor='w', justify='left',
                         wraplength=640).pack(anchor='w')
            ctk.CTkLabel(text, text=detail, text_color=MUTED if result.success else ERROR_COLOR, anchor='w',
                         justify='left', wraplength=640, font=FONT_SMALL).pack(anchor='w')
            for warning in result.warnings:
                ctk.CTkLabel(text, text=f'⚠ {warning}', text_color=WARN_COLOR, anchor='w', justify='left',
                             wraplength=640, font=FONT_SMALL).pack(anchor='w')
            if result.success:
                buttons = ctk.CTkFrame(self.results, fg_color='transparent')
                buttons.grid(row=row, column=2, padx=8, sticky='n')
                ctk.CTkButton(buttons, text='Abrir Excel', width=96,
                              command=lambda p=result.output_path: open_path(p)).pack(side='left', padx=2)
                ctk.CTkButton(buttons, text='Ver en carpeta', width=110, fg_color='transparent', border_width=1,
                              text_color=('gray10', 'gray90'),
                              command=lambda p=result.output_path: reveal_in_explorer(p)).pack(side='left', padx=2)
            row += 1

    # -- misc ---------------------------------------------------------------------
    def _open_settings(self):
        if SettingsDialog(self, self.bridge, self.settings, self.catalog).show():
            self.courses.refresh_templates()

    def _drain_log(self):
        lines = []
        while True:
            try:
                record = self.log_queue.get_nowait()
            except queue.Empty:
                break
            message = record.getMessage().splitlines()[0] if record.getMessage() else ''
            lines.append(f'{datetime.fromtimestamp(record.created):%H:%M:%S}  {message}')
        if lines:
            self.activity.configure(state='normal')
            self.activity.insert('end', '\n'.join(lines) + '\n')
            excess = int(self.activity.index('end-1c').split('.')[0]) - MAX_ACTIVITY_LINES
            if excess > 0:
                self.activity.delete('1.0', f'{excess + 1}.0')
            self.activity.see('end')
            self.activity.configure(state='disabled')
        self.after(150, self._drain_log)

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno('Salir', 'Se están generando reportes. ¿Cancelar y salir?', parent=self):
                return
            self.cancel_event.set()
        self.lookup_cancel.set()
        self.settings.save()
        self.status.configure(text='Cerrando... (esperando que termine el paso en curso)')
        self.generate_button.configure(state='disabled')
        self.cancel_button.configure(state='disabled')
        self._close_when_idle()

    def _close_when_idle(self):
        # Wait for workers so Chrome and Excel are always closed properly
        self.workers = [w for w in self.workers if w.is_alive()]
        if self.workers:
            self.after(300, self._close_when_idle)
        else:
            self.destroy()
