import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
from datetime import datetime
import csv
import os
import requests

# ======== CONFIGURACIÓN ========
api_key = 'Lw3sQdyAZcEJ2s522igX6E28ZL629ZL5JJ9UaqLyM7PXeNRLDu30LmPYFNJ4ixAx'
api_secret = 'Adw4DXL2BI9oS4sCJlS3dlBeoJQo6iPezmykfL1bhhm0NQe7aTHpaWULLQ0dYOIt'
symbol = 'SPKUSDT'
intervalo = '30m'
riesgo_pct = 0.03  # 3% de riesgo por operación
umbral_volatilidad = 0.02  # ATR máximo permitido para operar
# ===============================

client = Client(api_key, api_secret)
client.API_URL = 'https://fapi.binance.com/fapi'  # FUTUROS

TELEGRAM_TOKEN = '7857039325:AAFlT3ZZbwttizagdWNqyceO3x-OGZzx2i8'
TELEGRAM_CHAT_ID = '1715798949'

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error enviando notificación Telegram: {e}")

def obtener_datos(symbol, intervalo, limite=100):
    klines = client.futures_klines(symbol=symbol, interval=intervalo, limit=limite)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'close_time', 'quote_asset_volume', 'number_of_trades',
                                       'taker_buy_base', 'taker_buy_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    return df[['close', 'high', 'low']]

def calcular_senal(df, umbral_volatilidad=0.02):
    # Bandas de Bollinger y ATR
    df['ma'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['upper'] = df['ma'] + 2 * df['std']
    df['lower'] = df['ma'] - 2 * df['std']
    df['atr'] = df['close'].rolling(window=14).apply(lambda x: np.mean(np.abs(np.diff(x))), raw=True)
    
    if len(df) < 21:
        return 'neutral'
    
    close_now = df['close'].iloc[-1]
    close_prev = df['close'].iloc[-2]
    upper_now = df['upper'].iloc[-1]
    upper_prev = df['upper'].iloc[-2]
    lower_now = df['lower'].iloc[-1]
    lower_prev = df['lower'].iloc[-2]
    atr_now = df['atr'].iloc[-1]
    
    filtro_volatilidad = atr_now < umbral_volatilidad

    # Señal long: cruce arriba banda superior y filtro de volatilidad
    if close_prev <= upper_prev and close_now > upper_now and filtro_volatilidad:
        return 'long'
    # Señal short: cruce abajo banda inferior y filtro de volatilidad
    elif close_prev >= lower_prev and close_now < lower_now and filtro_volatilidad:
        return 'short'
    else:
        return 'neutral'

def calcular_cantidad_riesgo(saldo_usdt, riesgo_pct, distancia_sl):
    riesgo_usdt = saldo_usdt * riesgo_pct
    if distancia_sl == 0:
        return 0
    cantidad = riesgo_usdt / distancia_sl
    return round(cantidad, 3)

def ejecutar_orden(senal, symbol, cantidad):
    try:
        side = SIDE_BUY if senal == 'long' else SIDE_SELL
        try:
            orden = client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=cantidad
            )
        except Exception as e:
            print(f"❌ Error al crear la orden de mercado: {e}")
            return None, None

        # Verifica que la posición realmente se abrió
        info_pos = client.futures_position_information(symbol=symbol)
        if not info_pos or float(info_pos[0]['positionAmt']) == 0:
            print("❌ La orden fue enviada pero no se abrió posición. Puede ser por cantidad mínima o error de Binance.")
            return None, None

        precio = float(info_pos[0]['entryPrice'])
        print(f"✅ Operación {senal.upper()} ejecutada a {precio}")
        return precio, cantidad

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        enviar_telegram(f"❌ Error inesperado: {e}")

