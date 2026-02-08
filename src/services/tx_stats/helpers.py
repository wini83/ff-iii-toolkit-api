from typing import Any, cast

import pandas as pd
from anyio import to_thread

from services.domain.transaction import Transaction


def txs_to_df(txs: list[Transaction]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": tx.date,
            "tags": tx.tags,
        }
        for tx in txs
    )


def _group_tx_by_month_sync(txs: list[Transaction]) -> dict[str, int]:
    if not txs:
        return {}

    df = txs_to_df(txs)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    dt = cast(Any, df["date"].dt)
    df["month"] = dt.to_period("M").astype(str)

    return df.groupby("month").size().sort_index().to_dict()


async def group_tx_by_month(
    txs: list[Transaction],
) -> dict[str, int]:
    return await to_thread.run_sync(_group_tx_by_month_sync, txs)
