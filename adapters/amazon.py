"""Amazon Selling Partner API (SP-API) adapter, DISABLED until authorized.

Safety gates for any write action (listing, inventory, orders):
  1. SIMULATION_MODE must be false
  2. SP-API credentials must be present
  3. The caller must pass approved=True after explicit human approval
Otherwise the action is simulated and logged only."""
import logging

import config

log = logging.getLogger("dropbot.amazon")


class AmazonNotAuthorized(Exception):
    pass


class AmazonAdapter:
    @property
    def configured(self) -> bool:
        return all(config.SPAPI_CREDS.values())

    @property
    def live(self) -> bool:
        return self.configured and not config.SIMULATION_MODE

    def _gate(self, action: str, approved: bool) -> bool:
        """True only if a real call may proceed; False means simulate."""
        if not self.live:
            log.info("SIMULATED %s (simulation mode or no credentials)", action)
            return False
        if not approved:
            raise AmazonNotAuthorized(f"{action} requires explicit approval.")
        return True

    async def get_catalog_info(self, asin: str):
        if not self.live:
            return None
        # TODO when authorized: LWA token exchange + Catalog Items API (read-only).
        raise NotImplementedError("Connect SP-API read endpoints after authorization.")

    async def create_listing(self, sku: str, payload: dict, approved: bool = False) -> dict:
        if not self._gate("create_listing", approved):
            return {"simulated": True, "sku": sku}
        raise NotImplementedError("Listings API call goes here once authorized.")

    async def update_inventory(self, sku: str, qty: int, approved: bool = False) -> dict:
        if not self._gate("update_inventory", approved):
            return {"simulated": True, "sku": sku, "qty": qty}
        raise NotImplementedError("Inventory call goes here once authorized.")
