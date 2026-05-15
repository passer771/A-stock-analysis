# -*- coding: utf-8 -*-
"""
=========================================
   📊 A股智能分析系统 v2.0
   🛠 技术栈: Python + Streamlit + Plotly + AkShare
   
   依赖安装: pip install streamlit akshare plotly pandas numpy
   
   A股特色功能:
   - 支持6位纯数字代码输入
   - 红涨绿跌配色
   - 涨跌停价格计算
   - 主力资金流向
   - 量价确认信号
=========================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import akshare as ak  # A股数据源
import datetime
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

# ===================== 页面配置 =====================
st.set_page_config(
    page_title="📊 A股智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== 样式美化 =====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #E53935;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
    }
    .stButton>button {
        width: 100%;
        background: #E53935;
        color: white;
    }
    /* A股涨红跌绿样式覆盖 */
    .up-color { color: #E53935 !important; }
    .down-color { color: #4CAF50 !important; }
</style>
""", unsafe_allow_html=True)

# ===================== 辅助函数 =====================

def calculate_date_range(period_str):
    """
    将时间范围字符串转换为开始和结束日期
    A股时间范围映射
    """
    today = datetime.date.today()
    period_days = {
        "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, 
        "2y": 730, "5y": 1825
    }
    days = period_days.get(period_str, 365)
    start_date = (today - timedelta(days=days)).strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')
    return start_date, end_date


@st.cache_data(ttl=3600)
def load_stock_data(symbol, period="1y"):
    """
    使用 AkShare 获取A股历史K线数据
    
    参数:
        symbol: 6位A股代码，如 "600519"（茅台）、"000001"（平安）
        period: 时间范围，"1mo","3mo","6mo","1y","2y","5y"
    
    返回:
        DataFrame，列名统一为英文：Date, Open, Close, High, Low, Volume, Amount等
        或者 (None, error_message)
    """
    try:
        # 计算日期范围
        start_date, end_date = calculate_date_range(period)
        
        # 判断交易所：沪市以6开头，科创板以688开头；深市以0、3开头
        if symbol.startswith('6') and not symbol.startswith('688'):
            market = "上海主板"
        elif symbol.startswith('688'):
            market = "科创板"
        elif symbol.startswith('000') or symbol.startswith('001'):
            market = "深圳主板"
        elif symbol.startswith('002'):
            market = "中小板"
        elif symbol.startswith('300'):
            market = "创业板"
        else:
            market = "深圳主板"
        
        # 使用 akshare 获取日K线数据
        # akshare 返回的列名：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",    # 日线
            start_date=start_date,
            end_date=end_date,
            adjust=""          # 不复权
        )
        
        if df is None or df.empty:
            return None, f"❌ 未找到股票代码: {symbol}"
        
        # 重命名列名为英文（兼容原有逻辑）
        column_mapping = {
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume',
            '成交额': 'Amount',
            '振幅': 'Amplitude',
            '涨跌幅': 'Pct_Change',
            '涨跌额': 'Change',
            '换手率': 'Turnover'
        }
        df = df.rename(columns=column_mapping)
        
        # 将日期列转换为datetime并设为索引
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
        
        # 按日期排序
        df = df.sort_index()
        
        return df, None
        
    except Exception as e:
        return None, f"❌ 加载失败: {str(e)}"


def get_stock_info(symbol):
    """
    使用 AkShare 获取A股基本面信息
    
    参数:
        symbol: 6位A股代码
    
    返回:
        dict: 包含名称、行业、市值、PE等信息的字典
    """
    try:
        # 获取个股信息
        info_df = ak.stock_individual_info_em(symbol=symbol)
        
        # 转换为字典格式
        info_dict = dict(zip(info_df['item'], info_df['value']))
        
        # 提取需要的信息
        result = {
            'name': info_dict.get('股票名称', symbol),
            'industry': info_dict.get('行业', 'N/A'),
            'market_cap': info_dict.get('总市值', 'N/A'),
            'pe_ratio': info_dict.get('市盈率-动态', 'N/A'),
            'total_shares': info_dict.get('总股本', 'N/A'),
            'float_shares': info_dict.get('流通股本', 'N/A'),
            'high_52w': info_dict.get('52周最高', 'N/A'),
            'low_52w': info_dict.get('52周最低', 'N/A'),
            'listing_date': info_dict.get('上市时间', 'N/A'),
        }
        
        return result
        
    except Exception as e:
        # 如果获取失败，返回基本信息
        return {
            'name': symbol,
            'industry': 'N/A',
            'market_cap': 'N/A',
            'pe_ratio': 'N/A',
            'total_shares': 'N/A',
            'float_shares': 'N/A',
            'high_52w': 'N/A',
            'low_52w': 'N/A',
            'listing_date': 'N/A',
        }


