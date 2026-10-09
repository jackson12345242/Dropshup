"""Product research from permitted data only. With no APIs connected, this
screens products YOU have saved (from your own research or supplier feeds you
are licensed to use) against margin thresholds. It never invents demand,
sales, or price data."""
import fees
import config


def screen(products) -> list[dict]:
    out = []
    for p in products:
        b = fees.estimate(p["selling_price"], p["supplier_cost"], p["shipping_cost"], p["other_expenses"])
        out.append({"id": p["id"], "name": p["name"], "b": b,
                    "passes": b.margin_pct >= config.MIN_MARGIN_PCT and b.profit > 0})
    out.sort(key=lambda r: r["b"].profit, reverse=True)
    return out
