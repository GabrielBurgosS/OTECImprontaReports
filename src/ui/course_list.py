"""Editable list of courses: ID, platform name, template and attendance type."""
from typing import Callable

import customtkinter as ctk

from src.core.job import CourseRequest
from src.errors import OTECError
from src.report_export.template_writer import ATTENDANCE_LABELS, ATTENDANCE_NONE
from src.report_export.templates import TemplateCatalog
from src.settings import Settings
from src.ui.theme import ERROR_COLOR, FONT_SMALL, MUTED

ATTENDANCE_BY_LABEL = {label: key for key, label in ATTENDANCE_LABELS.items()}
DEFAULT_TEMPLATE = 'semanal'


class CourseRow:
    def __init__(self, master, course_list: 'CourseList', row: int, course_id: str = '',
                 template_id: str = DEFAULT_TEMPLATE, attendance: str = ATTENDANCE_NONE):
        self.list = course_list
        catalog = course_list.catalog
        self.id_entry = ctk.CTkEntry(master, width=70, placeholder_text='N°', justify='center')
        self.id_entry.insert(0, course_id)
        self.name = ctk.CTkLabel(master, text='', anchor='w', justify='left', wraplength=290, font=FONT_SMALL)
        self.template = ctk.CTkOptionMenu(master, values=[t.name for t in catalog.templates], width=210,
                                          dynamic_resizing=False, command=lambda _v: self._template_changed())
        self.attendance = ctk.CTkSegmentedButton(master, values=list(ATTENDANCE_LABELS.values()),
                                                 command=lambda _v: self.list.changed())
        self.remove = ctk.CTkButton(master, text='✕', width=30, fg_color='transparent', text_color=ERROR_COLOR,
                                    hover_color=('gray85', 'gray25'), command=lambda: self.list.remove_row(self))
        self.widgets = [self.id_entry, self.name, self.template, self.attendance, self.remove]
        self.place(row)

        self.template.set(self._template_name(template_id))
        self.attendance.set(ATTENDANCE_LABELS.get(attendance, ATTENDANCE_LABELS[ATTENDANCE_NONE]))
        self._update_attendance_state()
        self.id_entry.bind('<FocusOut>', lambda _e: self.list.id_changed(self))
        self.id_entry.bind('<Return>', lambda _e: self.list.id_changed(self))
        self.refresh_name()

    def place(self, row: int):
        for column, widget in enumerate(self.widgets):
            widget.grid(row=row, column=column, padx=4, pady=4, sticky='ew' if column == 1 else 'w')

    def destroy(self):
        for widget in self.widgets:
            widget.destroy()

    def _template_name(self, template_id: str) -> str:
        try:
            return self.list.catalog.get(template_id).name
        except OTECError:
            return self.list.catalog.get(DEFAULT_TEMPLATE).name

    @property
    def template_id(self) -> str:
        name = self.template.get()
        return next(t.id for t in self.list.catalog.templates if t.name == name)

    @property
    def course_id_text(self) -> str:
        return self.id_entry.get().strip()

    def _template_changed(self):
        self._update_attendance_state()
        self.list.changed()

    def _update_attendance_state(self):
        try:
            layout = self.list.catalog.layout(self.template_id)
            has_attendance = layout is not None and layout.has_attendance
        except OTECError:
            has_attendance = False
        if has_attendance:
            self.attendance.configure(state='normal')
        else:
            self.attendance.set(ATTENDANCE_LABELS[ATTENDANCE_NONE])
            self.attendance.configure(state='disabled')

    def refresh_name(self, message: str | None = None, error: bool = False):
        text = self.course_id_text
        if message is not None:
            self.name.configure(text=message, text_color=ERROR_COLOR if error else MUTED)
        elif not text:
            self.name.configure(text='Escribe el número del curso', text_color=MUTED)
        elif not text.isdigit():
            self.name.configure(text='El número de curso solo lleva dígitos', text_color=ERROR_COLOR)
        else:
            name = self.list.settings.course_name(int(text))
            if name:
                self.name.configure(text=name, text_color=('gray10', 'gray90'))
            elif self.list.can_lookup():
                self.name.configure(text='Buscando nombre...', text_color=MUTED)
            else:
                self.name.configure(text='Configura tu cuenta para ver el nombre', text_color=MUTED)

    def to_dict(self) -> dict:
        return {'id': self.course_id_text, 'template': self.template_id,
                'attendance': ATTENDANCE_BY_LABEL[self.attendance.get()]}

    def set_enabled(self, enabled: bool):
        state = 'normal' if enabled else 'disabled'
        for widget in (self.id_entry, self.template, self.remove):
            widget.configure(state=state)
        if enabled:
            self._update_attendance_state()
        else:
            self.attendance.configure(state='disabled')


