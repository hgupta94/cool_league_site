"""
fit_auction_exponent.py

Empirically fits the convexity exponent(s) used in `calculate_prices` against
real historical auction data, so star players price closer to what they
actually go for (e.g. RB1 at $60+ instead of $40).

------------------------------------------------------------------------
EXPECTED INPUT DATA
------------------------------------------------------------------------
A CSV (or list of CSVs, one per season) with at minimum:

    player_name, position, season, actual_price

`actual_price` = real auction value (AAV from FantasyPros, or your own
league's historical draft results). If you have multiple sources/leagues
for the same player-season, average them before loading, or pass multiple
rows and the script will average automatically.

You also need VOR per player-season. Two ways to supply it:

  (A) Recommended: re-run your existing `load_espn_data` + the VOR portion
      of `calculate_prices` for each historical season, and merge the
      resulting `vor` values onto the price CSV by player name. This
      keeps your replacement-level methodology identical between fitting
      and prediction, which matters more than people expect.

  (B) Quick-and-dirty: if you already have a CSV with vor precomputed,
      just point VOR_CSV_PATH at it with columns:
          player_name, position, season, vor

This script is written against option (B) for simplicity, with a clearly
marked function (`load_vor_for_season`) to swap in option (A) using your
real pipeline.

------------------------------------------------------------------------
WHAT THE SCRIPT DOES
------------------------------------------------------------------------
1. Loads actual prices + VOR, joins them on (player_name, position, season)
2. Splits seasons into train / holdout (out-of-sample validation)
3. Fits a separate exponent per position by minimizing squared error
   between predicted and actual price, using your same budget-allocation
   formula (floor + VOR^exponent share of remaining spend)
4. Reports fit quality (R^2, RMSE) on train AND holdout
5. Plots predicted vs actual so you can eyeball whether a power curve is
   even the right shape
6. Prints the final exponents ready to drop into calculate_prices()
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import matplotlib.pyplot as plt


# ============================================================
# CONFIG - edit these paths/columns to match your real data
# ============================================================

PRICE_CSV_PATH = "historical_auction_prices.csv"   # player_name, position, season, actual_price
VOR_CSV_PATH = "historical_vor.csv"                 # player_name, position, season, vor

# Seasons to fit on vs hold out for validation. Adjust to whatever you have.
TRAIN_SEASONS = [2022, 2023, 2024]
HOLDOUT_SEASONS = [2025]

MIN_BID = 1
BUDGET = 200          # per-team budget, matches your settings.auctionBudget
N_TEAMS = 10           # matches your league size
# Total roster spots filled league-wide (starters + bench, excluding any
# spots that never get bid on, e.g. IR). Match this to your real roster math.
N_ROSTER_SPOTS = 16

AVAIL_SPEND = (BUDGET - N_ROSTER_SPOTS * MIN_BID) * N_TEAMS

EXPONENT_SEARCH_BOUNDS = (1.0, 3.0)


# ============================================================
# 1. DATA LOADING
# ============================================================

def load_actual_prices(path: str) -> pd.DataFrame:
    """
    Loads historical actual auction prices.
    Expects columns: player_name, position, season, actual_price
    If duplicate (player_name, position, season) rows exist (e.g. multiple
    leagues/sources), they're averaged.
    """
    df = pd.read_csv(path)
    required = {"player_name", "position", "season", "actual_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Price CSV missing columns: {missing}")

    df["player_name"] = df["player_name"].str.strip()
    df["position"] = df["position"].str.upper().str.strip()

    df = (
        df.groupby(["player_name", "position", "season"], as_index=False)
        ["actual_price"].mean()
    )
    return df


def load_vor_for_season(path: str) -> pd.DataFrame:
    """
    OPTION (B) - quick path: load precomputed VOR from CSV.
    Expects columns: player_name, position, season, vor

    --------------------------------------------------------------
    OPTION (A) - recommended path: replace this function's body to
    call your real pipeline instead, e.g.:

        from your_module import load_espn_data, calculate_vor_only
        all_rows = []
        for season in TRAIN_SEASONS + HOLDOUT_SEASONS:
            dataloader = DataLoader(year=season)
            players = load_espn_data(dataloader)          # your existing fn
            vor_dict = calculate_vor_only(players, ...)    # the VOR-computing
                                                             # portion of your
                                                             # calculate_prices,
                                                             # factored out
            for pid, p in vor_dict.items():
                all_rows.append({
                    "player_name": p["name"],
                    "position": p["position"],
                    "season": season,
                    "vor": p["vor"],
                })
        return pd.DataFrame(all_rows)

    Using your real VOR pipeline instead of a static CSV matters because
    replacement-level calculation is sensitive to your league's exact
    roster settings, and you want the fitted exponent to compensate for
    *this* VOR methodology, not some generic one.
    --------------------------------------------------------------
    """
    df = pd.read_csv(path)
    required = {"player_name", "position", "season", "vor"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"VOR CSV missing columns: {missing}")

    df["player_name"] = df["player_name"].str.strip()
    df["position"] = df["position"].str.upper().str.strip()
    return df


def build_dataset(price_path: str, vor_path: str) -> pd.DataFrame:
    prices = load_actual_prices(price_path)
    vor = load_vor_for_season(vor_path)

    merged = prices.merge(
        vor, on=["player_name", "position", "season"], how="inner"
    )

    dropped = len(prices) - len(merged)
    if dropped > 0:
        print(f"[warn] {dropped} priced players had no VOR match and were dropped "
              f"(likely name mismatches - check spelling/suffixes like 'Jr.')")

    merged["vor"] = merged["vor"].clip(lower=0)
    return merged


# ============================================================
# 2. PRICE PREDICTION (mirrors calculate_prices' formula)
# ============================================================

def predict_prices(vor_array: np.ndarray, exponent: float,
                    avail_spend: float, min_bid: float) -> np.ndarray:
    """
    Same formula as the production calculate_prices function:
    floor of min_bid + a VOR^exponent share of the remaining position
    dollar pool. Operates on a single position's VOR array at a time.
    """
    spend_above_floor = avail_spend - len(vor_array) * min_bid
    spend_above_floor = max(spend_above_floor, 0)

    vor_adj = np.power(vor_array, exponent)
    total = vor_adj.sum()
    if total <= 0:
        return np.full_like(vor_array, min_bid, dtype=float)

    return min_bid + (vor_adj / total) * spend_above_floor


# ============================================================
# 3. FITTING
# ============================================================

def fit_exponent_for_position(df_pos: pd.DataFrame, avail_spend: float,
                               min_bid: float) -> dict:
    """
    Fits a single exponent for one position's data by minimizing SSE
    between predicted and actual price. Returns fit diagnostics too.

    Note: avail_spend here should be the DOLLAR POOL FOR THIS POSITION
    specifically, not the whole league's avail_spend - see fit_all_positions
    for how that's derived from real spend share.
    """
    vor_array = df_pos["vor"].to_numpy()
    actual = df_pos["actual_price"].to_numpy()

    def loss(exponent):
        pred = predict_prices(vor_array, exponent, avail_spend, min_bid)
        return np.sum((pred - actual) ** 2)

    result = minimize_scalar(
        loss, bounds=EXPONENT_SEARCH_BOUNDS, method="bounded"
    )
    best_exp = result.x

    pred = predict_prices(vor_array, best_exp, avail_spend, min_bid)
    rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
    ss_res = np.sum((pred - actual) ** 2)
    ss_tot = np.sum((actual - actual.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return {
        "exponent": best_exp,
        "rmse": rmse,
        "r2": r2,
        "n": len(df_pos),
    }


def fit_all_positions(train_df: pd.DataFrame) -> dict:
    """
    Fits one exponent per position. The dollar pool for each position is
    derived from the ACTUAL observed spend share in the training data
    (i.e. "in real drafts, RB ate 44% of all dollars spent"), rather than
    your VOR-derived pos_dollars - this decouples "how much exponent
    shapes the curve within a position" from "how much total budget that
    position should get", which is a separate calibration (spend_by_pos,
    which you already have hardcoded from 2022-2025 draft averages).
    """
    total_actual_spend = train_df["actual_price"].sum()
    fits = {}

    for pos, df_pos in train_df.groupby("position"):
        pos_actual_spend = df_pos["actual_price"].sum()
        pos_avail_spend = pos_actual_spend  # fit against this position's
                                              # own real dollar pool

        fit = fit_exponent_for_position(df_pos, pos_avail_spend, MIN_BID)
        fit["spend_share"] = pos_actual_spend / total_actual_spend
        fits[pos] = fit

    return fits


# ============================================================
# 4. VALIDATION ON HOLDOUT
# ============================================================

def validate_on_holdout(holdout_df: pd.DataFrame, fits: dict) -> pd.DataFrame:
    """
    Applies the fitted exponents to holdout-season data and reports
    out-of-sample fit quality per position. This is the number that
    actually matters - train R^2 will always look good.
    """
    rows = []
    for pos, df_pos in holdout_df.groupby("position"):
        if pos not in fits:
            print(f"[warn] no fitted exponent for position {pos}, skipping holdout check")
            continue

        exponent = fits[pos]["exponent"]
        pos_avail_spend = df_pos["actual_price"].sum()
        pred = predict_prices(
            df_pos["vor"].to_numpy(), exponent, pos_avail_spend, MIN_BID
        )
        actual = df_pos["actual_price"].to_numpy()

        rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
        ss_res = np.sum((pred - actual) ** 2)
        ss_tot = np.sum((actual - actual.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

        print(f"[holdout] {pos}: exponent={exponent:.3f}  RMSE=${rmse:.2f}  R^2={r2:.3f}  n={len(df_pos)}")

        for name, v, p, a in zip(df_pos["player_name"], df_pos["vor"], pred, actual):
            rows.append({
                "player_name": name, "position": pos,
                "vor": v, "predicted_price": round(p, 2), "actual_price": a,
            })

    return pd.DataFrame(rows)


# ============================================================
# 5. DIAGNOSTIC PLOT
# ============================================================

def plot_fit(holdout_results: pd.DataFrame, out_path: str = "fit_diagnostic.png"):
    positions = holdout_results["position"].unique()
    n = len(positions)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5), squeeze=False)

    for ax, pos in zip(axes[0], positions):
        d = holdout_results[holdout_results["position"] == pos]
        ax.scatter(d["actual_price"], d["predicted_price"], alpha=0.6)
        lims = [0, max(d["actual_price"].max(), d["predicted_price"].max()) * 1.05]
        ax.plot(lims, lims, "k--", linewidth=1, label="perfect fit")
        ax.set_xlabel("Actual price ($)")
        ax.set_ylabel("Predicted price ($)")
        ax.set_title(pos)
        ax.legend()

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"\nSaved diagnostic plot to {out_path}")


# ============================================================
# 6. MAIN
# ============================================================

def main():
    print("Loading and merging historical data...")
    dataset = build_dataset(PRICE_CSV_PATH, VOR_CSV_PATH)

    train_df = dataset[dataset["season"].isin(TRAIN_SEASONS)]
    holdout_df = dataset[dataset["season"].isin(HOLDOUT_SEASONS)]

    print(f"Train rows: {len(train_df)} across seasons {TRAIN_SEASONS}")
    print(f"Holdout rows: {len(holdout_df)} across seasons {HOLDOUT_SEASONS}\n")

    if train_df.empty or holdout_df.empty:
        raise ValueError(
            "Train or holdout set is empty after merge. Check TRAIN_SEASONS/"
            "HOLDOUT_SEASONS match what's actually in your CSVs, and check "
            "for name-matching drops (see [warn] messages above)."
        )

    print("Fitting exponent per position on training data...")
    fits = fit_all_positions(train_df)
    for pos, f in sorted(fits.items()):
        print(f"  {pos}: exponent={f['exponent']:.3f}  train RMSE=${f['rmse']:.2f}  "
              f"train R^2={f['r2']:.3f}  spend_share={f['spend_share']:.3f}  n={f['n']}")

    print("\nValidating on holdout season(s)...")
    holdout_results = validate_on_holdout(holdout_df, fits)

    plot_fit(holdout_results)

    print("\n" + "=" * 60)
    print("FINAL EXPONENTS - drop these into calculate_prices()")
    print("=" * 60)
    for pos, f in sorted(fits.items()):
        print(f"  {pos!r}: {f['exponent']:.3f}")

    holdout_results.to_csv("holdout_predictions.csv", index=False)
    print("\nFull holdout predictions saved to holdout_predictions.csv "
          "for manual review (sort by abs(predicted - actual) to find the "
          "worst misses).")


if __name__ == "__main__":
    main()
