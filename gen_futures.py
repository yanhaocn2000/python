from generate_sample_data import generate_realistic_crypto_data, add_market_regimes

print('生成BTC永续合约数据（11460条，2019-2024）...')
btc = generate_realistic_crypto_data(
    start_date='2019-09-01',
    periods=11460,
    interval='4h',
    initial_price=10000,
    volatility=0.025,
    trend=0.00005
)
btc = add_market_regimes(btc)
btc.to_csv('btcusdt_futures_4h.csv')
print(f'✓ BTC: {len(btc)}条数据')
print(f'  价格范围: ${btc["close"].min():.0f} - ${btc["close"].max():.0f}')
print(f'  起止价格: ${btc["close"].iloc[0]:.0f} -> ${btc["close"].iloc[-1]:.0f}')

print('\n生成ETH永续合约数据...')
eth = generate_realistic_crypto_data(
    start_date='2019-09-01',
    periods=11460,
    interval='4h',
    initial_price=200,
    volatility=0.03,
    trend=0.00006
)
eth = add_market_regimes(eth)
eth.to_csv('ethusdt_futures_4h.csv')
print(f'✓ ETH: {len(eth)}条数据')
print(f'  价格范围: ${eth["close"].min():.0f} - ${eth["close"].max():.0f}')
print(f'  起止价格: ${eth["close"].iloc[0]:.0f} -> ${eth["close"].iloc[-1]:.0f}')

print('\n✓ 永续合约数据生成完成！')
