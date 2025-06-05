# app.py

import os
import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD XRP DATA (LOCAL CSV)
# ─────────────────────────────────────────────────────────────────────────────

DATA_PATH = "xrp.csv"

df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
df = df.sort_values("Date").reset_index(drop=True)

# Compute daily returns (%) on the Close price
df["Return"] = df["Close"].pct_change() * 100
df["Return"] = df["Return"].fillna(0)

# Precompute a 30-day rolling volatility (std of returns), but we'll re-filter per range in callback
df["Vol30"] = df["Return"].rolling(window=30, min_periods=1).std()

# ─────────────────────────────────────────────────────────────────────────────
# 2. SET UP DASH
# ─────────────────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="XRP Explorer with Volatility")
server = app.server  # for deployment

# ─────────────────────────────────────────────────────────────────────────────
# 3. LAYOUT (4 CORE COMPONENTS + 4 PLOTS)
# ─────────────────────────────────────────────────────────────────────────────

app.layout = html.Div(
    style={"fontFamily": "Arial, sans‐serif", "margin": "0 2rem"},
    children=[
        html.H1("XRP-USD Explorer (2015–2022)", style={"textAlign": "center"}),
        html.P(
            """
            Explore daily XRP closing prices (USD), overlay a moving average, inspect daily returns,
            and see a 30-day rolling volatility. Use the controls below to pick a date range, specify
            a moving average window, toggle between linear/log scale, or highlight a specific date.
            """,
            style={"fontSize": "1.1rem", "marginBottom": "2rem"},
        ),

        # ────────────── CONTROLS ROW ──────────────
        html.Div(
            style={"display": "flex", "gap": "2rem"},
            children=[
                # 1) DatePickerRange
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Date Range:", style={"fontWeight": "bold"}),
                        dcc.DatePickerRange(
                            id="date-picker-range",
                            min_date_allowed=df["Date"].min().date(),
                            max_date_allowed=df["Date"].max().date(),
                            start_date=(df["Date"].max() - pd.Timedelta(days=180)).date(),
                            end_date=df["Date"].max().date(),
                            display_format="YYYY-MM-DD",
                        ),
                        html.Div(
                            id="date-range-warning",
                            style={"color": "crimson", "marginTop": "0.5rem"},
                        ),
                    ],
                ),

                # 2) Moving Average Slider
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Moving Average Window (days):", style={"fontWeight": "bold"}),
                        dcc.Slider(
                            id="ma-slider",
                            min=1,
                            max=60,
                            step=1,
                            value=7,
                            marks={1: "1", 7: "7", 30: "30", 60: "60"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                        html.Div(
                            id="ma-slider-output",
                            style={"marginTop": "0.5rem", "fontStyle": "italic"},
                        ),
                    ],
                ),

                # 3) Scale Toggle
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Y-Axis Scale:", style={"fontWeight": "bold"}),
                        dcc.RadioItems(
                            id="scale-radio",
                            options=[
                                {"label": "Linear", "value": "linear"},
                                {"label": "Logarithmic", "value": "log"},
                            ],
                            value="linear",
                            labelStyle={"display": "block"},
                            inputStyle={"marginRight": "0.5rem"},
                        ),
                    ],
                ),

                # 4) Highlight Date Input
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Highlight Date (YYYY-MM-DD):", style={"fontWeight": "bold"}),
                        dcc.Input(
                            id="highlight-date",
                            type="text",
                            placeholder="e.g. 2021-02-14",
                            style={"width": "100%", "padding": "0.3rem"},
                        ),
                        html.Div(
                            id="highlight-date-warning",
                            style={"color": "crimson", "marginTop": "0.5rem"},
                        ),
                    ],
                ),
            ],
        ),

        html.Hr(),

        # ────────────── PLOTS ROW ──────────────
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "2rem"},
            children=[
                # (A) Price + MA
                html.Div(
                    children=[
                        html.H3("XRP Close Price + Moving Avg", style={"textAlign": "center"}),
                        dcc.Graph(id="price-ma-chart"),
                        html.P(
                            "Line chart of daily XRP close price (USD), overlaid with the chosen moving average. "
                            "If you highlight a valid date, a vertical red line appears there.",
                            style={"fontSize": "0.9rem", "color": "#555"},
                        ),
                    ],
                ),

                # (B) Histogram of Daily Returns
                html.Div(
                    children=[
                        html.H3("Histogram of Daily Returns (%)", style={"textAlign": "center"}),
                        dcc.Graph(id="returns-histogram"),
                        html.P(
                            "Histogram of daily percentage returns over the selected date range.",
                            style={"fontSize": "0.9rem", "color": "#555"},
                        ),
                    ],
                ),

                # (C) Time Series of Daily Returns
                html.Div(
                    children=[
                        html.H3("XRP Daily Returns Over Time", style={"textAlign": "center"}),
                        dcc.Graph(id="returns-time-chart"),
                        html.P(
                            "Line chart of daily % returns. A red 'X' appears at your highlighted date, if valid.",
                            style={"fontSize": "0.9rem", "color": "#555"},
                        ),
                    ],
                ),

                # (D) Rolling Volatility (30-day)
                html.Div(
                    children=[
                        html.H3("30-Day Rolling Volatility (%)", style={"textAlign": "center"}),
                        dcc.Graph(id="volatility-chart"),
                        html.P(
                            """
                            Displays the 30-day rolling standard deviation of daily returns 
                            (i.e., volatility) over your selected date range.
                            """,
                            style={"fontSize": "0.9rem", "color": "#555"},
                        ),
                    ],
                ),
            ],
        ),

        html.Hr(),

        # ────────────── INSTRUCTIONS ──────────────
        html.Div(
            style={"marginBottom": "2rem"},
            children=[
                html.H4("How to Use This App", style={"textDecoration": "underline"}),
                html.Ul(
                    [
                        html.Li("Select a date range (between 2015-01-22 and 2022-08-23)."),
                        html.Li("Adjust the moving‐average window (1–60 days)."),
                        html.Li("Toggle the price chart’s y-axis between linear or log scale."),
                        html.Li("Optionally enter a highlight date (YYYY-MM-DD). If valid, a red line/marker appears."),
                        html.Li("Hover over plots to see exact values; zoom/pan using the toolbar."),
                    ]
                ),
                html.P(
                    "Source: ‘xrp.csv’ (2015–2022) from Yahoo Finance. App built with Dash & Plotly.",
                    style={"fontSize": "0.85rem", "textAlign": "right", "color": "#777"},
                ),
            ],
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CALLBACKS FOR INTERACTIVITY
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("ma-slider-output", "children"),
    Input("ma-slider", "value"),
)
def update_ma_text(window):
    return f"Using a {window}-day moving average."


