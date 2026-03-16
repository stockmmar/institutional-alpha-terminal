import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import io
import os

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Institutional Alpha Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Dark Theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #0a0b10;
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* KPI Card Styling */
    .kpi-container {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 25px;
    }
    .kpi-card {
        background: linear-gradient(145deg, #151921, #0e1117);
        border: 1px solid #232936;
        border-radius: 12px;
        padding: 20px;
        flex: 1;
        min-width: 200px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #8a8f98;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }
    .kpi-sub {
        font-size: 0.85rem;
        margin-top: 5px;
    }
    .text-cyan { color: #00d4ff; }
    .text-green { color: #00ffa3; }
    .text-red { color: #ff4b5c; }
    .text-gold { color: #ffcc00; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: #0a0b10;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border: none;
        color: #8a8f98;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #00d4ff !important;
        border-bottom: 2px solid #00d4ff !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0a0b10; }
    ::-webkit-scrollbar-thumb { background: #232936; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA ENGINE
# =============================================================================
def generate_sample_file():
    """Creates a sample trades.xlsx if not present."""
    dates = pd.date_range(end=datetime.now(), periods=100)
    data = {
        'date': dates,
        'instrument': np.random.choice(['EURUSD', 'BTCUSD', 'AAPL', 'GOLD', 'SPY'], 100),
        'side': np.random.choice(['Long', 'Short'], 100),
        'entry': np.random.uniform(100, 200, 100),
        'stop': np.random.uniform(90, 110, 100),
        'target': np.random.uniform(210, 300, 100),
        'result': np.random.choice(['Win', 'Loss', 'BE'], 100, p=[0.45, 0.45, 0.1]),
        'rr': np.random.uniform(1.5, 4.0, 100),
        'pnl_r': [],
        'setup': np.random.choice(['Trend Continuation', 'Mean Reversion', 'Breakout'], 100),
        'session': np.random.choice(['London', 'New York', 'Asia'], 100)
    }
    for res in data['result']:
        if res == 'Win': data['pnl_r'].append(np.random.uniform(1.5, 3.5))
        elif res == 'Loss': data['pnl_r'].append(-1.0)
        else: data['pnl_r'].append(0.0)
    
    df = pd.DataFrame(data)
    df.to_excel('trades.xlsx', index=False)

@st.cache_data(ttl=5)
def load_data():
    if not os.path.exists('trades.xlsx'):
        generate_sample_file()
    try:
        df = pd.read_excel('trades.xlsx')
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return None

def calculate_metrics(df):
    if df.empty: return {}
    
    m = {}
    m['total_trades'] = len(df)
    m['wins'] = len(df[df['pnl_r'] > 0])
    m['losses'] = len(df[df['pnl_r'] < 0])
    m['be'] = len(df[df['pnl_r'] == 0])
    
    m['win_rate'] = (m['wins'] / m['total_trades']) * 100
    m['be_rate'] = (m['be'] / m['total_trades']) * 100
    
    wins = df[df['pnl_r'] > 0]['pnl_r']
    losses = df[df['pnl_r'] < 0]['pnl_r']
    
    m['avg_win'] = wins.mean() if not wins.empty else 0
    m['avg_loss'] = losses.mean() if not losses.empty else 0
    m['expectancy'] = df['pnl_r'].mean()
    m['cumulative_r'] = df['pnl_r'].sum()
    m['payoff_ratio'] = abs(m['avg_win'] / m['avg_loss']) if m['avg_loss'] != 0 else 0
    
    gp = wins.sum()
    gl = abs(losses.sum())
    m['profit_factor'] = gp / gl if gl != 0 else gp
    
    df['equity'] = df['pnl_r'].cumsum()
    df['peak'] = df['equity'].cummax()
    df['drawdown'] = df['equity'] - df['peak']
    
    m['max_dd'] = df['drawdown'].min()
    m['recovery_factor'] = abs(m['cumulative_r'] / m['max_dd']) if m['max_dd'] != 0 else 0
    
    # Streaks
    wins_binary = (df['pnl_r'] > 0).astype(int)
    losses_binary = (df['pnl_r'] < 0).astype(int)
    
    def get_max_streak(s):
        return s.groupby((s != s.shift()).cumsum()).cumsum().max()
    
    m['win_streak'] = get_max_streak(wins_binary)
    m['loss_streak'] = get_max_streak(losses_binary)
    
    return m

# =============================================================================
# COMPONENTS
# =============================================================================
def kpi_card(label, value, sub="", color="cyan"):
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value text-{color}">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# MAIN APP
# =============================================================================
def main():
    st.title("🏛️ Institutional Alpha Terminal")
    st.markdown("---")
    
    df_raw = load_data()
    if df_raw is None: return

    # Sidebar Filters
    st.sidebar.title("🎛️ Terminal Controls")
    date_range = st.sidebar.date_input("Period", [df_raw['date'].min(), df_raw['date'].max()])
    instruments = st.sidebar.multiselect("Instrument", df_raw['instrument'].unique(), df_raw['instrument'].unique())
    setups = st.sidebar.multiselect("Setup", df_raw['setup'].unique(), df_raw['setup'].unique())
    sessions = st.sidebar.multiselect("Session", df_raw['session'].unique(), df_raw['session'].unique())
    
    # Apply Filters
    mask = (df_raw['instrument'].isin(instruments)) & (df_raw['setup'].isin(setups)) & (df_raw['session'].isin(sessions))
    if len(date_range) == 2:
        mask &= (df_raw['date'].dt.date >= date_range[0]) & (df_raw['date'].dt.date <= date_range[1])
    
    df = df_raw.loc[mask].copy()
    m = calculate_metrics(df)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # KPI Row 1
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Profit", f"{m['cumulative_r']:.2f} R", f"Trades: {m['total_trades']}", "cyan")
    with c2: kpi_card("Profit Factor", f"{m['profit_factor']:.2f}", f"Payoff: {m['payoff_ratio']:.2f}", "gold")
    with c3: kpi_card("Win Rate", f"{m['win_rate']:.1f}%", f"BE Rate: {m['be_rate']:.1f}%", "green")
    with c4: kpi_card("Expectancy", f"{m['expectancy']:.2f} R", "Average per trade", "cyan")

    # KPI Row 2
    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi_card("Max Drawdown", f"{m['max_dd']:.2f} R", "Depth from peak", "red")
    with c6: kpi_card("Recovery Factor", f"{m['recovery_factor']:.2f}", "Profit / Drawdown", "green")
    with c7: kpi_card("Win Streak", f"{int(m['win_streak'])}", "Consecutive", "green")
    with c8: kpi_card("Loss Streak", f"{int(m['loss_streak'])}", "Consecutive", "red")

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Analysis Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Performance", "⚖️ Risk Analysis", "📊 Distribution", "🔍 Breakdown"])

    with tab1:
        fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig_main.add_trace(go.Scatter(x=df['date'], y=df['equity'], name='Equity', line=dict(color='#00d4ff', width=3), fill='tozeroy'), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=df['date'], y=df['drawdown'], name='Drawdown', line=dict(color='#ff4b5c', width=2), fill='tozeroy'), row=2, col=1)
        fig_main.update_layout(height=600, template="plotly_dark", showlegend=False, margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig_main, use_container_width=True)

        monthly = df.set_index('date').resample('M')['pnl_r'].sum().reset_index()
        fig_monthly = px.bar(monthly, x='date', y='pnl_r', color='pnl_r', color_continuous_scale='RdYlGn', title="Monthly P&L (R)")
        fig_monthly.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_monthly, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            df['rolling_wr'] = (df['pnl_r'] > 0).rolling(10).mean() * 100
            fig_roll = px.line(df, x='date', y='rolling_win_rate' if 'rolling_win_rate' in df else 'rolling_wr', title="Rolling Win Rate (10 Trades)")
            fig_roll.update_traces(line_color='#00ffa3')
            fig_roll.update_layout(template="plotly_dark")
            st.plotly_chart(fig_roll, use_container_width=True)
        with col2:
            df['rolling_exp'] = df['pnl_r'].rolling(10).mean()
            fig_exp = px.line(df, x='date', y='rolling_exp', title="Rolling Expectancy (10 Trades)")
            fig_exp.update_traces(line_color='#ffcc00')
            fig_exp.update_layout(template="plotly_dark")
            st.plotly_chart(fig_exp, use_container_width=True)
            
        st.subheader("Monthly Heatmap")
        df_h = df.copy()
        df_h['Year'] = df_h['date'].dt.year
        df_h['Month'] = df_h['date'].dt.month_name()
        heatmap = df_h.groupby(['Year', 'Month'])['pnl_r'].sum().unstack().fillna(0)
        fig_heat = px.imshow(heatmap, text_auto=".1f", color_continuous_scale='RdYlGn', aspect="auto")
        fig_heat.update_layout(template="plotly_dark")
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab3:
        col3, col4 = st.columns(2)
        with col3:
            fig_dist = px.histogram(df, x="pnl_r", nbins=40, title="Return Distribution (R)", color_discrete_sequence=['#00d4ff'])
            fig_dist.update_layout(template="plotly_dark")
            st.plotly_chart(fig_dist, use_container_width=True)
        with col4:
            # Streak Distribution logic simplified
            streaks = df['pnl_r'].apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'BE')).value_counts()
            fig_pie = px.pie(values=streaks.values, names=streaks.index, title="Outcome Distribution", color_discrete_map={'Win':'#00ffa3', 'Loss':'#ff4b5c', 'BE':'#8a8f98'})
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab4:
        col5, col6 = st.columns(2)
        with col5:
            setup_pnl = df.groupby('setup')['pnl_r'].sum().reset_index()
            st.plotly_chart(px.bar(setup_pnl, x='setup', y='pnl_r', title="PnL by Setup", template="plotly_dark", color='pnl_r'), use_container_width=True)
            inst_pnl = df.groupby('instrument')['pnl_r'].sum().reset_index()
            st.plotly_chart(px.bar(inst_pnl, x='instrument', y='pnl_r', title="PnL by Instrument", template="plotly_dark", color='pnl_r'), use_container_width=True)
        with col6:
            sess_pnl = df.groupby('session')['pnl_r'].sum().reset_index()
            st.plotly_chart(px.bar(sess_pnl, x='session', y='pnl_r', title="PnL by Session", template="plotly_dark", color='pnl_r'), use_container_width=True)
            st.subheader("Trade Data Log")
            st.dataframe(df[['date', 'instrument', 'side', 'result', 'pnl_r', 'setup']].sort_values('date', ascending=False), height=400)

    # Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Export Current View", data=csv, file_name="filtered_trades.csv", mime='text/csv')

if __name__ == "__main__":
    main()