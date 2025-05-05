import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import os
from colorama import Fore, Style, init
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Inicializar colorama para los colores en la consola
init()

# Configurar sesión con reintentos
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Lista de símbolos de divisas
FOREX_SYMBOLS = [
    {'symbol': 'ARS=X', 'name': 'Dólar Oficial'},
    {'symbol': 'EURARS=X', 'name': 'Euro'}
]

# Lista completa de ADRs argentinos en NYSE
STOCKS = [
    # Bancos y Financieras
    ('GGAL', 'NYSE'),      # Grupo Financiero Galicia
    ('BMA', 'NYSE'),       # Banco Macro
    ('BBAR', 'NYSE'),      # BBVA Banco Francés
    ('SUPV', 'NYSE'),      # Grupo Supervielle
    ('BSMX', 'NYSE'),      # Banco Santander México (relacionado con Argentina)
    
    # Energía y Petróleo
    ('YPF', 'NYSE'),       # YPF
    ('PAM', 'NYSE'),       # Pampa Energía
    ('EDN', 'NYSE'),       # Edenor
    
    # Tecnología y Telecomunicaciones
    ('TEO', 'NYSE'),       # Telecom Argentina
    ('GLOB', 'NYSE'),      # Globant (tecnología)
    ('MELI', 'NYSE'),      # MercadoLibre
    
    # Industria y Materiales
    ('TS', 'NYSE'),        # Tenaris
    ('TX', 'NYSE'),        # Ternium
    
    # Real Estate y Construcción
    ('IRS', 'NYSE'),       # IRSA
    ('IRCP', 'NYSE'),      # IRSA Propiedades Comerciales
    
    # Agricultura y Alimentos
    ('CRESY', 'NYSE'),     # Cresud
    
    # Infraestructura y Transporte
    ('TGS', 'NYSE'),       # Transportadora Gas del Sur
    ('VSH', 'NYSE'),       # Vishay (con operaciones significativas en Argentina)
]

