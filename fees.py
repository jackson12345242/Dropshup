"""Profit estimation. Every number here is an ESTIMATE built from user-entered
inputs and configurable fee assumptions. Nothing is fetched or invented."""
from dataclasses import dataclass

import config


@dataclass
class Breakdown:
    revenue: float
    supplier_cost: float
    shipping: float
    other: float
    referral_fee: float
    fulfillment_fee: float
    payment_fee: float
    profit: float
    margin_pct: float
    roi_pct: float

    @property
    def total_costs(self) -> float:
        return (self.supplier_cost + self.shipping + self.other + self.referral_fee
                + self.fulfillment_fee + self.payment_fee)


def estimate(selling_price: float, supplier_cost: float, shipping: float = 0.0,
             other: float = 0.0, quantity: int = 1) -> Breakdown:
    q = max(quantity, 1)
    revenue = selling_price * q
    referral = revenue * config.REFERRAL_FEE_PCT / 100
    payment = revenue * config.PAYMENT_FEE_PCT / 100
    fulfil = config.FULFILLMENT_FEE * q
    sup, ship, oth = supplier_cost * q, shipping * q, other * q
    profit = revenue - sup - ship - oth - referral - payment - fulfil
    margin = (profit / revenue * 100) if revenue else 0.0
    invested = sup + ship + oth
    roi = (profit / invested * 100) if invested else 0.0
    return Breakdown(revenue, sup, ship, oth, referral, fulfil, payment, profit, margin, roi)


def money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"
