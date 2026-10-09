from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
import db
import fees

STATUSES = ["pending", "ordered_from_supplier", "shipped", "delivered", "cancelled", "returned"]


class Orders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    order = app_commands.Group(name="order", description="Track orders (records only; nothing is purchased)")

    @order.command(name="add", description="Record an order (no real purchase is made)")
    async def add(self, i: discord.Interaction, product_id: int,
                  quantity: app_commands.Range[int, 1, 10000] = 1,
                  sale_price: Optional[app_commands.Range[float, 0.01, 100000]] = None):
        rows = await db.fetch("SELECT * FROM products WHERE id=?", (product_id,))
        if not rows:
            return await i.response.send_message("Product not found.", ephemeral=True)
        p = rows[0]
        price = sale_price or p["selling_price"]
        b = fees.estimate(price, p["supplier_cost"], p["shipping_cost"], p["other_expenses"], quantity)
        oid = await db.execute(
            "INSERT INTO orders(product_id,quantity,sale_price,est_profit,simulated) VALUES(?,?,?,?,?)",
            (product_id, quantity, price, b.profit, 1 if config.SIMULATION_MODE else 0))
        await i.response.send_message(f"Recorded order `#{oid}` ({'SIMULATED' if config.SIMULATION_MODE else 'manual'}). "
                                      f"Est. profit {fees.money(b.profit)}.")

    @order.command(name="status", description="Update an order's status")
    @app_commands.choices(status=[app_commands.Choice(name=s, value=s) for s in STATUSES])
    async def status(self, i: discord.Interaction, order_id: int, status: app_commands.Choice[str]):
        await db.execute("UPDATE orders SET status=?, updated_at=datetime('now') WHERE id=?", (status.value, order_id))
        await i.response.send_message(f"Order `#{order_id}` -> **{status.value}**")

    @order.command(name="settle", description="Enter ACTUAL costs once an order is complete")
    @app_commands.describe(actual_supplier_cost="Total paid to supplier", actual_fees="Total Amazon fees charged",
                           actual_shipping_other="Shipping + other real costs")
    async def settle(self, i: discord.Interaction, order_id: int,
                     actual_supplier_cost: app_commands.Range[float, 0, 1e7],
                     actual_fees: app_commands.Range[float, 0, 1e7],
                     actual_shipping_other: app_commands.Range[float, 0, 1e7] = 0):
        rows = await db.fetch("SELECT * FROM orders WHERE id=?", (order_id,))
        if not rows:
            return await i.response.send_message("Order not found.", ephemeral=True)
        o = rows[0]
        actual = o["sale_price"] * o["quantity"] - actual_supplier_cost - actual_fees - actual_shipping_other
        await db.execute("UPDATE orders SET actual_profit=?, updated_at=datetime('now') WHERE id=?", (actual, order_id))
        await i.response.send_message(f"Order `#{order_id}` actual profit (from the numbers you entered): **{fees.money(actual)}**")

    @app_commands.command(name="orders", description="List recent orders")
    @app_commands.choices(status=[app_commands.Choice(name=s, value=s) for s in STATUSES])
    async def orders(self, i: discord.Interaction, status: Optional[app_commands.Choice[str]] = None):
        sql = ("SELECT o.*, p.name FROM orders o JOIN products p ON p.id=o.product_id "
               + ("WHERE o.status=? " if status else "") + "ORDER BY o.id DESC LIMIT 20")
        rows = await db.fetch(sql, (status.value,) if status else ())
        if not rows:
            return await i.response.send_message("No orders found.")
        lines = [f"`#{o['id']}` {o['name'][:40]} x{o['quantity']} - **{o['status']}**"
                 f"{' (sim)' if o['simulated'] else ''} - est. {fees.money(o['est_profit'])}"
                 + (f", actual {fees.money(o['actual_profit'])}" if o["actual_profit"] is not None else "")
                 for o in rows]
        await i.response.send_message("\n".join(lines))


async def setup(bot):
    await bot.add_cog(Orders(bot))
