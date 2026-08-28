# EdgeLab CME Futures Tick Dataset

A comprehensive, institutional-grade dataset of **1,078,414,656 ticks** (16.74 GB) across **11 CME futures assets** and **56 quarterly contracts**.

## Asset Universe

| Symbol | Name | Asset Class | Type | Contracts | Total Ticks | Tick Size | Multiplier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **6B** | British Pound | FX | Full-size | 5 | 8,320,560 | 0.0001 | $62500 |
| **6E** | Euro FX | FX | Full-size | 5 | 20,455,828 | 5e-05 | $125000 |
| **6J** | Japanese Yen | FX | Full-size | 5 | 15,552,894 | 5e-07 | $12500000 |
| **ES** | E-mini S&P 500 | Index | Full-size | 5 | 280,572,867 | 0.25 | $50 |
| **GC** | Gold | Commodity | Full-size | 5 | 39,789,544 | 0.1 | $100 |
| **MBT** | Micro Bitcoin | Crypto | Micro | 6 | 4,904,699 | 5.0 | $0.1 |
| **MES** | Micro E-mini S&P 500 | Index | Micro | 5 | 178,899,220 | 0.25 | $5 |
| **MNQ** | Micro E-mini Nasdaq | Index | Micro | 5 | 348,596,819 | 0.25 | $2 |
| **NQ** | E-mini Nasdaq 100 | Index | Full-size | 5 | 127,890,620 | 0.25 | $20 |
| **YM** | E-mini Dow Jones | Index | Full-size | 5 | 23,244,421 | 1.0 | $5 |
| **ZB** | 30-Year US Treasury | Bonds | Full-size | 5 | 30,187,184 | 0.03125 | $1000 |

## Key Pairs for Cross-Asset Microstructure Research:
- **Index Full vs Micro**: ES vs MES (459M ticks), NQ vs MNQ (476M ticks)
- **Foreign Exchange**: 6E (Euro), 6B (Pound), 6J (Yen) (44.3M ticks)
- **Commodities & Bonds**: GC (Gold - 39.8M ticks), ZB (30Y Treasury - 30.2M ticks)
- **Crypto Futures**: MBT (Micro Bitcoin - 4.9M ticks)

Generated automatically by EdgeLab.
