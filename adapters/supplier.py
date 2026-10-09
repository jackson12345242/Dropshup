"""Supplier adapter interface. Implement SupplierAdapter for any legitimate,
authorized supplier API/feed, then register it in get_supplier()."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import config


@dataclass
class SupplierQuote:
    cost: float
    in_stock: Optional[bool] = None
    source: str = ""


class SupplierAdapter(ABC):
    name = "base"

    @abstractmethod
    async def get_quote(self, product_url: str) -> Optional[SupplierQuote]:
        """Return a real quote from the supplier, or None if unavailable."""

    async def place_order(self, *args, **kwargs):
        raise NotImplementedError("Ordering is disabled until a supplier integration is authorized.")


class ManualSupplierAdapter(SupplierAdapter):
    """Prototype adapter: no API, so it never returns data. Costs are what you enter."""
    name = "manual"

    async def get_quote(self, product_url: str):
        return None


class ExampleApiSupplierAdapter(SupplierAdapter):
    """Template for a real supplier. Fill in with the supplier's OFFICIAL API docs.
    Do not scrape sites that forbid it."""
    name = "example-api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_quote(self, product_url: str):
        raise NotImplementedError("Implement against your supplier's official API.")


def get_supplier() -> SupplierAdapter:
    if config.SUPPLIER_API_KEY:
        return ExampleApiSupplierAdapter(config.SUPPLIER_API_KEY)
    return ManualSupplierAdapter()