class CourseList(ctk.CTkFrame):
    def __init__(self, master, settings: Settings, catalog: TemplateCatalog,
                 on_ids_changed: Callable[[], None], can_lookup: Callable[[], bool]):
        super().__init__(master)
        self.settings = settings
        self.catalog = catalog
        self.on_ids_changed = on_ids_changed
        self.can_lookup = can_lookup
        self.rows: list[CourseRow] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 0))
        ctk.CTkLabel(header, text='Cursos a procesar', font=('Segoe UI', 15, 'bold')).pack(side='left')
        ctk.CTkLabel(header, text='Número de curso · nombre · plantilla · asistencia',
                     text_color=MUTED, font=FONT_SMALL).pack(side='left', padx=12)

        self.body = ctk.CTkScrollableFrame(self, height=180, fg_color='transparent')
        self.body.grid(row=1, column=0, sticky='nsew', padx=6)
        self.body.grid_columnconfigure(1, weight=1)

        self.add_button = ctk.CTkButton(self, text='+ Agregar curso', width=140, command=self.add_row)
        self.add_button.grid(row=2, column=0, sticky='w', padx=12, pady=(4, 12))

        for course in settings.courses:
            self.add_row(str(course.get('id', '')), course.get('template', DEFAULT_TEMPLATE),
                         course.get('attendance', ATTENDANCE_NONE), save=False)
        if not self.rows:
            self.add_row(save=False)

    def add_row(self, course_id: str = '', template_id: str | None = None,
                attendance: str = ATTENDANCE_NONE, save: bool = True):
        if template_id is None:
            template_id = self.rows[-1].template_id if self.rows else DEFAULT_TEMPLATE
        row = CourseRow(self.body, self, len(self.rows), course_id, template_id, attendance)
        self.rows.append(row)
        if save:
            row.id_entry.focus_set()
            self.changed()

    def remove_row(self, row: CourseRow):
        row.destroy()
        self.rows.remove(row)
        for index, other in enumerate(self.rows):
            other.place(index)
        if not self.rows:
            self.add_row(save=False)
        self.changed()

    def id_changed(self, row: CourseRow):
        row.refresh_name()
        self.changed()
        self.on_ids_changed()

    def changed(self):
        self.settings.courses = [r.to_dict() for r in self.rows if r.course_id_text]
        self.settings.save()

    def refresh_templates(self):
        names = [t.name for t in self.catalog.templates]
        for row in self.rows:
            current = row.template.get()
            row.template.configure(values=names)
            if current not in names:
                row.template.set(self.catalog.get(DEFAULT_TEMPLATE).name)
            row._update_attendance_state()

    def refresh_names(self, errors: dict[int, str] | None = None):
        errors = errors or {}
        for row in self.rows:
            text = row.course_id_text
            if text.isdigit() and int(text) in errors:
                row.refresh_name(errors[int(text)], error=True)
            else:
                row.refresh_name()

    def ids_without_name(self) -> list[int]:
        ids = {int(r.course_id_text) for r in self.rows if r.course_id_text.isdigit()}
        return sorted(i for i in ids if not self.settings.course_name(i))

    def requests(self) -> tuple[list[CourseRequest], list[str]]:
        """Return the valid requests and a list of problems to show the user."""
        problems, requests, seen = [], [], set()
        for number, row in enumerate(self.rows, start=1):
            text = row.course_id_text
            if not text:
                continue
            if not text.isdigit() or int(text) <= 0:
                problems.append(f'Fila {number}: "{text}" no es un número de curso válido.')
                continue
            key = (int(text), row.template_id)
            if key in seen:
                problems.append(f'Fila {number}: el curso {text} con la plantilla "{row.template.get()}" está repetido.')
                continue
            seen.add(key)
            requests.append(CourseRequest(int(text), row.template_id, ATTENDANCE_BY_LABEL[row.attendance.get()]))
        if not requests and not problems:
            problems.append('Agrega al menos un número de curso.')
        return requests, problems

    def set_enabled(self, enabled: bool):
        for row in self.rows:
            row.set_enabled(enabled)
        self.add_button.configure(state='normal' if enabled else 'disabled')
