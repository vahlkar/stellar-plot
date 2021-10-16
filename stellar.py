#!/bin/env python

import sys, os, requests
from datetime import datetime, timedelta
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

# Aggregation resolution
resolutions = {"1m": 60000, "5m": 300000, "15m": 900000, "1h": 3600000,
        "1d": 86400000, "1w": 604800000}

DEFAULT_RES = "1d"
DEFAULT_INTERVAL = 30

# Assets

assets = dict()
assets["XLM"] = Asset("XLM")
assets["ETH"] = Asset("ETH", "GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR")
assets["BTC"] = Asset("BTC", "GAUTUYY2THLF7SGITDFMXJVYH3LHDSMGEAKSBU267M2K7A3W543CKUEF")
assets["EURT"] = Asset("EURT", "GAP5LETOV6YIE62YAM56STDANPRDO7ZFDBGSNHJQIYGGKSMOZAHOOS2S")
assets["USD"] = Asset("USD", "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX")
assets["MOBI"] = Asset("MOBI", "GA6HCMBLTZS5VYYBCATRBRZ3BZJMAFUDKYYF6AH6MVCMGWMRDNSWJPIH")
assets["LTC"] = Asset("LTC", "GC5LOR3BK6KIOK7GKAUD5EGHQCMFOGHJTC7I3ELB66PTDFXORC2VM5LP")
assets["SHX"] = Asset("SHX", "GDSTRSHXHGJ7ZIVRBXEYE5Q74XUVCUSEKEBR7UCHEUUEK72N7I7KJ6JH")
assets["SLT"] = Asset("SLT", "GCKA6K5PCQ6PNF5RQBF7PQDJWRHO6UOGFMRLK3DYHDOI244V47XKQ4GP")
assets["USDT"] = Asset("USDT", "GCQTGZQQ5G4PTM2GL7CDIFKUBIPEC52BROAQIAPW53XBRJVN6ZJVTG6V")
assets["BAT"] = Asset("BAT", "GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR")
assets["LINK"] = Asset("LINK", "GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR")
assets["KIN"] = Asset("KIN", "GBDEVU63Y6NTHJQQZIKVTC23NWLQVP3WJ2RI2OTSJTNYOIGICST6DUXR")
assets["PALL"] = Asset("PALL", "GCQ5ZYECTNYW6BZ47AZN6M5BXKV7ZZ24XPNHPSYZVUDVK7CIITOMPALL")
assets["PLAT"] = Asset("PLAT", "GBIMVJJJOTAKJYWJIY5YEXDZ4QIWQZLRJ4BXVHKH6EXWQ3WAEYBTPLAT")
assets["GOLD"] = Asset("GOLD", "GBC5ZGK6MQU3XG5Y72SXPA7P5R5NHYT2475SNEJB2U3EQ6J56QLVGOLD")
assets["SLVR"] = Asset("SLVR", "GBZVELEQD3WBN3R3VAG64HVBDOZ76ZL6QPLSFGKWPFED33Q3234NSLVR")
assets["AQUA"] = Asset("AQUA", "GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67AQUA")
# assets[""] = Asset("", "")

# ------------------------------------------------------------------------------

def trades_to_dataframe(records):
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
        }, records))

    df = pd.DataFrame.from_dict(_df)
    df['sma'] = df['close'].rolling(WINDOW).mean()
    df['std'] = df['close'].rolling(WINDOW).std(ddof = 0)

    return df

def plot_trades(df, base, counter):
    """
    Plot the trading data frame.
    """

    # Create subplots with 2 rows; top for candlestick price, and bottom for bar volume
    fig = make_subplots(rows = 2, cols = 1, shared_xaxes = True, subplot_titles = ('{}/{} price'.format(counter,base), 'Volume'), x_title = "Date", vertical_spacing = 0.1, row_width = [0.2, 0.7])

    # ----------------
    # Candlestick plot
    fig.add_trace(
        go.Candlestick(x=df["datetime"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="trades"),
        row = 1, col = 1)

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

    fig.add_trace(go.Bar(x = df['datetime'], y = df['volume'], showlegend=False, name="trade volume"),
        row = 2, col = 1)

    # Remove range slider; (short time frame)
    fig.update(layout_xaxis_rangeslider_visible=False)

    fig.update_yaxes(title_text=counter, row=1, col=1)
    fig.update_yaxes(title_text=base, row=2, col=1)

    # Show figure
    fig.show()

def test_strategy(df, base, counter):
    COUNTER_START = 100
    counter_balance = COUNTER_START
    base_balance = 0
    print("Balances: {} base; {} counter".format(base_balance, counter_balance))
    trades = 0
    profit = 0
    for i in df.index:
        bollinger_high = df["sma"][i] + 2*df["std"][i]
        bollinger_low = df["sma"][i] - 2*df["std"][i]
        close = df["close"][i]
        dt = df["datetime"][i]
        if close >= bollinger_high and base_balance > 0:
            print("On {} SELL {} {} for {} {} at {} {}/{}".format(dt, base_balance, base, base_balance*close, counter, close, counter, base))
            counter_balance += base_balance * close
            base_balance = 0
            profit = 100*(counter_balance / COUNTER_START - 1)
            trades += 1
        elif close <= bollinger_low and counter_balance > 0:
            print("On {} BUY {} {} for {} {} at {} {}/{}".format(dt, counter_balance / close, base, counter_balance, counter, close, counter, base))
            base_balance += counter_balance / close
            counter_balance = 0
            trades += 1
    print("Balances: {} {}; {} {}; Total trades: {}; Profit: {:+.2f}%".format(base_balance, base, counter_balance, counter, trades, profit))

def check_known_asset(code):
    if code not in assets.keys():
        print("{} is not a known asset!".format(code))
        exit(10)

def help(argv):
    USAGE = "Usage: {} base counter [resolution] [start] [end]"
    print(USAGE.format(argv[0]))

def main(argv=sys.argv):
    server = Server(horizon_url=SRV)

    if len(argv) > 6 or len(argv) < 3:
        help(argv)
        exit(0)

    base = argv[1].strip().upper()
    counter = argv[2].strip().upper()
    res = resolutions[argv[3]] if len(argv) > 3 else resolutions[DEFAULT_RES]
    end = datetime.strptime(argv[5],"%Y-%m-%d") if len(argv) > 5 else datetime(datetime.today().year, datetime.today().month, datetime.today().day)
    start = datetime.strptime(argv[4],"%Y-%m-%d") if len(argv) > 4 else end - timedelta(days=DEFAULT_INTERVAL)

    check_known_asset(base)
    check_known_asset(counter)

    # tr_b = server.trade_aggregations(assets[base], assets[counter], 86400000, round(datetime.timestamp(datetime(2021,3,26)))*1000, offset=22*60*60*1000)
    total_periods = round((datetime.timestamp(end)-datetime.timestamp(start))*1000/res)
    offset = 0
    trs = []
    while offset < total_periods:
        limit = round(min(200, abs(total_periods-offset)))
        print("Loading {} periods from {}.".format(limit, start + timedelta(milliseconds=res*offset)))
        tr_b = server.trade_aggregations(assets[base], assets[counter], res, round(datetime.timestamp(start)*1000)+res*offset)
        tr_b.limit(limit)
        tr = tr_b.call()
        trs += tr["_embedded"]["records"]
        offset += limit

    df = trades_to_dataframe(trs)
    print("Plotting data.")
    plot_trades(df, base, counter)
    print("Testing strategy.")
    test_strategy(df, base, counter)

if __name__ == "__main__":
    main()
