from market_tickers import get_ticker, get_default_index
import yfinance as yf

stock = get_ticker("Nvidia")
index = get_default_index("Nvidia")

print(stock, index)

data = yf.download(
    [stock, index],
    start="2022-01-01",
    end="2024-01-01"
)["Close"]

print(data.head())
