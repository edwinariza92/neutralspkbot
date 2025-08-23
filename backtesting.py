import pandas as pd
import numpy as np
import os

# Obtener la ruta del directorio actual donde está el script
directorio_actual = os.path.dirname(os.path.abspath(__file__))
archivo = os.path.join(directorio_actual, 'SPKUSDT30m.csv')

# Verificar si el archivo existe
if not os.path.exists(archivo):
    print(f"❌ Error: No se encontró el archivo {archivo}")
    print("📁 Archivos disponibles en el directorio:")
    for archivo_en_dir in os.listdir(directorio_actual):
        if archivo_en_dir.endswith('.csv'):
            print(f"   • {archivo_en_dir}")
    exit(1)
try:
    df = pd.read_csv(archivo)
    print(f"✅ Archivo cargado exitosamente: {archivo}") 
except Exception as e:
    print(f"❌ Error al leer el archivo: {e}")
    exit(1)

# Carga tus datos históricos (ajusta el nombre del archivo y columnas si es necesario)
df['close'] = df['close'].astype(float)
df['high'] = df['high'].astype(float)
df['low'] = df['low'].astype(float)

# Indicadores igual que en tu bot
df['ma'] = df['close'].rolling(window=19).mean()
df['std'] = df['close'].rolling(window=19).std()
df['upper'] = df['ma'] + 2 * df['std']
df['lower'] = df['ma'] - 2 * df['std']
df['prev_close'] = df['close'].shift(1)
df['tr1'] = df['high'] - df['low']
df['tr2'] = abs(df['high'] - df['prev_close'])
df['tr3'] = abs(df['low'] - df['prev_close'])
df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
df['atr'] = df['tr'].rolling(window=14).mean()

umbral_volatilidad = 0.02
comision = 0.0004  # 0.04% por trade
resultados = []

posicion = None  # None, 'long', 'short'
precio_entrada = 0
tp = 0
sl = 0

for i in range(20, len(df)):
    close_now = df['close'].iloc[i]
    close_prev = df['close'].iloc[i-1]
    upper_now = df['upper'].iloc[i]
    upper_prev = df['upper'].iloc[i-1]
    lower_now = df['lower'].iloc[i]
    lower_prev = df['lower'].iloc[i-1]
    atr_now = df['atr'].iloc[i]
    filtro_volatilidad = atr_now < umbral_volatilidad

    # Señal de entrada
    if posicion is None:
        if close_prev <= upper_prev and close_now > upper_now and filtro_volatilidad:
            posicion = 'long'
            precio_entrada = close_now
            tp = precio_entrada + atr_now * 2.5
            sl = precio_entrada - atr_now * 1.5
            entry_idx = i
        elif close_prev >= lower_prev and close_now < lower_now and filtro_volatilidad:
            posicion = 'short'
            precio_entrada = close_now
            tp = precio_entrada - atr_now * 2.5
            sl = precio_entrada + atr_now * 1.5
            entry_idx = i
        print(f"i={i}, close_prev={close_prev}, upper_prev={upper_prev}, close_now={close_now}, upper_now={upper_now}, filtro_volatilidad={filtro_volatilidad}")
    # Gestión de la posición
    elif posicion == 'long':
        # ¿Tocó TP?
        if df['high'].iloc[i] >= tp:
            pnl = (tp - precio_entrada) / precio_entrada - comision
            resultados.append({'tipo': 'TP', 'pnl': pnl, 'entrada': precio_entrada, 'salida': tp, 'idx': i})
            posicion = None
        # ¿Tocó SL?
        elif df['low'].iloc[i] <= sl:
            pnl = (sl - precio_entrada) / precio_entrada - comision
            resultados.append({'tipo': 'SL', 'pnl': pnl, 'entrada': precio_entrada, 'salida': sl, 'idx': i})
            posicion = None
    elif posicion == 'short':
        # ¿Tocó TP?
        if df['low'].iloc[i] <= tp:
            pnl = (precio_entrada - tp) / precio_entrada - comision
            resultados.append({'tipo': 'TP', 'pnl': pnl, 'entrada': precio_entrada, 'salida': tp, 'idx': i})
            posicion = None
        # ¿Tocó SL?
        elif df['high'].iloc[i] >= sl:
            pnl = (precio_entrada - sl) / precio_entrada - comision
            resultados.append({'tipo': 'SL', 'pnl': pnl, 'entrada': precio_entrada, 'salida': sl, 'idx': i})
            posicion = None

# Resumen de resultados
resultados_df = pd.DataFrame(resultados)
if resultados_df.empty:
    print("No hubo operaciones para mostrar.")
else:
    print(resultados_df)
    print("Total operaciones:", len(resultados_df))
    print("Ganancia acumulada (%):", resultados_df['pnl'].sum() * 100)
    print("Operaciones ganadoras:", (resultados_df['tipo'] == 'TP').sum())
    print("Operaciones perdedoras:", (resultados_df['tipo'] == 'SL').sum())

    # Opcional: curva de equity
    import matplotlib.pyplot as plt
    resultados_df['equity'] = resultados_df['pnl'].cumsum()
    resultados_df['equity'].plot(title='Evolución del capital (%)')
    plt.show()