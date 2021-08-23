#!/bin/env python

import sys, os, requests
from datetime import datetime
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------------------

# Stellar parameters
HORIZON='https://horizon.stellar.org'
HORIZON_TESTNET='https://horizon-testnet.stellar.org'
SRV=HORIZON

# SMA time frame
WINDOW = 20

# Assets

assets = dict()
assets["XLM"] = Asset("XLM")
assets["ETH"] = Asset("ETH", "GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR")
assets["BTC"] = Asset("BTC", "GAUTUYY2THLF7SGITDFMXJVYH3LHDSMGEAKSBU267M2K7A3W543CKUEF")

BASE = "ETH"
COUNTER = "XLM"

# ------------------------------------------------------------------------------

def trades_to_dataframe(trade_aggregation):
    """
    Convert the stellar trade aggregation to a panda data frame.
    """

    # dict_keys(['timestamp', 'trade_count', 'base_volume', 'counter_volume', 'avg', 'high', 'high_r', 'low', 'low_r', 'open', 'open_r', 'close', 'close_r'])
    _df = list(map(lambda el: {
        "datetime": datetime.fromtimestamp(int(el["timestamp"])/1000),
        "open": float(el["open"]),
        "high": float(el["high"]),
        "low": float(el["low"]),
        "close": float(el["close"]),
        "volume": float(el["counter_volume"])
        }, trade_aggregation["_embedded"]["records"]))

    df = pd.DataFrame.from_dict(_df)
    df['sma'] = df['close'].rolling(WINDOW).mean()
    df['std'] = df['close'].rolling(WINDOW).std(ddof = 0)

    return df

def plot_trades(df):
    """
    Plot the trading data frame.
    """

    # Create subplots with 2 rows; top for candlestick price, and bottom for bar volume
    fig = make_subplots(rows = 2, cols = 1, shared_xaxes = True, subplot_titles = ('Asset price', 'Volume'), vertical_spacing = 0.1, row_width = [0.2, 0.7])

    # ----------------
    # Candlestick plot
    fig.add_trace(
        go.Candlestick(x=df["datetime"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"])
    )

    # Moving average
    fig.add_trace(go.Scatter(x = df['datetime'],
            y = df['sma'],
            line_color = 'black',
            name = 'sma'),
        row = 1, col = 1)

    # Upper bound
    fig.add_trace(go.Scatter(x = df['datetime'],
            y = df['sma'] + (df['std'] * 2),
            line_color = 'gray',
            line = {'dash': 'dash'},
            name = 'upper band',
            opacity = 0.5),
        row = 1, col = 1)

    # Lower bound fill in between with parameter 'fill': 'tonexty'
    fig.add_trace(go.Scatter(x = df['datetime'],
            y = df['sma'] - (df['std'] * 2),
            line_color = 'gray',
            line = {'dash': 'dash'},
            fill = 'tonexty',
            name = 'lower band',
            opacity = 0.5),
        row = 1, col = 1)

    # ----------------
    # Volume Plot

    fig.add_trace(go.Bar(x = df['datetime'], y = df['volume'], showlegend=False),
        row = 2, col = 1)

    # Remove range slider; (short time frame)
    fig.update(layout_xaxis_rangeslider_visible=False)

    # Show figure
    fig.show()

def main(argv=sys.argv):
    server = Server(horizon_url=SRV)

    tr_b = server.trade_aggregations(assets[BASE], assets[COUNTER], 86400000, round(datetime.timestamp(datetime(2021,3,1))*1000))
    tr_b.limit(200)
    tr = tr_b.call()

    df = trades_to_dataframe(tr)
    counter_balance = 100
    base_balance = 0
    print("Balances: {} base; {} counter".format(base_balance, counter_balance))
    for i in df.index:
        bollinger_high = df["sma"][i] + 2*df["std"][i]
        bollinger_low = df["sma"][i] - 2*df["std"][i]
        close = df["close"][i]
        dt = df["datetime"][i]
        if close >= bollinger_high:
            print("SELL on {} at {}".format(dt, close))
            counter_balance += base_balance * close
            base_balance = 0
        elif close <= bollinger_low:
            print("BUY on {} at {}".format(dt, close))
            base_balance += counter_balance / close
            counter_balance = 0

    print("Balances: {} base; {} counter".format(base_balance, counter_balance))

    # plot_trades(df)

if __name__ == "__main__":
    main()