def get_fund_flow(symbol):
    """
    获取A股资金流向数据
    
    参数:
        symbol: 6位A股代码
    
    返回:
        DataFrame: 包含主力净流入、散户净流入等数据
    """
    try:
        # 判断市场
        if symbol.startswith('6') or symbol.startswith('9'):
            market = "sh"
        else:
            market = "sz"
        
        # 获取资金流向
        df = ak.stock_individual_fund_flow(stock=symbol, market=market)
        return df
    except Exception as e:
        return None


def calculate_limit_prices(df):
    """
    计算涨跌停价格
    
    参数:
        df: 包含前收盘价的DataFrame
    
    返回:
        dict: 包含涨停价、跌停价、涨跌幅限制
    """
    try:
        latest = df.iloc[-1]
        prev_close = df['Close'].iloc[-2]  # 前一日收盘价
        
        # 判断股票类型
        name = get_stock_info(df.name if hasattr(df, 'name') else '')['name']
        
        # 判断涨跌停幅度
        if 'ST' in str(name) or '*ST' in str(name):
            limit_pct = 5  # ST股5%
        elif symbol.startswith('688'):
            limit_pct = 20  # 科创板20%
        elif symbol.startswith('300'):
            limit_pct = 20  # 创业板20%
        else:
            limit_pct = 10  # 普通A股10%
        
        upper_limit = round(prev_close * (1 + limit_pct / 100), 2)
        lower_limit = round(prev_close * (1 - limit_pct / 100), 2)
        
        return {
            'upper_limit': upper_limit,
            'lower_limit': lower_limit,
            'limit_pct': limit_pct,
            'prev_close': prev_close
        }
    except:
        return None


def calculate_technical_indicators(df):
    """
    计算常用技术指标
    """
    df = df.copy()
    
    # 移动平均线
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 布林带
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * bb_std
    df['BB_Lower'] = df['BB_Middle'] - 2 * bb_std
    
    # RSI (相对强弱指标)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # 成交量移动平均
    df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
    
    # 波动率
    df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * 100
    
    return df