def registrar_operacion(fecha, tipo, precio_entrada, cantidad, tp, sl, resultado=None, pnl=None):
    archivo = 'registro_operaciones_spk.csv'
    existe = os.path.isfile(archivo)
    with open(archivo, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha', 'Tipo', 'Precio Entrada', 'Cantidad', 'Take Profit', 'Stop Loss', 'Resultado', 'PnL'])
        writer.writerow([fecha, tipo, precio_entrada, cantidad, tp, sl, resultado if resultado else "", pnl if pnl is not None else ""])

def obtener_precisiones(symbol):
    info = client.futures_exchange_info()
    cantidad_decimales = 3
    precio_decimales = 3
    for s in info['symbols']:
        if s['symbol'] == symbol:
            for f in s['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = float(f['stepSize'])
                    cantidad_decimales = abs(int(np.log10(step_size)))
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = float(f['tickSize'])
                    precio_decimales = abs(int(np.log10(tick_size)))
    return cantidad_decimales, precio_decimales

def calcular_atr(df, periodo=14):
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['tr'] = df[['high', 'low', 'close']].apply(
        lambda row: max(row['high'] - row['low'], abs(row['high'] - row['close']), abs(row['low'] - row['close'])), axis=1)
    df['atr'] = df['tr'].rolling(window=periodo).mean()
    return df['atr'].iloc[-1]

def notificar_pnl(symbol):
    trades = client.futures_account_trades(symbol=symbol)
    if trades:
        ultimo_trade = trades[-1]
        pnl = float(ultimo_trade.get('realizedPnl', 0))
        enviar_telegram(f"🔔 Posición cerrada en {symbol}. PnL: {pnl:.4f} USDT")
        return pnl
    else:
        enviar_telegram(f"🔔 Posición cerrada en {symbol}. No se pudo obtener el PnL.")
        return None

# ============ LOOP PRINCIPAL ============
ultima_posicion_cerrada = True
datos_ultima_operacion = {}
hubo_posicion_abierta = False
tiempo_ultima_apertura = None

while True:
    df = obtener_datos(symbol, intervalo)

    if len(df) < 51:
        print("⏳ Esperando más datos...")
        time.sleep(60)
        continue

    senal = calcular_senal(df)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Señal detectada: {senal.upper()}")

    info_pos = client.futures_position_information(symbol=symbol)
    if not info_pos:
        print("Sin posición abierta.")
        pos_abierta = 0.0
    else:
        posicion = info_pos[0]
        pos_abierta = float(posicion['positionAmt'])
        if pos_abierta != 0:
            print(f"Posición actual: cantidad={posicion['positionAmt']}, precio entrada={posicion['entryPrice']}, PnL={posicion['unRealizedProfit']}")
        else:
            print("Sin posición abierta.")

    # Cancelar órdenes TP/SL pendientes si no hay posición abierta
    if pos_abierta == 0:
        ordenes_abiertas = client.futures_get_open_orders(symbol=symbol)
        for orden in ordenes_abiertas:
            if orden['type'] in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                try:
                    client.futures_cancel_order(symbol=symbol, orderId=orden['orderId'])
                    print(f"🗑️ Orden pendiente cancelada: {orden['type']}")
                except Exception as e:
                    print(f"❌ Error al cancelar orden pendiente: {e}")

    # Evitar duplicar posiciones en la misma dirección
    if (senal == 'long' and pos_abierta > 0) or (senal == 'short' and pos_abierta < 0):
        print("⚠️ Ya hay una posición abierta en la misma dirección. No se ejecuta nueva orden.")
        time.sleep(60)
        continue

    # === Gestión dinámica y avanzada ===
    if senal in ['long', 'short'] and pos_abierta == 0:
        atr = calcular_atr(df)
        if atr > umbral_volatilidad:
            print("Mercado demasiado volátil, no se opera.")
            time.sleep(60)
            continue

        # Gestión de riesgo avanzada
        balance = client.futures_account_balance()
        saldo_usdt = next((float(b['balance']) for b in balance if b['asset'] == 'USDT'), 0)

        # Calcula distancia SL en precio (ajustable)
        precio_actual = float(df['close'].iloc[-1])
        # Calcula ATR para la última vela
        atr = df['atr'].iloc[-1]

        if senal == 'long':
            sl = precio_actual - atr * 1.5
            tp = precio_actual + atr * 2
            distancia_sl = atr * 1.5
        else:
            sl = precio_actual + atr * 1.5
            tp = precio_actual - atr * 2
            distancia_sl = atr * 1.5

        # Redondeo de precios y cantidad según precisión del símbolo
        cantidad_decimales, precio_decimales = obtener_precisiones(symbol)
        cantidad = calcular_cantidad_riesgo(saldo_usdt, riesgo_pct, distancia_sl)
        cantidad = round(cantidad, cantidad_decimales)
        sl = round(sl, precio_decimales)
        tp = round(tp, precio_decimales)

        # Ajuste para cumplir el mínimo notional de Binance
        notional = precio_actual * cantidad
        if notional < 5:
            cantidad_minima = round(5 / precio_actual, cantidad_decimales)
            print(f"⚠️ Ajustando cantidad al mínimo permitido: {cantidad_minima} contratos ({5:.2f} USDT)")
            cantidad = cantidad_minima
            notional = precio_actual * cantidad

        if notional < 5:
            print(f"⚠️ Orden rechazada: el valor notional ({notional:.2f} USDT) sigue siendo menor al mínimo permitido por Binance (5 USDT).")
            continue

        print(f"💰 Saldo disponible: {saldo_usdt} USDT | Usando {cantidad} contratos para la operación ({riesgo_pct*100:.1f}% de riesgo, SL={sl:.4f}, TP={tp:.4f})")

        precio_entrada, cantidad_real = ejecutar_orden(senal, symbol, cantidad)

        if precio_entrada:
            ultima_posicion_cerrada = False
            hubo_posicion_abierta = True
            tiempo_ultima_apertura = time.time()
            datos_ultima_operacion = {
                "senal": senal,
                "precio_entrada": precio_entrada,
                "cantidad_real": cantidad_real,
                "tp": tp,
                "sl": sl
            }
            # Cancelar órdenes TP/SL abiertas antes de crear nuevas
            ordenes_abiertas = client.futures_get_open_orders(symbol=symbol)
            for orden in ordenes_abiertas:
                if orden['type'] in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                    try:
                        client.futures_cancel_order(symbol=symbol, orderId=orden['orderId'])
                    except Exception as e:
                        print(f"❌ Error al cancelar orden previa: {e}")

            # Crear TP/SL según la dirección de la señal
            try:
                if senal == 'long':
                    client.futures_create_order(
                        symbol=symbol,
                        side='SELL',
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        quantity=cantidad_real,
                        reduceOnly=True
                    )
                    client.futures_create_order(
                        symbol=symbol,
                        side='SELL',
                        type='STOP_MARKET',
                        stopPrice=sl,
                        quantity=cantidad_real,
                        reduceOnly=True
                    )
                else:
                    client.futures_create_order(
                        symbol=symbol,
                        side='BUY',
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        quantity=cantidad_real,
                        reduceOnly=True
                    )
                    client.futures_create_order(
                        symbol=symbol,
                        side='BUY',
                        type='STOP_MARKET',
                        stopPrice=sl,
                        quantity=cantidad_real,
                        reduceOnly=True
                    )
            except Exception as e:
                print(f"❌ Error al crear TP/SL: {e}")

            print(f"✅ Orden {senal.upper()} ejecutada correctamente.")
            print(f"🎯 Take Profit: {tp:.4f} | 🛑 Stop Loss: {sl:.4f}")
            enviar_telegram(f"✅ Orden {senal.upper()} ejecutada a {precio_entrada}.\nTP: {tp} | SL: {sl}")
        else:
            print(f"❌ No se pudo ejecutar la orden {senal.upper()}.")

    # Verificar cierre de posición solo si ha pasado suficiente tiempo desde la apertura
    tiempo_actual = time.time()
    if (pos_abierta == 0 and 
        not ultima_posicion_cerrada and 
        datos_ultima_operacion and 
        hubo_posicion_abierta and
        tiempo_ultima_apertura and
        (tiempo_actual - tiempo_ultima_apertura) > 10):  # Esperar al menos 10 segundos
        
        # Espera unos segundos para que Binance registre el trade de cierre real
        time.sleep(5)
        trades = client.futures_account_trades(symbol=symbol)
        if trades:
            ultimo_trade = trades[-1]
            pnl = float(ultimo_trade.get('realizedPnl', 0))
            precio_ejecucion = float(ultimo_trade['price'])
            tp = datos_ultima_operacion["tp"]
            sl = datos_ultima_operacion["sl"]
            senal_original = datos_ultima_operacion["senal"]
            
            # Verificar que el trade realmente corresponde a la posición que abrimos
            trade_time = int(ultimo_trade['time']) / 1000  # Convertir a segundos
            if trade_time > tiempo_ultima_apertura:
                # Lógica mejorada para determinar TP vs SL
                # Para LONG: TP > precio_entrada, SL < precio_entrada
                # Para SHORT: TP < precio_entrada, SL > precio_entrada
                precio_entrada = datos_ultima_operacion["precio_entrada"]
                
                if senal_original == 'long':
                    # En posición LONG, si el precio de ejecución es mayor al precio de entrada, probablemente fue TP
                    if precio_ejecucion > precio_entrada:
                        resultado = "TP"
                        enviar_telegram(f"🎉 ¡Take Profit alcanzado en {symbol}! Ganancia: {pnl:.4f} USDT")
                    else:
                        resultado = "SL"
                        enviar_telegram(f"⚠️ Stop Loss alcanzado en {symbol}. Pérdida: {pnl:.4f} USDT")
                else:  # senal_original == 'short'
                    # En posición SHORT, si el precio de ejecución es menor al precio de entrada, probablemente fue TP
                    if precio_ejecucion < precio_entrada:
                        resultado = "TP"
                        enviar_telegram(f"🎉 ¡Take Profit alcanzado en {symbol}! Ganancia: {pnl:.4f} USDT")
                    else:
                        resultado = "SL"
                        enviar_telegram(f"⚠️ Stop Loss alcanzado en {symbol}. Pérdida: {pnl:.4f} USDT")
                
                print(f"📊 Detalles del cierre: Precio entrada={precio_entrada:.4f}, Precio ejecución={precio_ejecucion:.4f}, {resultado}")
            else:
                resultado = ""
                pnl = None
                print("⚠️ Trade detectado no corresponde a la posición actual")
        else:
            resultado = ""
            pnl = None
            enviar_telegram(f"🔔 Posición cerrada en {symbol}. No se pudo obtener el PnL.")

        registrar_operacion(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            datos_ultima_operacion["senal"],
            datos_ultima_operacion["precio_entrada"],
            datos_ultima_operacion["cantidad_real"],
            datos_ultima_operacion["tp"],
            datos_ultima_operacion["sl"],
            resultado=resultado,
            pnl=pnl
        )
        ultima_posicion_cerrada = True
        datos_ultima_operacion = {}
        hubo_posicion_abierta = False
        tiempo_ultima_apertura = None

    time.sleep(60)  # Esperar antes de la siguiente verificación