@app.callback(
    Output("date-range-warning", "children"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
)
def validate_date_range(start_date, end_date):
    if start_date and end_date:
        sd = pd.to_datetime(start_date)
        ed = pd.to_datetime(end_date)
        if sd > ed:
            return "⚠️ Start date must be on or before end date."
    return ""


@app.callback(
    Output("highlight-date-warning", "children"),
    Input("highlight-date", "value"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
)
def validate_highlight_date(hd_str, start_date, end_date):
    if not hd_str:
        return ""
    # Check format
    try:
        hd = pd.to_datetime(hd_str)
    except:
        return "⚠️ Invalid format; use YYYY-MM-DD."
    # Check in selected range
    sd = pd.to_datetime(start_date)
    ed = pd.to_datetime(end_date)
    if not (sd <= hd <= ed):
        return f"⚠️ Must be between {sd.date()} and {ed.date()}."
    # Check if in data
    if hd not in df["Date"].values:
        return "⚠️ Date not found in dataset."
    return f"Highlighting {hd.date()}."


@app.callback(
    Output("price-ma-chart", "figure"),
    Output("returns-histogram", "figure"),
    Output("returns-time-chart", "figure"),
    Output("volatility-chart", "figure"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
    Input("ma-slider", "value"),
    Input("scale-radio", "value"),
    Input("highlight-date", "value"),
)
def update_all_plots(start_date, end_date, ma_window, scale, highlight_date):
    # 1) Filter by date range
    sd = pd.to_datetime(start_date)
    ed = pd.to_datetime(end_date)
    dff = df[(df["Date"] >= sd) & (df["Date"] <= ed)].copy()

    # Compute MA on Close within this filtered range
    dff["MA"] = dff["Close"].rolling(window=ma_window, min_periods=1).mean()

    # Recompute 30-day volatility on filtered data
    dff["Vol30"] = dff["Return"].rolling(window=30, min_periods=1).std()

    # Parse highlight_date if valid
    highlight_dt = None
    if highlight_date:
        try:
            tmp = pd.to_datetime(highlight_date)
            if tmp in dff["Date"].values:
                highlight_dt = tmp
        except:
            highlight_dt = None

    # ─────────────────────────────────────────────
    # (A) Price + Moving Average Line Chart
    # ─────────────────────────────────────────────
    fig_price = px.line(
        dff,
        x="Date",
        y="Close",
        labels={"Close": "Close Price (USD)", "Date": "Date"},
        title="XRP Close Price",
    )
    fig_price.add_scatter(
        x=dff["Date"],
        y=dff["MA"],
        mode="lines",
        name=f"{ma_window}-day MA",
        line=dict(dash="dash"),
    )
    # If highlight_dt is valid, add vertical line
    if highlight_dt is not None:
        fig_price.add_vline(
            x=highlight_dt,
            line_width=2,
            line_dash="dot",
            line_color="red",
            annotation_text=f"Highlight {highlight_dt.date()}",
            annotation_position="top left",
        )

    fig_price.update_yaxes(type=scale)
    fig_price.update_layout(margin={"l": 50, "r": 20, "t": 50, "b": 50})

    # ─────────────────────────────────────────────
    # (B) Histogram of Returns
    # ─────────────────────────────────────────────
    fig_hist = px.histogram(
        dff,
        x="Return",
        nbins=50,
        labels={"Return": "Daily Return (%)"},
        title="Histogram of Daily Returns",
    )
    fig_hist.update_layout(margin={"l": 50, "r": 20, "t": 50, "b": 50})

    # ─────────────────────────────────────────────
    # (C) Time Series of Daily Returns
    # ─────────────────────────────────────────────
    fig_ret = px.line(
        dff,
        x="Date",
        y="Return",
        labels={"Return": "Daily Return (%)", "Date": "Date"},
        title="XRP Daily Returns Over Time",
    )
    # If highlight_dt is valid, put a red X at that point
    if highlight_dt is not None:
        ret_on_hd = dff.loc[dff["Date"] == highlight_dt, "Return"].iloc[0]
        fig_ret.add_scatter(
            x=[highlight_dt],
            y=[ret_on_hd],
            mode="markers",
            marker=dict(size=12, color="red", symbol="x"),
            name=f"Highlight {highlight_dt.date()}",
            hovertemplate="Date: %{x}<br>Return: %{y:.2f}%",
        )
    fig_ret.update_layout(margin={"l": 50, "r": 20, "t": 50, "b": 50})

    # ─────────────────────────────────────────────
    # (D) 30-Day Rolling Volatility Chart
    # ─────────────────────────────────────────────
    fig_vol = px.line(
        dff,
        x="Date",
        y="Vol30",
        labels={"Vol30": "30-Day Volatility (%)", "Date": "Date"},
        title="30-Day Rolling Volatility of Returns",
    )
    fig_vol.update_layout(margin={"l": 50, "r": 20, "t": 50, "b": 50})

    return fig_price, fig_hist, fig_ret, fig_vol


# ─────────────────────────────────────────────────────────────────────────────
# 5. RUN THE APP
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
