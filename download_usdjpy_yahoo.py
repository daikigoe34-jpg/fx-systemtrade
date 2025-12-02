"""
USDJPYの5分足データをYahoo Financeから取得して保存するスクリプト。
Python 3.10 と Pythonista 3 で動くように、標準ライブラリと pandas と yfinance だけで書いています。
"""

from pathlib import Path
from typing import List

import pandas as pd

# yfinance は別途インストールが必要になるので、ここで読み込めない場合は
# わかりやすいメッセージを出して終了する
try:
    import yfinance as yf
except ModuleNotFoundError as exc:  # インストールされていない場合
    raise SystemExit(
        "yfinance が見つかりません。'pip install yfinance' を実行してください。"
    ) from exc


# 使うティッカー（Yahoo Finance での USD/JPY レート）
TICKER = "USDJPY=X"
# 保存するファイル名（リポジトリ直下に置く）
OUTPUT_CSV = Path(__file__).resolve().parent / "usdjpy_yahoo_30d_5m.csv"


def _format_timestamps(datetimes: pd.DatetimeIndex) -> List[str]:
    """UTC の文字列にそろえたリストを作る helper 関数。"""

    # タイムゾーンが付いていなければ UTC とみなす
    if datetimes.tz is None:
        datetimes = datetimes.tz_localize("UTC")
    else:
        datetimes = datetimes.tz_convert("UTC")

    # isoformat() は「2024-01-01 00:00:00+00:00」のように
    # 子どもでも読める形にしてくれる
    return [dt.isoformat(sep=" ") for dt in datetimes]


def fetch_usdjpy_candles() -> pd.DataFrame:
    """直近30日分の5分足を取得して、列をそろえた DataFrame を返す。"""

    # Yahoo Finance からデータをダウンロード（進捗バーは非表示）
    raw = yf.download(
        TICKER,
        period="30d",
        interval="5m",
        progress=False,
        auto_adjust=False,
    )

    # データが空なら、そのまま進めても意味がないので教えてあげる
    if raw.empty:
        raise RuntimeError("データの取得に失敗しました。ネット接続などを確認してください。")

    # 必要な列だけにしぼり、順番を「Close, High, Low, Open, Volume」に並べ替える
    data = raw[["Close", "High", "Low", "Open", "Volume"]].copy()

    # 日付の列を人が読める形の文字列に変換して、先頭に挿入する
    timestamps = _format_timestamps(data.index)
    data.insert(0, "Price", timestamps)

    # Volume の欠損があるとそのまま保存するときに困るので、0 で埋めておく
    data["Volume"] = data["Volume"].fillna(0)

    return data


def save_with_metadata(data: pd.DataFrame) -> None:
    """データの先頭にメタ情報の行を付けて、CSV に保存する。"""

    # 既存の CSV と同じように、先頭に「Ticker」と「Datetime」の行を差し込む
    metadata = pd.DataFrame(
        [
            {
                "Price": "Ticker",
                "Close": TICKER,
                "High": TICKER,
                "Low": TICKER,
                "Open": TICKER,
                "Volume": TICKER,
            },
            {"Price": "Datetime", "Close": "", "High": "", "Low": "", "Open": "", "Volume": ""},
        ]
    )

    # メタ情報の後ろにデータ本体をつなげる
    final_df = pd.concat([metadata, data], ignore_index=True)

    # インデックスは不要なので付けずに保存する
    final_df.to_csv(OUTPUT_CSV, index=False)


def main() -> None:
    """スクリプトのメイン処理。関数に分けて読みやすくしている。"""

    # 1. データを取得する
    candles = fetch_usdjpy_candles()

    # 2. メタ情報を付けて保存する
    save_with_metadata(candles)

    # 3. 完了を知らせる（実行する人が安心できるように）
    print(f"保存が完了しました: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
