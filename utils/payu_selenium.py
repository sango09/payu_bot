# Python
from time import sleep

# Selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Environment variables
import environ

env = environ.Env()
env.read_env('.local/.env')


class PayuSelenium:
    """
    Clase encargada de buscar y descargar
    los reportes en PayU filtrando por las fecha de inicio y fin
    """

    def __init__(self, path_workspace: str,
                 initial_date: str = None,
                 final_date: str = None,
                 distinct_number: str = None,
                 report_month: bool = None):

        self.login_url = 'https://secure.payulatam.com/login.zul'
        self.error_login_url = 'https://secure.payulatam.com/login.zul?login_error=1'
        self.success_login_url = 'https://secure.payulatam.com/reports/'
        self.password = env('PASSWORD_PAYU')
        self.initial_date = initial_date
        self.final_date = final_date
        self.current_day = distinct_number
        self.report_month = report_month
        op = webdriver.ChromeOptions()
        download_path = {'download.default_directory': path_workspace}
        op.add_experimental_option('prefs', download_path)
        self.driver = webdriver.Chrome(options=op, executable_path='files/chromedriver.exe')
        self.driver.maximize_window()

    def login(self, username: str, account_name: str):
        """Ingreso de credenciales de acceso"""
        print('---------------------------------------------')
        print(f'Iniciando Sesión en la cuenta {account_name}')
        driver = self.driver
        if self.is_element_present(By.CLASS_NAME, 'initialMessage'):
            print('Logout failed')
            self.logout()
            self.login(username, account_name)
        driver.refresh()
        driver.implicitly_wait(10)
        driver.get(self.login_url)
        driver.find_element_by_name('j_username').send_keys(username)
        driver.find_element_by_name('j_password').send_keys(self.password)
        driver.find_element_by_id('btnenviar').click()
        if driver.current_url == self.success_login_url:
            print('Inicio de sesión exitoso')
        elif driver.current_url == self.error_login_url:
            print('Contraseña incorrecta')
        else:
            print(f'URL actual {driver.current_url}')
            answer = input('¿Desa continuar? (Y/N): ').lower()
            if answer == 'n' or answer != 'y':
                raise SystemExit
            else:
                pass

    def account(self, account_name: str, number_account: str):
        """Esta encargado de desplazarse por la pagina de PayU
        y descargar los archivos .csv correspondientes a las fechas ingresadas
        """
        print(f'Descargando reporte #{number_account}')
        driver = self.driver
        driver.find_element_by_xpath(f'//option[contains(text(),"{number_account}")]').click()
        Select(driver.find_element_by_name('listboxDateType')).select_by_value('lastUpdateDate')

        account_initial_date = driver.find_element_by_name('dateboxStartDate')
        account_initial_date.clear()
        account_initial_date.send_keys(self.initial_date)

        account_finish_date = driver.find_element_by_name('dateboxEndDate')
        account_finish_date.clear()
        account_finish_date.send_keys(self.final_date)
        driver.implicitly_wait(2)

        # Si es informe de mes se cambia el Estado de 'Todos' a 'Aprobados'
        if self.report_month:
            listbox_state = Select(self.driver.find_element_by_name('listboxState'))
            listbox_state.select_by_visible_text('Approved')

        driver.find_element_by_xpath('//button[contains(text(),"Download")]').click()
        driver.implicitly_wait(3)

        if self.is_element_present(By.CLASS_NAME, 'z-loading-indicator'):
            print('Procesando')
            while self.is_element_present(By.CLASS_NAME, 'z-loading-indicator'):
                sleep(1)
        try:
            if self.is_element_present(By.CSS_SELECTOR, 'div.z-window-modal'):
                if self.report_month:
                    file_name = f'{account_name}_MES'
                    self.current_day = 'MES'
                else:
                    file_name = f'{account_name}_{self.current_day}'
                input_file_name = driver.find_element_by_name('textboxReportName')
                input_file_name.clear()
                input_file_name.send_keys(file_name)
                driver.implicitly_wait(5)
                print('El informe se descargara en formato .zip')

                driver.find_element_by_xpath(
                    '//div[@class="message"]//button[contains(text(),"Continue")]').click()
                driver.implicitly_wait(3)
                driver.find_element_by_class_name('z-messagebox-btn').click()
                await_data = True
                print('Obteniendo reporte comprimido')

                while await_data:
                    try:
                        btn_report = driver.find_element_by_partial_link_text(f'{account_name}_{self.current_day}')
                        driver.execute_script("arguments[0].click();", btn_report)
                        print('Archivos comprimido descargado')
                        await_data = False
                    except NoSuchElementException:
                        # Esperando que el archivo sea generado
                        pass
        except ElementNotInteractableException:
            driver.refresh()
            self.account(account_name, number_account)

        if self.is_element_present(By.XPATH, '//div[@class="z-window-highlighted z-window-highlighted-shadow"]'):
            driver.find_element_by_xpath(
                '//div[@class="z-window-highlighted z-window-highlighted-shadow"]')
            driver.find_element_by_xpath('//td/button[contains(text(),"OK")]').click()
            print('No se encontraron datos relacionados con la consulta')

        else:
            print('El informe fue descargado')
        self.logout()

    def logout(self):
        """Cerrar sesión de la cuenta activa"""
        logout = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, '//a[contains(text(),"Logout")]'))
        )
        self.driver.execute_script('arguments[0].click();', logout)

    def is_element_present(self, how, what) -> bool:
        """Verifica si un elemento existe dentro del DOM"""
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def close_connection(self):
        """
        Cierra el navegador y finaliza el uso de recursos
        por parte de selenium
        """
        self.driver.quit()
