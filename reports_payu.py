# Environment variables
import environ

# PayU selenium
from utils.payu_selenium import PayuSelenium

# Utils
from utils.utils_payu import (
    get_date,
    define_workflow
)

env = environ.Env()
env.read_env('.local/.env')

DATA = []


@define_workflow
def run_payu(path_workspace: str):
    user_confirmation = None
    start_date = None
    end_date = None
    user_selection = int(input('''
    1. Ejecutar automatización
    2. Ejecutar por fechas
    3. Reporte Mensual 
    :'''))

    if user_selection == 1:
        print('Ejecutando Automatización'.center(50, '='))
        start_date, end_date, global_date, current_day = get_date(True)
        user_confirmation = input(f'La fecha es {global_date},\n¿Desea generar el reporte? (Y/N): ').lower()

    if user_selection == 3:
        print('REPORTE MENSUAL PAYU'.center(50, '='))
        start_date, end_date, current_day = get_date(False)
        user_confirmation = input(f'''
        La fecha inicial es {start_date}
        La fecha final es {end_date}
        ¿Desea generar el reporte? Y/N
        : ''').lower()

    if user_selection == 2 or user_confirmation == 'n':
        print('Ejecutando por fechas'.center(50, '='))
        start_date = f'{input("Digite la fecha de inicio (dd/mm/yyyy): ")} 00:00'
        end_date = f'{input("Digite la fecha de fin (dd/mm/yyyy): ")} 23:59'
        user_confirmation = input(f'''
        La fecha inicial es {start_date}
        La fecha final es {end_date}
        ¿Desea generar el reporte? Y/N
        : ''').lower()

    if start_date is not None and end_date is not None:
        if user_confirmation == 'y':
            distinct_number = None
            if user_selection != 3:
                distinct_number = input('Digite el numero distintivo para el informe: ').lower()
            if user_selection == 3:
                report_month = True
            else:
                report_month = False
            payu_selenium = PayuSelenium(path_workspace=path_workspace,
                                         initial_date=start_date,
                                         final_date=end_date,
                                         distinct_number=distinct_number,
                                         report_month=report_month)
            for account in DATA:
                username = None
                account_name = account.get('account_name')
                number_account = account.get('number_account')
                payu_selenium.login(username=username,
                                    account_name=account_name)
                payu_selenium.account(account_name=account_name,
                                      number_account=number_account)
            input('PRESIONE ENTER PARA CONTINUAR'.center(50, '='))
            if report_month:
                return True
        else:
            print('Opción incorrecta')
    else:
        print('No se ingreso ninguna fecha')


if __name__ == '__main__':
    run_payu()