def plot_candlestick_chart(df, symbol, indicators=None):
    """
    绘制K线图和技术指标（A股红涨绿跌配色）
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol} - K线图", "成交量", "RSI / MACD")
    )
    
    # A股配色：涨(收盘>开盘)红色，跌绿色
    # Plotly默认是涨绿跌红，需要反转
    colors_increase = '#E53935'  # 红色（涨）
    colors_decrease = '#4CAF50'  # 绿色（跌）
    
    # K线图 - 设置A股配色
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="K线",
            showlegend=False,
            increasing_line_color=colors_increase,    # 涨红色
            decreasing_line_color=colors_decrease,    # 跌绿色
            increasing_fill_color=colors_increase,
            decreasing_fill_color=colors_decrease
        ),
        row=1, col=1
    )
    
    # 移动平均线
    if indicators and 'MA' in indicators:
        colors = {'MA5': '#FF6B6B', 'MA10': '#4ECDC4', 'MA20': '#45B7D1', 'MA60': '#96CEB4'}
        for ma in ['MA5', 'MA10', 'MA20', 'MA60']:
            if ma in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index, y=df[ma],
                        mode='lines',
                        name=ma,
                        line=dict(color=colors.get(ma, '#888'), width=1)
                    ),
                    row=1, col=1
                )
    
    # 布林带
    if indicators and 'BB' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['BB_Upper'],
                mode='lines',
                name='布林上轨',
                line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
                showlegend=True
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['BB_Lower'],
                mode='lines',
                name='布林下轨',
                line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
                fill='tonexty',
                fillcolor='rgba(173, 216, 230, 0.1)',
                showlegend=True
            ),
            row=1, col=1
        )
    
    # 成交量柱状图 - A股红涨绿跌
    colors_vol = ['#E53935' if close >= open else '#4CAF50' 
                  for close, open in zip(df['Close'], df['Open'])]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df['Volume'],
            name='成交量',
            marker_color=colors_vol,
            opacity=0.7
        ),
        row=2, col=1
    )
    
    # RSI
    if indicators and 'RSI' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['RSI'],
                mode='lines',
                name='RSI',
                line=dict(color='#FF9800', width=2)
            ),
            row=3, col=1
        )
        # RSI 参考线
        fig.add_hline(y=70, line_dash="dash", line_color="#E53935", row=3, col=1)  # 红色超买
        fig.add_hline(y=30, line_dash="dash", line_color="#4CAF50", row=3, col=1)  # 绿色超卖
    
    # MACD - A股红涨绿跌
    if indicators and 'MACD' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['MACD'],
                mode='lines',
                name='MACD',
                line=dict(color='#2196F3', width=2)
            ),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['MACD_Signal'],
                mode='lines',
                name='MACD Signal',
                line=dict(color='#FF5722', width=2)
            ),
            row=3, col=1
        )
        # MACD 柱状图 - 正值红色，负值绿色
        colors_macd = ['#E53935' if v >= 0 else '#4CAF50' for v in df['MACD_Hist']]
        fig.add_trace(
            go.Bar(
                x=df.index, y=df['MACD_Hist'],
                name='MACD Hist',
                marker_color=colors_macd,
                opacity=0.5
            ),
            row=3, col=1
        )
    
    # 更新布局
    fig.update_layout(
        template='plotly_dark',
        height=800,
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode='x unified',
        xaxis_rangeslider_visible=False
    )
    
    fig.update_xaxes(title_text="日期", row=3, col=1)
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_yaxes(title_text="指标值", row=3, col=1)
    
    return fig


def generate_signal(df, symbol=""):
    """
    生成交易信号（优化版：量价确认）
    
    优化逻辑：
    - 均线金叉/死叉：需要当日成交量 > 5日均量才算有效信号
    - RSI：结合趋势判断，趋势中RSI超买超卖标准不同
    - MACD：零轴以上金叉才看多，零轴以下死叉才看空
    - 布林带：带宽收缩时突破更有意义
    - 新增涨跌停风险提示
    """
    signals = []
    
    # 确保有足够的数据
    if len(df) < 25:
        signals.append(("⚪ 数据不足", "历史数据不足25天，无法生成完整信号", "neutral"))
        return signals
    
    # 最近的数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # ========== 1. 均线金叉/死叉（量价确认） ==========
    today_vol = latest['Volume']
    vol_ma5 = latest['Volume_MA5']
    has_volume_confirm = today_vol > vol_ma5 if pd.notna(vol_ma5) else False
    
    if latest['MA5'] > latest['MA20'] and prev['MA5'] <= prev['MA20']:
        if has_volume_confirm:
            signals.append(("🔴 买入信号", "【量价齐升】5日均线上穿20日均线 + 成交量放大", "positive"))
        else:
            signals.append(("🟡 观望信号", "5日均线金叉20日均线，但成交量未放大", "neutral"))
    elif latest['MA5'] < latest['MA20'] and prev['MA5'] >= prev['MA20']:
        if has_volume_confirm:
            signals.append(("🟢 卖出信号", "【量价齐跌】5日均线下穿20日均线 + 成交量放大", "negative"))
        else:
            signals.append(("🟡 观望信号", "5日均线死叉20日均线，但成交量未放大", "neutral"))
    
    # ========== 2. RSI 超买/超卖（趋势结合判断） ==========
    trend_up = latest['Close'] > latest['MA20']  # 上升趋势
    trend_down = latest['Close'] < latest['MA20']  # 下降趋势
    
    if trend_up and latest['RSI'] > 80:
        signals.append(("🟠 超买风险", f"上升趋势中RSI={latest['RSI']:.1f}>80，注意回调风险", "negative"))
    elif trend_down and latest['RSI'] < 20:
        signals.append(("🔵 超卖机会", f"下降趋势中RSI={latest['RSI']:.1f}<20，可能存在反弹机会", "positive"))
    elif latest['RSI'] < 30:
        signals.append(("🔵 超卖信号", f"RSI={latest['RSI']:.1f}<30，处于超卖区", "positive"))
    elif latest['RSI'] > 70:
        signals.append(("🟠 超买信号", f"RSI={latest['RSI']:.1f}>70，处于超买区", "negative"))
    
    # ========== 3. MACD 金叉/死叉（零轴过滤） ==========
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        if latest['MACD'] > 0:
            signals.append(("🔴 强势金叉", "MACD零轴上方金叉，多头信号较强", "positive"))
        else:
            signals.append(("🟡 弱势金叉", "MACD零轴下方金叉，反弹力度有限", "neutral"))
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        if latest['MACD'] < 0:
            signals.append(("🟢 弱势死叉", "MACD零轴下方死叉，空头信号较弱", "neutral"))
        else:
            signals.append(("🟠 强势死叉", "MACD零轴上方死叉，注意回调风险", "negative"))
    
    # ========== 4. 布林带（带宽收缩判断） ==========
    if 'BB_Upper' in latest and 'BB_Lower' in latest:
        bb_width = (latest['BB_Upper'] - latest['BB_Lower']) / latest['BB_Middle']
        bb_width_20 = df['BB_Upper'].sub(df['BB_Lower']).div(df['BB_Middle']).rolling(20).min()
        bb_width_min = bb_width_20.iloc[-1] if pd.notna(bb_width_20.iloc[-1]) else bb_width
        
        # 布林带收缩（处于近20日最低30%范围）
        is_squeezed = bb_width <= bb_width_min * 1.3 if pd.notna(bb_width_min) else False
        
        if latest['Close'] <= latest['BB_Lower'] * 1.02:
            if is_squeezed:
                signals.append(("🔵 布林下轨反弹", "股价触及布林带下轨+带宽收缩，反弹概率大", "positive"))
            else:
                signals.append(("🔵 超跌信号", "股价触及布林带下轨，可能存在反弹机会", "positive"))
        elif latest['Close'] >= latest['BB_Upper'] * 0.98:
            if is_squeezed:
                signals.append(("🟠 布林突破", "股价触及布林带上轨+带宽收缩，突破概率大，注意假突破", "neutral"))
            else:
                signals.append(("🟠 超涨信号", "股价触及布林带上轨，注意回调风险", "negative"))
    
    # ========== 5. 涨跌停风险提示 ==========
    try:
        pct_change = abs(latest.get('Pct_Change', 0))
        name = get_stock_info(symbol).get('name', '')
        
        # 判断涨跌幅限制
        if 'ST' in str(name) or '*ST' in str(name):
            limit = 5
        elif symbol.startswith('688') or symbol.startswith('300'):
            limit = 20
        else:
            limit = 10
        
        # 接近涨停（>9.5%或接近限制）
        if pct_change >= limit * 0.95:
            signals.append(("⚠️ 涨停风险", f"接近涨停价（{limit}%），注意炸板风险", "negative"))
        elif pct_change <= -limit * 0.95:
            signals.append(("⚠️ 跌停风险", f"接近跌停价（-{limit}%），注意流动性风险", "negative"))
    except:
        pass
    
    if not signals:
        signals.append(("⚪ 无明确信号", "当前无强烈交易信号，建议观望", "neutral"))
    
    return signals


# ===================== 全局变量（用于涨跌停计算） =====================
symbol = "600519"  # 默认贵州茅台

# ===================== 主程序 =====================

def main():
    global symbol
    
    # 侧边栏
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/stock.png", width=80)
        st.markdown("## 📊 A股分析系统")
        st.markdown("---")
        
        # 股票代码输入（A股6位代码）
        ticker_input = st.text_input(
            "🔍 输入6位A股代码",
            value="600519",
            help="输入6位A股代码，如：\n600519(茅台)\n000001(平安)\n300750(宁德时代)\n688981(中芯国际)"
        ).strip()
        
        # 输入校验：必须是6位数字
        if ticker_input:
            if len(ticker_input) == 6 and ticker_input.isdigit():
                symbol = ticker_input
            else:
                st.warning("⚠️ 请输入6位数字代码")
                symbol = "600519"  # 默认值
        else:
            symbol = "600519"
        
        # 时间周期选择（本地化）
        period = st.selectbox(
            "📅 选择时间范围",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=3,
            format_func=lambda x: {
                "1mo": "1个月", "3mo": "3个月", "6mo": "6个月",
                "1y": "1年", "2y": "2年", "5y": "5年"
            }.get(x, x)
        )
        
        # 技术指标选择
        st.markdown("### 📐 技术指标")
        indicators = []
        if st.checkbox("移动平均线 (MA)", value=True):
            indicators.extend(['MA5', 'MA10', 'MA20', 'MA60'])
        if st.checkbox("布林带 (BB)", value=True):
            indicators.append('BB')
        if st.checkbox("RSI", value=True):
            indicators.append('RSI')
        if st.checkbox("MACD", value=True):
            indicators.append('MACD')
        
        # 启动按钮
        analyze_btn = st.button("🚀 开始分析", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📌 快速示例（点击切换）")
        quick_stocks = [
            ("600519", "贵州茅台"),
            ("300750", "宁德时代"),
            ("002594", "比亚迪"),
            ("601318", "中国平安"),
            ("600036", "招商银行"),
            ("688981", "中芯国际"),
        ]
        
        # 分两列显示
        for i in range(0, len(quick_stocks), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(quick_stocks):
                    code, name = quick_stocks[i + j]
                    if cols[j].button(f"{code}\n{name[:4]}", key=f"quick_{code}", use_container_width=True):
                        symbol = code
                        analyze_btn = True
    
    # 主界面
    st.markdown('<h1 class="main-header">📊 A股智能分析系统</h1>', unsafe_allow_html=True)
    
    if not analyze_btn:
        # 欢迎页面
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("📈 **实时行情**\n\n获取A股股票实时数据")
        with col2:
            st.success("📐 **技术分析**\n\nMA, MACD, RSI, 布林带等")
        with col3:
            st.warning("🔔 **智能信号**\n\n量价确认的买卖信号")
        
        st.markdown("---")
        st.markdown("### 🏆 A股热门股票速览")
        
        # A股热门股票（减少到5只避免限流）
        hot_stocks = [
            ("600519", "贵州茅台"),
            ("300750", "宁德时代"),
            ("002594", "比亚迪"),
            ("601318", "中国平安"),
            ("688981", "中芯国际"),
        ]
        
        cols = st.columns(5)
        for i, (code, name) in enumerate(hot_stocks):
            with cols[i]:
                try:
                    data, err = load_stock_data(code, "5d")
                    if data is not None and len(data) >= 2:
                        price = data['Close'].iloc[-1]
                        change = data['Close'].iloc[-1] - data['Close'].iloc[-2]
                        pct = (change / data['Close'].iloc[-2]) * 100
                        # A股红涨绿跌
                        color = "#E53935" if change >= 0 else "#4CAF50"
                        arrow = "↑" if change >= 0 else "↓"
                        st.markdown(f"""
                        <div style="text-align:center; padding:10px; background:#f0f2f6; border-radius:10px; margin:5px;">
                            <h6>{name}</h6>
                            <h5>{code}</h5>
                            <h4>¥{price:.2f}</h4>
                            <p style="color:{color}; font-weight:bold;">{arrow}{abs(change):.2f} ({pct:+.2f}%)</p>
                        </div>
                        """, unsafe_allow_html=True)
                except:
                    st.markdown(f"""
                    <div style="text-align:center; padding:10px; background:#f0f2f6; border-radius:10px; margin:5px;">
                        <h6>{name}</h6>
                        <h5>{code}</h5>
                        <p>加载中...</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        return
    
    # ========== 核心分析逻辑 ==========
    
    # 显示加载状态
    with st.spinner(f"🔍 正在加载 {symbol} 数据..."):
        df, error = load_stock_data(symbol, period)
    
    if error:
        st.error(error)
        st.info("💡 提示：A股代码为6位数字，如贵州茅台→600519，中国平安→601318")
        return
    
    if df is None or df.empty:
        st.error("❌ 未获取到数据，请检查股票代码")
        return
    
    # 计算技术指标
    df = calculate_technical_indicators(df)
    
    # 获取公司信息
    info = get_stock_info(symbol)
    
    # ==================== 顶部信息卡片 ====================
    
    st.markdown(f"## 🏢 {info['name']} ({symbol})")
    
    # 基本信息行（增加换手率）
    latest = df.iloc[-1]
    latest_price = df['Close'].iloc[-1]
    price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
    price_pct = (price_change / df['Close'].iloc[-2]) * 100
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        # 当前价格 - A股用¥
        st.metric(
            "当前价格",
            f"¥{latest_price:.2f}",
            f"{price_change:+.2f} ({price_pct:+.2f}%)",
            delta_color="normal"
        )
    
    with col2:
        st.metric("开盘价", f"¥{df['Open'].iloc[-1]:.2f}")
    
    with col3:
        st.metric("最高价", f"¥{df['High'].iloc[-1]:.2f}")
    
    with col4:
        st.metric("最低价", f"¥{df['Low'].iloc[-1]:.2f}")
    
    with col5:
        # 成交量格式化
        vol = df['Volume'].iloc[-1]
        if vol >= 100000000:
            vol_str = f"{vol/100000000:.2f}亿"
        elif vol >= 10000:
            vol_str = f"{vol/10000:.2f}万"
        else:
            vol_str = f"{vol:.0f}"
        st.metric("成交量", vol_str)
    
    with col6:
        # 换手率
        turnover = latest.get('Turnover', 0)
        st.metric("换手率", f"{turnover:.2f}%" if pd.notna(turnover) else "N/A")
    
    # 涨跌停价格显示
    limit_info = calculate_limit_prices(df)
    if limit_info:
        st.markdown(f"""
        <div style="padding:10px; background:#f5f5f5; border-radius:8px; margin:10px 0;">
            <span style="font-weight:bold;">📌 涨跌停提示：</span>
            涨停价 <span style="color:#E53935;font-weight:bold;">¥{limit_info['upper_limit']:.2f}</span> 
            ({limit_info['limit_pct']}%) | 
            跌停价 <span style="color:#4CAF50;font-weight:bold;">¥{limit_info['lower_limit']:.2f}</span> 
            (-{limit_info['limit_pct']}%) | 
            前收价 ¥{limit_info['prev_close']:.2f}
        </div>
        """, unsafe_allow_html=True)
    
    # 基本面信息
    if info:
        with st.expander("📋 公司基本面信息", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("行业", info['industry'])
            col2.metric("总市值", info['market_cap'] if info['market_cap'] != 'N/A' else "N/A")
            col3.metric("市盈率(PE)", info['pe_ratio'] if info['pe_ratio'] != 'N/A' else "N/A")
            col4.metric("上市时间", info['listing_date'] if info['listing_date'] != 'N/A' else "N/A")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总股本", info['total_shares'] if info['total_shares'] != 'N/A' else "N/A")
            col2.metric("流通股本", info['float_shares'] if info['float_shares'] != 'N/A' else "N/A")
            col3.metric("52周最高", f"¥{info['high_52w']}" if info['high_52w'] != 'N/A' else "N/A")
            col4.metric("52周最低", f"¥{info['low_52w']}" if info['low_52w'] != 'N/A' else "N/A")
    
    # ==================== 资金动向 ====================
    st.markdown("---")
    st.markdown("### 💰 资金动向")
    
    fund_flow_data = get_fund_flow(symbol)
    if fund_flow_data is not None and len(fund_flow_data) > 0:
        # 取最近5天的资金流向
        recent_flow = fund_flow_data.tail(5)
        col1, col2, col3 = st.columns(3)
        
        # 计算主力净流入和散户净流入（根据数据结构调整）
        try:
            # 尝试不同的列名
            if '主力净流入' in recent_flow.columns:
                main_net = recent_flow['主力净流入'].iloc[-1]
                retail_net = recent_flow['散户净流入'].iloc[-1] if '散户净流入' in recent_flow.columns else 0
            elif '主力资金净流入' in recent_flow.columns:
                main_net = recent_flow['主力资金净流入'].iloc[-1]
                retail_net = recent_flow['散户资金净流入'].iloc[-1] if '散户资金净流入' in recent_flow.columns else 0
            else:
                # 使用第一列作为净流入
                net_col = recent_flow.columns[1] if len(recent_flow.columns) > 1 else recent_flow.columns[0]
                main_net = recent_flow[net_col].iloc[-1]
                retail_net = 0
            
            # 格式化显示
            def format_amount(val):
                if abs(val) >= 100000000:
                    return f"{val/100000000:.2f}亿"
                elif abs(val) >= 10000:
                    return f"{val/10000:.2f}万"
                else:
                    return f"{val:.2f}"
            
            main_color = "#E53935" if main_net >= 0 else "#4CAF50"
            retail_color = "#4CAF50" if retail_net >= 0 else "#E53935"
            
            with col1:
                st.markdown(f"""
                <div style="padding:15px; background:#fff3e0; border-radius:10px; text-align:center;">
                    <h5>主力净流入</h5>
                    <h3 style="color:{main_color};">{format_amount(main_net)}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="padding:15px; background:#e8f5e9; border-radius:10px; text-align:center;">
                    <h5>散户净流入</h5>
                    <h3 style="color:{retail_color};">{format_amount(retail_net)}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            # 计算净流入占比
            total_vol = recent_flow.iloc[-1].iloc[1] if len(recent_flow) > 0 else 1  # 成交量
            if total_vol > 0:
                net_ratio = (main_net / total_vol * 100) if total_vol else 0
                with col3:
                    st.markdown(f"""
                    <div style="padding:15px; background:#e3f2fd; border-radius:10px; text-align:center;">
                        <h5>主力净流入占比</h5>
                        <h3 style="color:{'#E53935' if net_ratio > 0 else '#4CAF50'};">{net_ratio:+.2f}%</h3>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.info("资金流向数据格式解析中...")
    else:
        st.info("暂无资金流向数据")
    
    # ==================== K线图 ====================
    
    st.markdown("---")
    st.markdown("### 📈 股价走势分析")
    
    fig = plot_candlestick_chart(df, symbol, indicators)
    st.plotly_chart(fig, use_container_width=True)
    
    # ==================== 交易信号 ====================
    
    st.markdown("---")
    st.markdown("### 🔔 智能交易信号（量价确认版）")
    
    signals = generate_signal(df, symbol)
    
    cols = st.columns(len(signals))
    for i, (title, desc, signal_type) in enumerate(signals):
        with cols[i]:
            if signal_type == "positive":
                st.success(f"**{title}**\n\n{desc}")
            elif signal_type == "negative":
                st.error(f"**{title}**\n\n{desc}")
            else:
                st.info(f"**{title}**\n\n{desc}")
    
    # ==================== 数据表和统计数据 ====================
    
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 历史数据", "📐 指标详情", "📈 收益率分析", "📋 统计分析"])
    
    with tab1:
        # 显示最新数据
        display_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Pct_Change', 'Turnover']
        display_df = df[display_cols].copy()
        display_df.columns = ['开盘', '最高', '最低', '收盘', '成交量', '涨跌幅%', '换手率%']
        display_df.index = pd.to_datetime(display_df.index).strftime('%Y-%m-%d')
        
        # A股红涨绿跌：涨用红色背景，跌用绿色背景
        def color_pct(val):
            if val > 0:
                return 'background-color: #ffcdd2; color: #c62828'  # 红色背景
            elif val < 0:
                return 'background-color: #c8e6c9; color: #2e7d32'  # 绿色背景
            else:
                return ''
        
        st.dataframe(
            display_df.tail(30).style.format({
                '开盘': '¥{:.2f}', '最高': '¥{:.2f}',
                '最低': '¥{:.2f}', '收盘': '¥{:.2f}', 
                '成交量': '{:,.0f}', '涨跌幅%': '{:+.2f}%', '换手率%': '{:.2f}%'
            }).applymap(color_pct, subset=['涨跌幅%']),
            use_container_width=True,
            height=400
        )
        
        # 下载按钮
        csv = df.to_csv().encode('utf-8')
        st.download_button(
            label="📥 下载CSV数据",
            data=csv,
            file_name=f"{symbol}_{info['name']}_数据.csv",
            mime="text/csv",
        )
    
    with tab2:
        # 技术指标详细表格
        tech_cols = [col for col in ['MA5', 'MA10', 'MA20', 'MA60', 'RSI', 'MACD', 'MACD_Signal', 'BB_Upper', 'BB_Lower', 'Volatility'] if col in df.columns]
        tech_df = df[tech_cols].tail(20).copy()
        tech_df.index = pd.to_datetime(tech_df.index).strftime('%Y-%m-%d')
        
        st.dataframe(
            tech_df.style.format('{:.2f}').background_gradient(cmap='coolwarm'),
            use_container_width=True,
            height=400
        )
    
    with tab3:
        # 收益率分析
        st.markdown("#### 不同时间周期收益率")
        
        returns = {}
        periods = {
            '5天': 5, '10天': 10, '20天': 20, 
            '60天': 60, '120天': 120, '250天': 250
        }
        
        for name, days in periods.items():
            if len(df) > days:
                ret = (df['Close'].iloc[-1] / df['Close'].iloc[-days] - 1) * 100
                returns[name] = ret
        
        cols = st.columns(len(returns))
        colors = ['#FFCDD2', '#C8E6C9', '#BBDEFB', '#F8BBD9', '#FFE0B2', '#E1BEE7']
        for i, (name, ret) in enumerate(returns.items()):
            with cols[i]:
                # A股红涨绿跌
                color = '#E53935' if ret > 0 else '#4CAF50'
                st.markdown(f"""
                <div style="text-align:center; padding:15px; background:{colors[i]}; border-radius:10px; opacity:0.9;">
                    <h4>{name}</h4>
                    <h2 style="color:{color};">¥{ret:+.2f}%</h2>
                </div>
                """, unsafe_allow_html=True)
        
        # 日收益率分布
        df['Daily_Return'] = df['Pct_Change']
        daily_returns = df['Daily_Return'].dropna()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 日收益率直方图")
            fig_ret = go.Figure()
            fig_ret.add_trace(go.Histogram(
                x=daily_returns,
                nbinsx=50,
                name='日收益率分布',
                marker_color='#E53935',
                opacity=0.7
            ))
            fig_ret.update_layout(
                template='plotly_dark',
                title=f"日收益率分布 (均值: {daily_returns.mean():.2f}%, 标准差: {daily_returns.std():.2f}%)",
                xaxis_title="收益率 (%)",
                yaxis_title="频次",
                height=400
            )
            st.plotly_chart(fig_ret, use_container_width=True)
        
        with col2:
            st.markdown("#### 累计收益率曲线")
            cumulative_ret = (1 + df['Daily_Return'] / 100).cumprod() * 100 - 100
            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=df.index,
                y=cumulative_ret,
                mode='lines',
                name='累计收益率',
                line=dict(color='#FF9800', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 152, 0, 0.1)'
            ))
            fig_cum.update_layout(
                template='plotly_dark',
                title="累计收益率",
                xaxis_title="日期",
                yaxis_title="累计收益率 (%)",
                height=400
            )
            st.plotly_chart(fig_cum, use_container_width=True)
    
    with tab4:
        # 统计分析
        st.markdown("#### 描述性统计")
        
        stats_data = {
            '统计量': ['均值', '中位数', '标准差', '最大值', '最小值', '偏度', '峰度', '25%分位', '75%分位'],
            '收盘价': [
                df['Close'].mean(),
                df['Close'].median(),
                df['Close'].std(),
                df['Close'].max(),
                df['Close'].min(),
                df['Close'].skew(),
                df['Close'].kurtosis(),
                df['Close'].quantile(0.25),
                df['Close'].quantile(0.75)
            ],
            '收益率 (%)': [
                daily_returns.mean(),
                daily_returns.median(),
                daily_returns.std(),
                daily_returns.max(),
                daily_returns.min(),
                daily_returns.skew(),
                daily_returns.kurtosis(),
                daily_returns.quantile(0.25),
                daily_returns.quantile(0.75)
            ],
            '成交量': [
                df['Volume'].mean(),
                df['Volume'].median(),
                df['Volume'].std(),
                df['Volume'].max(),
                df['Volume'].min(),
                df['Volume'].skew(),
                df['Volume'].kurtosis(),
                df['Volume'].quantile(0.25),
                df['Volume'].quantile(0.75)
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        stats_df = stats_df.set_index('统计量')
        
        st.dataframe(
            stats_df.style.format('{:.4f}').background_gradient(cmap='viridis'),
            use_container_width=True
        )
        
        # 相关性分析
        st.markdown("#### 价格与成交量相关性")
        corr = df[['Close', 'Volume', 'Daily_Return']].dropna().corr()
        st.dataframe(
            corr.style.format('{:.4f}').background_gradient(cmap='coolwarm'),
            use_container_width=True
        )


# ===================== 运行入口 =====================

if __name__ == "__main__":
    main()
