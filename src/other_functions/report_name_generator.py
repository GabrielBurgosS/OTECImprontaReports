from src.other_functions.date_functions import get_cur_date_string

def clean_course_name(course_name: str) -> str:
    course_name = course_name.replace('Curso de Capacitación', '')
    course_name = course_name.replace('"', '')
    course_name = course_name.replace('“', '')
    course_name = course_name.replace('”', '')
    course_name = course_name.replace(':', '')
    # if len(course_name) > 90:
    #     course_list_name = course_name.split(' ')
    #     if len(course_list_name) > 10:
    #         course_name = ' '.join(course_list_name[10])
    return course_name

def generate_report_name(course_dict: dict) -> str:
    # Info extraction
    type = course_dict["info"]["type"]
    id = course_dict["info"]["id"]
    course_name = course_dict["info"]["name"]
    # Name Generation
    type_name = 'Semanal' if type == 'weekly' else 'Final'
    course_name = clean_course_name(course_name)
    report_name = f'Reporte {type_name} - {course_name} ({get_cur_date_string(time=False)})'
    return report_name