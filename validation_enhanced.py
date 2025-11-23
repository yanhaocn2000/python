"""
增强版模型验证
使用改进的信号生成逻辑进行验证
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from squeeze_momentum_enhanced import SqueezeMomentumEnhanced
from backtest_example import SqueezeBacktester


def quick_backtest(data: pd.DataFrame, config: Dict) -> Dict:
    """
    快速回测

    参数:
        data: OHLCV数据
        config: 策略配置

    返回:
        性能指标
    """
    # 创建指标
    indicator = SqueezeMomentumEnhanced(**config)

    # 生成信号
    signals = indicator.generate_signals_enhanced(
        data['high'],
        data['low'],
        data['close'],
        data['volume']
    )

    # 回测
    backtester = SqueezeBacktester(initial_capital=10000, commission=0.001)
    results, trades = backtester.run_backtest(data, signals)
    metrics = backtester.calculate_metrics(results, trades)

    return metrics, signals


def run_enhanced_validation():
    """运行增强版完整验证"""
    print("Squeeze Momentum增强版 - 完整验证")
    print("=" * 80)

    # 加载数据
    try:
        data = pd.read_csv('btc_4h_data.csv', index_col=0, parse_dates=True)
    except:
        print("数据文件不存在，正在生成...")
        from generate_sample_data import main as generate_data
        data = generate_data()

    print(f"\n数据量: {len(data)} 条")
    print(f"时间范围: {data.index[0]} 至 {data.index[-1]}")

    # 数据分割
    train_ratio = 0.7
    val_ratio = 0.15
    test_ratio = 0.15

    n = len(data)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_data = data.iloc[:train_end]
    val_data = data.iloc[train_end:val_end]
    test_data = data.iloc[val_end:]

    print("\n数据分割:")
    print("=" * 80)
    print(f"训练集: {len(train_data)} 条 | {train_data.index[0]} 至 {train_data.index[-1]}")
    print(f"验证集: {len(val_data)} 条 | {val_data.index[0]} 至 {val_data.index[-1]}")
    print(f"测试集: {len(test_data)} 条 | {test_data.index[0]} 至 {test_data.index[-1]}")

    # 测试不同配置
    configurations = {
        '原版策略（严格模式）': {
            'signal_mode': 'strict',
            'use_volume_filter': False,
            'use_trend_filter': False,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（无过滤器）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': False,
            'use_trend_filter': False,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（仅成交量过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': False,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（仅趋势过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': False,
            'use_trend_filter': True,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（完整过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': True,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（优化参数）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': True,
            'bb_length': 15, 'bb_mult': 2.5,
            'kc_length': 15, 'kc_mult': 2.0
        }
    }

    all_results = []

    for config_name, config in configurations.items():
        print(f"\n{'=' * 80}")
        print(f"测试配置: {config_name}")
        print(f"{'=' * 80}")

        # 训练集
        train_metrics, train_signals = quick_backtest(train_data, config)
        train_total_signals = (train_signals['signal'] != 0).sum()

        # 验证集
        val_metrics, val_signals = quick_backtest(val_data, config)
        val_total_signals = (val_signals['signal'] != 0).sum()

        # 测试集
        test_metrics, test_signals = quick_backtest(test_data, config)
        test_total_signals = (test_signals['signal'] != 0).sum()

        print(f"\n训练集:")
        print(f"  信号数: {train_total_signals:3d} | 收益: {train_metrics['total_return']:8.2f}% | "
              f"回撤: {train_metrics['max_drawdown']:7.2f}% | Sharpe: {train_metrics['sharpe_ratio']:6.3f} | "
              f"胜率: {train_metrics['win_rate']:5.1f}%")

        print(f"验证集:")
        print(f"  信号数: {val_total_signals:3d} | 收益: {val_metrics['total_return']:8.2f}% | "
              f"回撤: {val_metrics['max_drawdown']:7.2f}% | Sharpe: {val_metrics['sharpe_ratio']:6.3f} | "
              f"胜率: {val_metrics['win_rate']:5.1f}%")

        print(f"测试集:")
        print(f"  信号数: {test_total_signals:3d} | 收益: {test_metrics['total_return']:8.2f}% | "
              f"回撤: {test_metrics['max_drawdown']:7.2f}% | Sharpe: {test_metrics['sharpe_ratio']:6.3f} | "
              f"胜率: {test_metrics['win_rate']:5.1f}%")

        # 过拟合检测
        sharpe_drop = (train_metrics['sharpe_ratio'] - test_metrics['sharpe_ratio']) / (abs(train_metrics['sharpe_ratio']) + 0.01)
        if abs(sharpe_drop) > 0.3:
            print(f"\n  ⚠️ 过拟合风险: Sharpe下降 {sharpe_drop*100:.1f}%")
        else:
            print(f"\n  ✓ 泛化良好: Sharpe下降 {sharpe_drop*100:.1f}%")

        # 记录结果
        all_results.append({
            'config': config_name,
            'train_signals': train_total_signals,
            'val_signals': val_total_signals,
            'test_signals': test_total_signals,
            'train_return': train_metrics['total_return'],
            'val_return': val_metrics['total_return'],
            'test_return': test_metrics['total_return'],
            'train_sharpe': train_metrics['sharpe_ratio'],
            'val_sharpe': val_metrics['sharpe_ratio'],
            'test_sharpe': test_metrics['sharpe_ratio'],
            'train_winrate': train_metrics['win_rate'],
            'val_winrate': val_metrics['win_rate'],
            'test_winrate': test_metrics['win_rate'],
            'train_trades': train_metrics['total_trades'],
            'val_trades': val_metrics['total_trades'],
            'test_trades': test_metrics['total_trades']
        })

    # 汇总比较
    print(f"\n\n{'=' * 80}")
    print("策略对比汇总")
    print(f"{'=' * 80}")

    results_df = pd.DataFrame(all_results)

    print("\n测试集性能排名（按Sharpe比率）:")
    print("-" * 80)
    sorted_results = results_df.sort_values('test_sharpe', ascending=False)

    print(f"{'排名':<4s} {'策略':<30s} {'收益率':>10s} {'Sharpe':>8s} {'胜率':>7s} {'信号数':>7s}")
    print("-" * 80)
    for idx, row in sorted_results.iterrows():
        rank = sorted_results.index.get_loc(idx) + 1
        print(f"{rank:<4d} {row['config']:<30s} {row['test_return']:>9.2f}% {row['test_sharpe']:>8.3f} "
              f"{row['test_winrate']:>6.1f}% {row['test_signals']:>7d}")

    # 保存结果
    results_df.to_csv('enhanced_validation_results.csv', index=False)
    print(f"\n结果已保存到: enhanced_validation_results.csv")

    # 推荐策略
    print(f"\n{'=' * 80}")
    print("推荐策略")
    print(f"{'=' * 80}")

    # 找出平衡性能和稳定性的策略
    # 标准：测试集Sharpe > 1.0, 交易次数 > 10, 过拟合风险小
    results_df['sharpe_consistency'] = 1 - abs(
        (results_df['train_sharpe'] - results_df['test_sharpe']) / (results_df['train_sharpe'] + 0.01)
    )

    # 处理可能的除零问题
    max_trades = results_df['test_trades'].max()
    if max_trades > 0:
        trade_score = results_df['test_trades'] / max_trades
    else:
        trade_score = 0

    results_df['综合得分'] = (
        results_df['test_sharpe'].clip(lower=0) * 0.4 +
        results_df['sharpe_consistency'].fillna(0).clip(0, 1) * 0.3 +
        trade_score * 0.3
    )

    # 找到最佳配置（排除NaN）
    valid_scores = results_df['综合得分'].dropna()
    if len(valid_scores) > 0:
        best_idx = valid_scores.idxmax()
        best_config = results_df.loc[best_idx]
    else:
        best_config = results_df.iloc[0]

    print(f"\n最佳配置: {best_config['config']}")
    print(f"  测试集Sharpe: {best_config['test_sharpe']:.3f}")
    print(f"  测试集收益: {best_config['test_return']:.2f}%")
    print(f"  测试集胜率: {best_config['test_winrate']:.1f}%")
    print(f"  测试集交易数: {best_config['test_trades']:.0f}")
    print(f"  Sharpe一致性: {best_config['sharpe_consistency']:.2%}")
    print(f"  综合得分: {best_config['综合得分']:.3f}")

    return results_df


if __name__ == "__main__":
    results = run_enhanced_validation()
