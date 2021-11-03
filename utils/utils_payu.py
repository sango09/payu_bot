# Python
import os
from datetime import datetime, timedelta, date
from time import sleep
from zipfile import ZipFile
from os import path

# Pandas
import pandas as pd
from pandas import DataFrame

# gspread
import gspread

ACCOUNTS_DAILY = []

ACCOUNTS_MONTH = []


def define_path(file_path: str):
    """Define el path absoluto para los reportes descargados"""
    return path.abspath(f'files/report_files/{file_path}')


def delete_old_reports(folder_path: str):
    """Elimina los reportes anteriormente descargados"""
    list_dir = os.listdir(folder_path)
    if list_dir:
        [os.remove(define_path(filename)) for filename in list_dir if '.zip' or '.csv' in filename]


def define_workflow(func):
    """
    Decorador encargado de ejecutar el flujo de datos
    necesarios para actualizar el reporte de Payu en Google Sheets
    """

    def wrapper():
        PATH_WORKSPACE = path.abspath('files/report_files/')
        delete_old_reports(PATH_WORKSPACE)
        report_status = func(PATH_WORKSPACE)
        files_dowloaded = verify_zip_or_csv_files(PATH_WORKSPACE)
        if report_status:
            date_entered = datetime.today()
            month_name = (date(date_entered.year, date_entered.month, 1) - timedelta(days=1)).strftime('%B')
            print(f'Generando reporte mensual de {month_name}, por favor espere :)')
            writer = pd.ExcelWriter(f'report_payu_{month_name}.xlsx', engine='xlsxwriter')
            for account_month in ACCOUNTS_MONTH:
                for filter_account in account_month.get('accounts_to_filter'):
                    df_temp_month = create_and_join_dataframes(
                        csv_files=files_dowloaded,
                        bussiness_id=account_month.get('bussiness_id'),
                        account_id=filter_account.get('account_filter_id')
                    )
                    df_temp_month.to_excel(writer,
                                           sheet_name=filter_account.get('account_name'),
                                           index=False,
                                           encoding="ISO-8859-1",
                                           engine='xlsxwriter')
            writer.save()
            print('Reporte mensual generado exitosamente'.center(50, '='))
        else:
            for account in ACCOUNTS_DAILY:
                df_temp = create_and_join_dataframes(
                    csv_files=files_dowloaded,
                    bussiness_id=account.get('bussiness_id'),
                    account_id=account.get('account_id')
                )
                for filter_account in account.get('accounts_to_filter'):
                    if not df_temp.empty:
                        data_cleaned = clean_dataframe(df_temp, type_account=filter_account.get('account_filter_id'))
                        if data_cleaned:
                            show_values(data_to_show=data_cleaned,
                                        sheet_name=filter_account.get("sheet_name"),
                                        account_id=filter_account.get('account_filter_id'))
                            update_sheet(data_cleaned, filter_account.get('sheet_name'))
                        else:
                            print('DF VACIO REVISAR :)')
            print('REPORTE FINALIZADO'.center(50, '='))
            # workspace_files(PATH_WORKSPACE)

    return wrapper


def get_date(state: bool) -> tuple:
    """
    Generador de fechas necesarias para filtrar
    los reportes con el formato correcto
    """
    if state:
        only_date = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
        start_date = f'{only_date} 00:00'
        end_date = f'{only_date} 23:59'
        current_day = (datetime.now() - timedelta(days=1)).day
        return start_date, end_date, only_date, current_day
    else:
        date_entered = datetime.today()
        current_day = date_entered.day
        end_date = date(date_entered.year, date_entered.month, 1) - timedelta(days=1)
        start_date = date(end_date.year, end_date.month, 1)
        start_date = start_date.strftime("%d/%m/%Y 00:00")
        end_date = end_date.strftime("%d/%m/%Y 23:59")
        return start_date, end_date, current_day


def verify_zip_or_csv_files(folder_path: str):
    """
    Función encargada de retornar una lista con los nombres
    de los archivos de extensión .zip y .csv en workspace_path
    """
    print('Comprobando si hay archivos comprimidos...'.center(50, '='))
    list_dir = os.listdir(folder_path)
    zip_files = [filename for filename in list_dir if '.zip' in filename]
    if bool(zip_files):
        for file in zip_files:
            with ZipFile(define_path(file), 'r') as current_zip:
                current_zip.extractall(folder_path)
        print(f'{len(zip_files)} Archivos descomprimidos exitosamente')
    sleep(3)
    csv_files = []
    for filename in os.listdir(folder_path):
        if ' ' in filename and '.csv' in filename:
            new_file_name = filename.replace(' ', '_')
            os.renames(define_path(filename), define_path(new_file_name))
            csv_files.append(define_path(new_file_name))
        elif '.csv' in filename:
            csv_files.append(define_path(filename))
    if bool(csv_files):
        print(f'{len(csv_files)} Archivos encontrados como .csv')
        return csv_files
    elif not bool(csv_files):
        print('No se encontraron archivos .csv')
    elif not bool(zip_files) and not bool(csv_files):
        print('No se encontraron archivos .zip')
    elif not bool(zip_files) and not bool(csv_files):
        print('No se encontraron archivos .zip ni .csv')
    return None


