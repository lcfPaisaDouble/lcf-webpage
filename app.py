from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

# Initializing App
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server

# Read Trade Log to Pandas
tradeLog = pd.read_csv('tradeLog.log')
tradeLog = tradeLog.iloc[::-1]  # Inverting the dataframe

# Creating App layout
app.title = 'LCF'
app.layout = dbc.Container([

    # Dropdown for Ticker and Indicators
    dbc.Row([
        dbc.Col([
                dcc.Dropdown(
                    id='ticker-name',
                    placeholder='Select Ticker Name',
                    value='ETHUSD',
                    clearable=False,
                    searchable=False,
                    options=[
                        {'label': 'ETHUSD', 'value': 'ETHUSD'},
                        {'label': 'TQQQ', 'value': 'TQQQ'}
                    ],
                )
        ]),
        dbc.Col([
            dcc.Dropdown(
                id='indicator',
                placeholder='Select Indicator',
                multi=True,
                clearable=True,
                value=None,
                searchable=False,
                options=[
                    {'label': 'SMA 15 day', 'value': 'sma15day'},
                    {'label': '200 day SMA', 'value': 'baseSMA'}
                ],

            )
        ])
    ]),

    # Ticker Graph
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='graph',
            )
            ]),
        ]),

    # Platform Dropdown for balance
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='platform',
                placeholder='Select Platform',
                clearable=False,
                value='Binance',
                options=[
                    {'label': 'Alpaca', 'value': 'Alpaca'},
                    {'label': 'Binance', 'value': 'Binance'}
                ],
            )
        ]),
        dbc.Col([
            html.H2('TradeLog')
            ], style={'text-align': 'center'})
    ]),

    # Balance Graph and Trade Log
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='balance',
            )
        ], style={'width': '49%', 'display': 'inline-block'}),
        dbc.Col([
            dash_table.DataTable(tradeLog.to_dict('records'),
                                 [{"name": i, "id": i} for i in tradeLog.columns],
                                 style_table={
                                    'height': 450,
                                    'overflow': 'scroll',
                                    },
                                 style_cell={
                                    'textAlign': 'left',
                                 }
                                 )

        ], style={'width': '49%', 'display': 'incline-block'})
    ], style={'display': 'flex'})
], fluid=True,)

# Callback for Ticker Graph
@app.callback(
    Output('graph', 'figure'),
    [Input('ticker-name', 'value'),
     Input('indicator', 'value')]
)
def stock_details(ticker_name, indicator):

    # Check if indicator is selected
    if type(indicator) == str:
        indicator = [indicator]

    # Reading ticker database
    price_con = sqlite3.connect('tradingData.db')
    price_cur = price_con.cursor()

    # Check for distinct ticker
    price_cur.execute("SELECT DISTINCT ticker FROM cryptoData")
    allTickerName = price_cur.fetchall()
    allTickerName = pd.DataFrame(allTickerName)

    # Reading balance & trade database
    update_con = sqlite3.connect('miscData.db')
    update_cur = update_con.cursor()

    # Ticker selected from site
    ticker = ticker_name

    # Parse data from ticker database
    price_cur.execute("SELECT openTimestamp,close FROM cryptoData WHERE ticker=:ticker", {"ticker": ticker})
    data = price_cur.fetchall()
    data = pd.DataFrame(data, columns=['Time', 'Close'])

    # Parse data for buy transaction
    update_cur.execute("SELECT timestamp,price FROM miscData WHERE side='buy' AND ticker=:ticker",
                       {"ticker": ticker})
    transaction_buy = update_cur.fetchall()
    transaction_buy = pd.DataFrame(transaction_buy, columns=['Time','Price'])

    # Parse data for sell transaction
    update_cur.execute("SELECT timestamp,price FROM miscData WHERE side='sell' AND ticker=:ticker",
                       {"ticker": ticker})
    transaction_sell = update_cur.fetchall()
    transaction_sell = pd.DataFrame(transaction_sell, columns=['Time','Price'])

    # Plot ticker and transaction data as per ticker selected
    fig = px.line(data, x="Time", y="Close")
    fig.add_trace(go.Scatter(x=transaction_buy["Time"], y=transaction_buy["Price"],
                             mode='markers', marker=dict(size=10, color='#FF0000'),
                             name='buy'))
    fig.add_trace(go.Scatter(x=transaction_sell["Time"], y=transaction_sell["Price"],
                             mode='markers', marker=dict(size=10, color='#00FF00'),
                             name='sell'))
    # Return empty if indicator is empty
    # Graph won't be plotted if fig is not returned before the next for loop
    if indicator is None:
        return fig

    # Plotting selected indicator
    for ind in indicator:
        if ind == 'sma15day':
            price_cur.execute("SELECT openTimestamp,sma15day FROM cryptoData WHERE ticker=:ticker", {"ticker": ticker})
            indicator_data = price_cur.fetchall()
            indicator_data = pd.DataFrame(indicator_data, columns=['Time', 'SMA15Day'])
            fig.add_trace(go.Scatter(x=indicator_data["Time"], y=indicator_data["SMA15Day"],
                                     name='SMA 15d', line=dict(color='#FFA500')))

        if ind == 'baseSMA':
            price_cur.execute("SELECT openTimestamp,baseSMA FROM cryptoData WHERE ticker=:ticker", {"ticker": ticker})
            indicator_data = price_cur.fetchall()
            indicator_data = pd.DataFrame(indicator_data, columns=['Time', 'baseSMA'])
            fig.add_trace(go.Scatter(x=indicator_data["Time"], y=indicator_data["baseSMA"],
                                     name='SMA 200d', line=dict(color='#023020')))

    # Blue Line for Main Ticker Line
    fig['data'][0]['line']['color'] = '#0000FF'

    return fig

# Callback for balance graph
@app.callback(
    Output('balance', 'figure'),
    [Input('platform', 'value')]
)
def platform_details(platform):
    platform = [platform]
    for plat in platform:
        update_con = sqlite3.connect('miscData.db')
        update_cur = update_con.cursor()
        update_cur.execute("SELECT timestamp,balance FROM miscData WHERE side='' AND platform=:platform",
                           {"platform": plat})
        balance = update_cur.fetchall()
        balance = pd.DataFrame(balance, columns=['Time', 'Balance'])
        fig = px.line(balance, x="Time", y="Balance")
        return fig


if __name__ == '__main__':
    app.run_server(debug=True)
