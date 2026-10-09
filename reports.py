import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import db
import fees
from adapters.supplier import get_supplier

log = logging.getLogger("dropbot.reports")


async def build_summary() -> discord.Embed:
    rows = await db.fetch("SELECT o.*, p.supplier_cost, p.shipping_cost, p.other_expenses FROM orders o "
                          "JOIN products p ON p.id=o.product_id WHERE o.status!='cancelled'")
    revenue = sum(o["sale_price"] * o["quantity"] for o in rows)
    est = sum(o["est_profit"] for o in rows)
    settled = [o for o in rows if o["actual_profit"] is not None]
    actual = sum(o["actual_profit"] for o in settled)
    est_costs = revenue - est
    e = discord.Embed(title="Profit summary", colour=discord.Colour.blurple())
    e.add_field(name="Orders counted", value=str(len(rows)))
    e.add_field(name="Revenue (order records)", value=fees.money(revenue))
    e.add_field(name="Estimated total costs", value=fees.money(est_costs))
    e.add_field(name="ESTIMATED net profit", value=fees.money(est), inline=False)
    e.add_field(name=f"ACTUAL profit ({len(settled)} settled orders, user-entered)",
                value=fees.money(actual) if settled else "None settled yet", inline=False)
    mode = "SIMULATION MODE" if config.SIMULATION_MODE else "live mode"
    e.set_footer(text=f"{mode}. Estimates are not guarantees of earnings.")
    return e


class Reports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily.change_interval(time=dt.time(hour=config.REPORT_HOUR_UTC, tzinfo=dt.timezone.utc))
        self.refresh.change_interval(minutes=config.REFRESH_MINUTES)

    async def cog_load(self):
        self.daily.start()
        self.refresh.start()

    async def cog_unload(self):
        self.daily.cancel()
        self.refresh.cancel()

    async def paused(self) -> bool:
        return (await db.get_setting("paused", "0")) == "1"

    async def alert(self, text: str):
        """Post a short, secret-free error notice to the report channel."""
        ch = self.bot.get_channel(config.REPORT_CHANNEL_ID) if config.REPORT_CHANNEL_ID else None
        if ch:
            try:
                await ch.send(f"Warning: {text[:500]}")
            except discord.HTTPException:
                pass

    @tasks.loop(minutes=60)
    async def refresh(self):
        if await self.paused():
            return
        try:
            supplier = get_supplier()
            changed = 0
            for p in await db.fetch("SELECT id, url, supplier_cost FROM products"):
                q = await supplier.get_quote(p["url"])
                if q and q.cost > 0 and q.cost != p["supplier_cost"]:
                    await db.execute("UPDATE products SET supplier_cost=? WHERE id=?", (q.cost, p["id"]))
                    changed += 1
            log.info("Refresh complete via %s adapter; %d updated", supplier.name, changed)
        except NotImplementedError:
            log.warning("Supplier adapter not implemented; skipping refresh")
        except Exception:
            log.exception("Refresh failed")
            await self.alert("Product refresh failed; see Railway logs.")

    @tasks.loop(time=dt.time(hour=14, tzinfo=dt.timezone.utc))
    async def daily(self):
        if await self.paused():
            return
        try:
            ch = self.bot.get_channel(config.REPORT_CHANNEL_ID)
            if ch:
                await ch.send("**Daily report**", embed=await build_summary())
        except Exception:
            log.exception("Daily report failed")

    @refresh.before_loop
    @daily.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="profit", description="Revenue, costs, estimated vs actual profit")
    async def profit(self, i: discord.Interaction):
        await i.response.send_message(embed=await build_summary())

    @app_commands.command(name="dailyreport", description="Send the daily report now")
    async def dailyreport(self, i: discord.Interaction):
        await i.response.defer()
        await i.followup.send("**Daily report**", embed=await build_summary())

    @app_commands.command(name="pause", description="Pause background automation")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pause(self, i: discord.Interaction):
        await db.set_setting("paused", "1")
        await i.response.send_message("Background automation paused.")

    @app_commands.command(name="resume", description="Resume background automation")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def resume(self, i: discord.Interaction):
        await db.set_setting("paused", "0")
        await i.response.send_message("Background automation resumed.")


async def setup(bot):
    await bot.add_cog(Reports(bot))
