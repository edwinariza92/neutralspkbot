from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta

api_key = 'Lw3sQdyAZcEJ2s522igX6E28ZL629ZL5JJ9UaqLyM7PXeNRLDu30LmPYFNJ4ixAx'
api_secret = 'Adw4DXL2BI9oS4sCJlS3dlBeoJQo6iPezmykfL1bhhm0NQe7aTHpaWULLQ0dYOIt'
client = Client(api_key, api_secret)

symbol = 'SPKUSDT'
interval = Client.KLINE_INTERVAL_30MINUTE

# Fechas de inicio y fin (últimas 3 semanas)
end_time = datetime.now()
start_time = end_time - timedelta(weeks=3)

# Descargar datos
klines = client.futures_historical_klines(
    symbol=symbol,
    interval=interval,
    start_str=start_time.strftime("%d %b %Y %H:%M:%S"),
    end_str=end_time.strftime("%d %b %Y %H:%M:%S")
)

# Guardar como CSV
df = pd.DataFrame(klines, columns=[
    'timestamp', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_asset_volume', 'number_of_trades',
    'taker_buy_base', 'taker_buy_quote', 'ignore'
])
df.to_csv('SPKUSDT30m.csv', index=False)
print("✅ Archivo SPKUSDT30m.csv guardado correctamente.")