def create_and_join_dataframes(csv_files: list,
                               bussiness_id: str,
                               account_id: str) -> DataFrame:
    """
    Función encargada de crear los dataframes para
    cada archivo .csv, si hay dos cuentas iguales las unimos
    """
    df_temp = pd.DataFrame()
    for file in csv_files:
        df = pd.read_csv(file,
                         sep=';',
                         low_memory=False,
                         header=0,
                         encoding='ISO-8859-1')
        df = df.rename(columns={'Merchant Id': 'Id Comercio', 'Account Id': 'Id Cuenta'})
        # Buscamos dentro de cada archivo el usuario y la cuenta a la que pertenecen
        bussiness_id_df = str(df['Id Comercio'].iloc[0])
        account_id_df = str(df['Id Cuenta'].iloc[0])
        if bussiness_id_df == bussiness_id:
            if account_id_df == account_id:
                if df_temp.empty:
                    df_temp = df
                elif not df_temp.empty:
                    df_temp = pd.concat([df_temp, df])
                else:
                    print('ERROR DURANTE LA CREACIÓN DEL DATAFRAME')
    return df_temp


def clean_dataframe(df: DataFrame, type_account: str = None) -> dict:
    """
    Función encargada de procesar el dataframe que recibe
    como parametro y devolverlo según los estandares de la cuenta
    """
    if not df.empty:
        df = df.rename(columns={'Id Comercio': 'Merchant Id',
                                'Id Cuenta': 'Account Id',
                                'Fecha última actualización': 'Update date',
                                'Descripción': 'Description',
                                'Estado': 'Status',
                                'Valor cobrado': 'Charged value'})

        df['Update date'] = df['Update date'].str.slice(start=8, stop=10).astype('int')
        df['Description'] = df['Description'].str.slice(stop=14).str.lower()
        optional_filter = []

        if type_account == '671009':
            df = df[df.Description.isin(['autopagos_mobi', 'autopagos mobi'])]

        elif type_account == '549710':
            df = df[~df.Description.str.contains('home') &
                    ~df.Description.isin(optional_filter) &
                    ~(df.Description == 'Processing pay') &
                    ~df.Reference.str.contains('-')]

        elif type_account == '527424':
            df = df[~df.Description.str.contains('home') &
                    (df.Description.isin(optional_filter))]

        elif type_account == '738826':
            df = df[df.Description.isin(['autopagos_home', 'autopagos home'])]

        elif type_account == '738311':
            df = df[~df.Description.str.contains('movil') &
                    ~((df.Description.isin(['processing pay'])) &
                      (~df.Reference.str.contains('-')))]

        pivot_data = {}
        if not df.empty:
            dates_in_df = df.groupby(['Update date'], as_index=False).sum()
            dates_per_day = [int(dates_in_df.values[_][0]) for _ in range(dates_in_df.shape[0])]

            for day in dates_per_day:
                data_to_add = {}
                df_filtered = df[(df['Update date'] == day)]
                df_approved = df_filtered[(df_filtered.Status.str.contains('APPROVED'))]
                df_declined = df_filtered[(df_filtered.Status.str.contains('DECLINED|ERROR'))]

                if not df_approved.empty:
                    charged_approved = df_approved.pivot_table(
                        values='Charged value',
                        index='Update date',
                        columns=['Description', 'Status'],
                        aggfunc=[sum, 'count'],
                        margins=True,
                        margins_name='TOTAL'
                    )
                    total_values = charged_approved.unstack().xs('TOTAL', level=1)
                    data_to_add['approved_count'] = int(total_values.loc['count'][0])
                    data_to_add['total_values'] = int(total_values.loc['sum'][0])

                if not df_declined.empty:
                    charged_declined = df_declined.pivot_table(
                        values='Charged value',
                        index='Update date',
                        columns='Franchise',
                        aggfunc=['count'],
                        margins=True,
                        margins_name='TOTAL'
                    )
                    franchise_total = charged_declined.xs('TOTAL', axis=0)
                    try:
                        data_to_add['rejectd_PSE'] = int(franchise_total.loc['count', 'PSE'])
                        data_to_add['rejectd_TC'] = int(franchise_total[-1]) - int(franchise_total.loc['count', 'PSE'])
                    except KeyError:
                        data_to_add['rejectd_TC'] = int(franchise_total[-1])

                data_to_add['day'] = day
                pivot_data[day] = data_to_add

        return pivot_data


def show_values(data_to_show: dict, sheet_name: str, account_id: str):
    """Imprime los valores obtenidos por cada cuenta descarga"""
    print(f'\nSHEET NAME: {sheet_name} - ACCOUNT {account_id}\n')
    data_to_print = pd.DataFrame(
        list(data_to_show.values()),
        index=[_ for _ in data_to_show.keys()],
        columns=['approved_count', 'total_values', 'rejectd_PSE', 'rejectd_TC'])
    print(data_to_print)


def update_sheet(data_to_upload: dict, sheet_name: str):
    """
    Actualiza el archivo Pruebapy en Google Sheet
    para actualizar el reporte de Payu
    """
    gc = gspread.service_account(filename='.local/credentials_PayU.json')
    sheet = gc.open('google_sheet').worksheet(sheet_name)
    dates = sheet.col_values(1)
    try:
        for data in data_to_upload.values():
            row_date = dates.index(str(data.get('day'))) + 1
            sheet.batch_update([{
                'range': f'B{row_date}:E{row_date}',
                'values': [[
                    data.get('approved_count'),
                    data.get('total_values'),
                    data.get('rejectd_TC'),
                    data.get('rejectd_PSE')
                ]]}])
    except ValueError:
        print('No se encontro la fecha digitada en la hoja')
