from __future__ import annotations

import polars as pl


def lttb(x: pl.Series, y: pl.Series, target: int) -> tuple[pl.Series, pl.Series]:
    """Largest-Triangle-Three-Buckets downsampling.

    Preserves visual shape for time-series charts — ideal for mid/PnL lines.
    Falls back to the original arrays if n <= target.
    """
    n = x.len()
    if target >= n or target < 3:
        return x, y

    xs = x.to_numpy()
    ys = y.to_numpy()
    bucket_size = (n - 2) / (target - 2)

    out_idx = [0]
    a = 0
    for i in range(target - 2):
        start = int((i + 1) * bucket_size) + 1
        end = int((i + 2) * bucket_size) + 1
        end = min(end, n)

        # average point of the NEXT bucket, used as fixed triangle vertex
        next_start = end
        next_end = min(int((i + 3) * bucket_size) + 1, n)
        if next_start >= next_end:
            avg_x = xs[-1]
            avg_y = ys[-1]
        else:
            avg_x = xs[next_start:next_end].mean()
            avg_y = ys[next_start:next_end].mean()

        max_area = -1.0
        chosen = start
        ax, ay = xs[a], ys[a]
        for j in range(start, end):
            area = abs(
                (ax - avg_x) * (ys[j] - ay) - (ax - xs[j]) * (avg_y - ay)
            )
            if area > max_area:
                max_area, chosen = area, j
        out_idx.append(chosen)
        a = chosen

    out_idx.append(n - 1)
    return x.gather(out_idx), y.gather(out_idx)


def bucket_mean(df: pl.DataFrame, *, x_col: str, y_cols: list[str], target: int) -> pl.DataFrame:
    """Timestamp-bucket mean downsampling for volume/spread style series."""
    n = df.height
    if target >= n or target < 2:
        return df

    bucket = (n + target - 1) // target
    return (
        df.with_row_index("__ridx__")
        .with_columns((pl.col("__ridx__") // bucket).alias("__bkt__"))
        .group_by("__bkt__", maintain_order=True)
        .agg([pl.col(x_col).first(), *(pl.col(c).mean() for c in y_cols)])
        .drop("__bkt__")
    )
