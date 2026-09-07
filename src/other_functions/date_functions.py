from datetime import datetime

def get_cur_date_string(time=True)-> str:
    """
    Generates a text with the current date.
    ### Params:
    - ```time: bool```: Indicates if the time its included on the string.
    """
    if time:
        return datetime.today().strftime('%d-%m (%H%M%S)')
    else:
        return datetime.today().strftime('%d-%m')    