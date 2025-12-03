import pandas as pd

# ================== 設定 ==================

CSV_PATH = "usdjpy_yahoo_30d_5m.csv"

DEFAULT_PARAMS = {
    "short_window": 20,         # 短期MA
    "long_window": 60,          # 長期MA
    "initial_capital": 10_000,  # 初期資金
    "fee_rate": 0.00002,        # 手数料率 (0.002% = 0.00002)
    "trade_size": 1,            # 1トレードあたり枚数
}


# ================== データ読み込み ==================

def load_price_data(path: str) -> pd.DataFrame:
    """CSV からデータを読み込み、Datetime を整えて返す。"""
    df = pd.read_csv(
        path,
        skiprows=2,  # 先頭2行のメタ情報を飛ばす
        names=["Datetime", "Close", "High", "Low", "Open", "Volume"],
    )
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
    df = df.dropna(subset=["Datetime"])
    df = df.sort_values("Datetime").reset_index(drop=True)
    return df


# ================== バックテスト本体 ==================

def calculate_max_drawdown(equity_curve):
    max_peak = 0
    max_dd = 0
    for eq in equity_curve:
        if eq > max_peak:
            max_peak = eq
        if max_peak > 0:
            dd = (eq - max_peak) / max_peak
            if dd < max_dd:
                max_dd = dd
    return max_dd


def _run_backtest(df: pd.DataFrame, params: dict):
    """
    シンプルな移動平均クロス戦略のバックテスト。
    ゴールデンクロスで買い、デッドクロスで全決済。
    """
    df = df.copy()

    short = params["short_window"]
    long = params["long_window"]

    # インジケーター
    df["sma_short"] = df["Close"].rolling(window=short).mean()
    df["sma_long"] = df["Close"].rolling(window=long).mean()

    # シグナル & ポジション
    df["signal"] = 0
    df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1
    df["position"] = df["signal"].shift(1).fillna(0)

    # 取引イベント (+1: 新規買い, -1: 決済)
    df["trade"] = df["position"].diff().fillna(df["position"])

    capital = params["initial_capital"]
    fee_rate = params["fee_rate"]
    size = params["trade_size"]

    cash = capital
    position = 0
    last_price = None

    equity_curve = []
    raw_trades = []  # すべての約定(BUY/SELL)

    for _, row in df.iterrows():
        price = float(row["Close"])
        trade = int(row["trade"])

        # 新規買い
        if trade == 1 and position == 0:
            cost = price * size
            fee = cost * fee_rate
            cash -= cost + fee
            position += size
            raw_trades.append(
                {
                    "Datetime": row["Datetime"],
                    "Side": "BUY",
                    "Price": price,
                    "Size": size,
                    "Fee": fee,
                }
            )

        # 全決済
        elif trade == -1 and position > 0:
            proceeds = price * position
            fee = proceeds * fee_rate
            cash += proceeds - fee
            raw_trades.append(
                {
                    "Datetime": row["Datetime"],
                    "Side": "SELL",
                    "Price": price,
                    "Size": position,
                    "Fee": fee,
                }
            )
            position = 0

        last_price = price
        equity_curve.append(cash + position * price)

    # 最後まで持っていたら終値で決済したことにする
    if last_price is not None and position > 0:
        proceeds = last_price * position
        fee = proceeds * fee_rate
        cash += proceeds - fee
        raw_trades.append(
            {
                "Datetime": df.iloc[-1]["Datetime"],
                "Side": "SELL",
                "Price": last_price,
                "Size": position,
                "Fee": fee,
            }
        )
        position = 0
        equity_curve[-1] = cash

    final_equity = cash
    max_dd = calculate_max_drawdown(equity_curve)

    # ラウンドトリップ単位で損益計算
    round_trips = []
    entry = None
    for tr in raw_trades:
        if tr["Side"] == "BUY":
            entry = tr
        elif tr["Side"] == "SELL" and entry is not None:
            pnl = (tr["Price"] - entry["Price"]) * entry["Size"] - (entry["Fee"] + tr["Fee"])
            round_trips.append(pnl)
            entry = None

    n_trades = len(round_trips)
    wins = sum(1 for p in round_trips if p > 0)
    win_rate = wins / n_trades if n_trades > 0 else 0.0

    # 評価スコア(とりあえず「最終残高 × (1-最大DD)」)
    score = final_equity * (1 - max_dd)

    return {
        "final_equity": final_equity,
        "max_drawdown": max_dd,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "score": score,
        "raw_trades": raw_trades,
    }


# ================== 外から呼ぶ用の関数 ==================

def evaluate_params(df: pd.DataFrame, params: dict) -> float:
    """
    グリッドサーチや GA から呼ぶための関数。
    DataFrame と params(dict) を受け取って「スコア」だけ返す。
    """
    result = _run_backtest(df, params)
    return result["score"]


def run_and_save_trades(df: pd.DataFrame, params: dict, trades_path: str = "trades_latest.csv"):
    """
    1 回バックテストして結果を表示 + トレード一覧を CSV に保存。
    """
    result = _run_backtest(df, params)

    # トレード一覧CSV用にラウンドトリップを作る
    trades = []
    entry = None
    for tr in result["raw_trades"]:
        if tr["Side"] == "BUY":
            entry = tr
        elif tr["Side"] == "SELL" and entry is not None:
            pnl = (tr["Price"] - entry["Price"]) * entry["Size"] - (entry["Fee"] + tr["Fee"])
            trades.append(
                {
                    "EntryTime": entry["Datetime"],
                    "EntryPrice": entry["Price"],
                    "ExitTime": tr["Datetime"],
                    "ExitPrice": tr["Price"],
                    "Size": entry["Size"],
                    "PnL": pnl,
                }
            )
            entry = None

    if trades:
        pd.DataFrame(trades).to_csv(trades_path, index=False, encoding="utf-8-sig")
        print(f"トレード一覧を保存しました: {trades_path}")

    print("===== バックテスト結果 =====")
    print(f"最終口座残高: {result['final_equity']:.2f} 円")
    print(f"トレード回数: {result['n_trades']}")
    print(f"勝率: {result['win_rate'] * 100:.2f}%")
    print(f"最大ドローダウン: {result['max_drawdown'] * 100:.2f}%")
    print(f"評価関数のスコア: {result['score']:.2f}")


def main():
    df = load_price_data(CSV_PATH)
    run_and_save_trades(df, DEFAULT_PARAMS)


if __name__ == "__main__":
    main()