"""
Squeeze Momentum策略回测示例
"""

import numpy as np
import pandas as pd
from squeeze_momentum import SqueezeMomentumIndicator


class SqueezeBacktester:
    """Squeeze Momentum策略回测器"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1%手续费
        slippage: float = 0.0005    # 0.05%滑点
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run_backtest(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame
    ) -> pd.DataFrame:
        """
        运行回测

        参数:
            data: 包含OHLC数据的DataFrame
            signals: 指标生成的信号DataFrame

        返回:
            包含回测结果的DataFrame
        """
        results = pd.DataFrame(index=data.index)
        results['close'] = data['close']
        results['signal'] = signals['signal']
        results['stop_loss'] = signals['stop_loss']

        # 初始化
        position = 0  # 当前仓位 (0: 无仓位, 1: 多头, -1: 空头)
        entry_price = 0
        capital = self.initial_capital
        holdings = 0

        # 记录
        positions = []
        capitals = []
        pnls = []
        trades = []

        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            current_signal = signals['signal'].iloc[i]
            current_stop = signals['stop_loss'].iloc[i]

            trade_info = None

            # 检查止损
            if position == 1 and not pd.isna(current_stop):
                if current_price <= current_stop:
                    # 多头止损
                    exit_price = current_price * (1 - self.slippage)
                    pnl = (exit_price - entry_price) * holdings
                    capital += exit_price * holdings * (1 - self.commission)

                    trade_info = {
                        'type': 'STOP_LOSS',
                        'direction': 'LONG',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': (exit_price - entry_price) / entry_price * 100
                    }

                    position = 0
                    holdings = 0
                    entry_price = 0

            elif position == -1 and not pd.isna(current_stop):
                if current_price >= current_stop:
                    # 空头止损
                    exit_price = current_price * (1 + self.slippage)
                    pnl = (entry_price - exit_price) * abs(holdings)
                    capital += pnl + abs(holdings) * entry_price * (1 - self.commission)

                    trade_info = {
                        'type': 'STOP_LOSS',
                        'direction': 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': (entry_price - exit_price) / entry_price * 100
                    }

                    position = 0
                    holdings = 0
                    entry_price = 0

            # 处理新信号
            if current_signal == 1 and position != 1:
                # 平空开多
                if position == -1:
                    exit_price = current_price * (1 + self.slippage)
                    pnl = (entry_price - exit_price) * abs(holdings)
                    capital += pnl + abs(holdings) * entry_price * (1 - self.commission)

                # 开多
                entry_price = current_price * (1 + self.slippage)
                holdings = capital * 0.95 / entry_price  # 使用95%资金
                capital -= holdings * entry_price * (1 + self.commission)
                position = 1

                trade_info = {
                    'type': 'ENTRY',
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'exit_price': None,
                    'pnl': None,
                    'pnl_pct': None
                }

            elif current_signal == -1 and position != -1:
                # 平多开空
                if position == 1:
                    exit_price = current_price * (1 - self.slippage)
                    pnl = (exit_price - entry_price) * holdings
                    capital += exit_price * holdings * (1 - self.commission)

                # 开空
                entry_price = current_price * (1 - self.slippage)
                holdings = -(capital * 0.95 / entry_price)  # 使用95%资金
                position = -1

                trade_info = {
                    'type': 'ENTRY',
                    'direction': 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': None,
                    'pnl': None,
                    'pnl_pct': None
                }

            # 计算当前权益
            if position == 1:
                current_equity = capital + holdings * current_price
            elif position == -1:
                current_equity = capital + (entry_price - current_price) * abs(holdings)
            else:
                current_equity = capital

            positions.append(position)
            capitals.append(current_equity)
            pnls.append(current_equity - self.initial_capital)
            trades.append(trade_info)

        results['position'] = positions
        results['equity'] = capitals
        results['pnl'] = pnls

        return results, trades

    def calculate_metrics(self, results: pd.DataFrame, trades: list) -> dict:
        """计算回测指标"""
        # 收益率
        total_return = (results['equity'].iloc[-1] - self.initial_capital) / self.initial_capital * 100

        # 最大回撤
        cummax = results['equity'].cummax()
        drawdown = (results['equity'] - cummax) / cummax * 100
        max_drawdown = drawdown.min()

        # 交易统计
        completed_trades = [t for t in trades if t and t.get('exit_price') is not None]
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl'] < 0]

        total_trades = len(completed_trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(sum([t['pnl'] for t in winning_trades]) / sum([t['pnl'] for t in losing_trades])) \
            if losing_trades and winning_trades else 0

        # Sharpe比率 (假设252个交易日)
        returns = results['equity'].pct_change()
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0

        metrics = {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'final_equity': results['equity'].iloc[-1]
        }

        return metrics


def run_example():
    """运行示例回测"""
    print("Squeeze Momentum策略回测示例")
    print("=" * 80)

    # 生成示例数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='D')

    # 模拟有趋势的价格数据
    trend = np.linspace(0, 50, 500)
    noise = np.cumsum(np.random.randn(500) * 2)
    close = 100 + trend + noise

    # 添加一些波动
    volatility = np.random.rand(500) * 3
    high = close + volatility
    low = close - volatility

    data = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    }, index=dates)

    # 创建指标
    indicator = SqueezeMomentumIndicator(
        bb_length=20,
        bb_mult=2.0,
        kc_length=20,
        kc_mult=1.5,
        rsi_length=14,
        rsi_overbought=70,
        rsi_oversold=30,
        atr_length=14,
        atr_mult=2.0
    )

    # 生成信号
    print("生成交易信号...")
    signals = indicator.generate_signals(data['high'], data['low'], data['close'])

    # 运行回测
    print("运行回测...")
    backtester = SqueezeBacktester(initial_capital=10000, commission=0.001)
    results, trades = backtester.run_backtest(data, signals)

    # 计算指标
    metrics = backtester.calculate_metrics(results, trades)

    # 打印结果
    print("\n回测结果:")
    print("-" * 80)
    print(f"总收益率: {metrics['total_return']:.2f}%")
    print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"最终权益: ${metrics['final_equity']:.2f}")
    print(f"总交易次数: {metrics['total_trades']}")
    print(f"胜率: {metrics['win_rate']:.2f}%")
    print(f"平均盈利: ${metrics['avg_win']:.2f}")
    print(f"平均亏损: ${metrics['avg_loss']:.2f}")
    print(f"盈亏比: {metrics['profit_factor']:.2f}")
    print(f"Sharpe比率: {metrics['sharpe_ratio']:.2f}")

    # 打印最近的交易
    print("\n最近的交易:")
    print("-" * 80)
    recent_trades = [t for t in trades if t and t.get('exit_price') is not None][-5:]
    for i, trade in enumerate(recent_trades, 1):
        print(f"\n交易 {i}:")
        print(f"  方向: {trade['direction']}")
        print(f"  入场价: ${trade['entry_price']:.2f}")
        print(f"  出场价: ${trade['exit_price']:.2f}")
        print(f"  盈亏: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")

    return results, metrics


if __name__ == "__main__":
    results, metrics = run_example()