def clear_screen():
    """Limpiar la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_ticker_data(symbol, session):
    """Obtener datos de un ticker con manejo de errores"""
    try:
        ticker = yf.Ticker(symbol)
        ticker._session = session
        info = ticker.info
        
        if info and 'regularMarketPrice' in info:
            return info
    except Exception as e:
        print(f"Error al obtener datos para {symbol}: {str(e)}")
    return None

def get_forex_data():
    """Obtener datos de tipos de cambio"""
    data = []
    session = create_session()
    
    for forex in FOREX_SYMBOLS:
        try:
            info = get_ticker_data(forex['symbol'], session)
            if info:
                current_price = info['regularMarketPrice']
                previous_close = info.get('regularMarketPreviousClose', current_price)
                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close != 0 else 0
                
                data.append({
                    'Símbolo': forex['name'],
                    'Precio': current_price,
                    'Cambio $': change,
                    'Cambio %': change_percent
                })
        except Exception as e:
            print(f"Error al procesar datos para {forex['symbol']}: {str(e)}")
    
    return pd.DataFrame(data)

def get_stock_data(dolar_rate=None):
    """Obtener datos actualizados de las acciones"""
    data = []
    session = create_session()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {
            executor.submit(get_ticker_data, symbol, session): (symbol, market)
            for symbol, market in STOCKS
        }
        
        for future in as_completed(future_to_stock):
            symbol, market = future_to_stock[future]
            try:
                info = future.result()
                if info:
                    current_price = info['regularMarketPrice']
                    previous_close = info.get('regularMarketPreviousClose', current_price)
                    change = current_price - previous_close
                    change_percent = (change / previous_close * 100) if previous_close != 0 else 0
                    
                    # Convertir a pesos si tenemos la tasa de cambio y es del mercado NYSE
                    if dolar_rate and market == 'NYSE':
                        current_price *= dolar_rate
                        change *= dolar_rate
                    
                    company_name = info.get('shortName', info.get('longName', ''))
                    
                    data.append({
                        'Símbolo': symbol,
                        'Nombre': company_name,
                        'Precio': current_price,
                        'Cambio $': change,
                        'Cambio %': change_percent,
                        'Volumen': info.get('regularMarketVolume', 0),
                        'Mercado': market
                    })
            except Exception as e:
                print(f"Error al procesar datos para {symbol}: {str(e)}")
    
    return pd.DataFrame(data)

def display_stock_row(row):
    """Mostrar una fila de datos de acción con formato"""
    symbol = row['Símbolo']
    name = row['Nombre']
    price = row['Precio']
    change = row['Cambio $']
    change_percent = row['Cambio %']
    volume = row['Volumen']
    market = row['Mercado']
    
    color = Fore.GREEN if change >= 0 else Fore.RED
    market_color = Fore.YELLOW if market == 'NYSE' else Fore.WHITE
    
    # Mostrar símbolo y nombre de la empresa
    print(f"{market_color}{symbol:<10}{Style.RESET_ALL}", end='')
    if name:
        print(f"{Fore.CYAN}{name[:30]:<31}{Style.RESET_ALL}", end='')
    else:
        print(" " * 31, end='')
    
    # Mostrar precio y cambios
    print(f"${price:,.2f} ", end='')
    print(f"{color}{change:+,.2f} ({change_percent:+.2f}%){Style.RESET_ALL}", end='')
    print(f" Vol: {volume:,}")

def display_data(forex_df, stocks_df):
    """Mostrar los datos en la consola con formato"""
    clear_screen()
    print(f"\n{Fore.CYAN}=== TIPOS DE CAMBIO ==={Style.RESET_ALL}")
    print(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not forex_df.empty:
        for _, row in forex_df.iterrows():
            symbol = row['Símbolo']
            price = row['Precio']
            change = row['Cambio $']
            change_percent = row['Cambio %']
            
            color = Fore.GREEN if change >= 0 else Fore.RED
            
            print(f"{Fore.WHITE}{symbol:<12}{Style.RESET_ALL}", end='')
            print(f"${price:,.2f} ", end='')
            print(f"{color}{change:+,.2f} ({change_percent:+.2f}%){Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}No hay datos disponibles de tipos de cambio{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}=== MERCADO DE VALORES ARGENTINO ==={Style.RESET_ALL}")
    
    if not stocks_df.empty:
        # Mostrar acciones NYSE
        print(f"\n{Fore.YELLOW}Acciones argentinas en NYSE (en pesos){Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}Organizado por sectores:{Style.RESET_ALL}\n")
        
        nyse_stocks = stocks_df[stocks_df['Mercado'] == 'NYSE'].sort_values('Símbolo')
        for _, row in nyse_stocks.iterrows():
            display_stock_row(row)
    else:
        print(f"\n{Fore.RED}No hay datos disponibles del mercado de valores{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Presiona Ctrl+C para detener el programa{Style.RESET_ALL}")

def main():
    """Función principal que ejecuta el monitoreo en tiempo real"""
    print("Iniciando monitoreo del mercado argentino y tipos de cambio...")
    
    try:
        while True:
            try:
                # Obtener datos de forex primero para tener la tasa de cambio
                forex_df = get_forex_data()
                
                # Obtener tasa de cambio del dólar si está disponible
                dolar_rate = None
                if not forex_df.empty:
                    dolar_data = forex_df[forex_df['Símbolo'] == 'Dólar Oficial']
                    if not dolar_data.empty:
                        dolar_rate = dolar_data.iloc[0]['Precio']
                
                # Obtener datos de acciones
                stocks_df = get_stock_data(dolar_rate)
                
                # Mostrar datos
                display_data(forex_df, stocks_df)
                
                # Esperar antes de la siguiente actualización
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\nMonitoreo finalizado.")
                break
            except Exception as e:
                print(f"\nError inesperado: {str(e)}")
                print("Reintentando en 5 segundos...")
                time.sleep(5)
    
    except KeyboardInterrupt:
        print("\nMonitoreo finalizado.")

if __name__ == "__main__":
    main()