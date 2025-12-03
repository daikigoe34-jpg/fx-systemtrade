from backtest_ma_cross import (
    load_price_data,
    evaluate_params,
    DEFAULT_PARAMS,
    CSV_PATH,
)


def main():
    df = load_price_data(CSV_PATH)

    best_params = None
    best_score = None

    # ざっくりサーチの例:
    # 短期 5〜30 / 長期 40〜120 を試す
    for short in range(5, 31, 5):      # 5,10,15,20,25,30
        for long in range(40, 121, 10):  # 40,50,...,120
            if short >= long:
                continue  # 短期 >= 長期 はスキップ

            params = dict(DEFAULT_PARAMS)
            params["short_window"] = short
            params["long_window"] = long

            score = evaluate_params(df, params)

            print(f"short={short:2d}, long={long:3d} -> score={score:.2f}")

            if (best_score is None) or (score > best_score):
                best_score = score
                best_params = params

    print("\n===== ベストパラメータ =====")
    if best_params is None:
        print("有効な組み合わせが見つかりませんでした。")
    else:
        print(best_params)
        print(f"score = {best_score:.2f}")


if __name__ == "__main__":
    main()