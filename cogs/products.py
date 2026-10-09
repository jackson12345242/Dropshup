import discord
from discord import app_commands
from discord.ext import commands

import db
import fees
from adapters import research

NOTE = "Estimate from your inputs and fee assumptions; not actual profit or a guarantee."


def _row_est(p):
    return fees.estimate(p["selling_price"], p["supplier_cost"], p["shipping_cost"], p["other_expenses"])


class Products(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    product = app_commands.Group(name="product", description="Manage products")

    @product.command(name="add", description="Save a product")
    @app_commands.describe(name="Product name", supplier_cost="Cost per unit from supplier",
                           selling_price="Planned Amazon selling price", url="Product URL",
                           shipping_cost="Shipping per unit", other_expenses="Other per-unit expenses")
    async def add(self, i: discord.Interaction, name: app_commands.Range[str, 1, 200],
                  supplier_cost: app_commands.Range[float, 0.0, 100000.0],
                  selling_price: app_commands.Range[float, 0.01, 100000.0], url: str,
                  shipping_cost: app_commands.Range[float, 0.0, 100000.0] = 0,
                  other_expenses: app_commands.Range[float, 0.0, 100000.0] = 0):
        if not url.startswith(("http://", "https://")) or len(url) > 500:
            return await i.response.send_message("URL must start with http:// or https://", ephemeral=True)
        pid = await db.execute(
            "INSERT INTO products(name,supplier_cost,selling_price,url,shipping_cost,other_expenses,added_by)"
            " VALUES(?,?,?,?,?,?,?)", (name, supplier_cost, selling_price, url, shipping_cost, other_expenses, i.user.id))
        b = fees.estimate(selling_price, supplier_cost, shipping_cost, other_expenses)
        await i.response.send_message(
            f"Saved **{name}** as product `#{pid}`. Estimated profit/unit: **{fees.money(b.profit)}** "
            f"({b.margin_pct:.1f}% margin). {NOTE}")

    @product.command(name="analyze", description="Estimate profit for a saved product")
    @app_commands.describe(product_id="Product ID", quantity="Units")
    async def analyze(self, i: discord.Interaction, product_id: int, quantity: app_commands.Range[int, 1, 10000] = 1):
        rows = await db.fetch("SELECT * FROM products WHERE id=?", (product_id,))
        if not rows:
            return await i.response.send_message("Product not found.", ephemeral=True)
        p = rows[0]
        b = fees.estimate(p["selling_price"], p["supplier_cost"], p["shipping_cost"], p["other_expenses"], quantity)
        e = discord.Embed(title=f"Estimate: {p['name']} x{quantity}",
                          colour=discord.Colour.green() if b.profit > 0 else discord.Colour.red())
        e.add_field(name="Revenue", value=fees.money(b.revenue))
        e.add_field(name="Supplier", value=fees.money(b.supplier_cost))
        e.add_field(name="Shipping", value=fees.money(b.shipping))
        e.add_field(name="Other", value=fees.money(b.other))
        e.add_field(name="Referral fee", value=fees.money(b.referral_fee))
        e.add_field(name="Fulfillment", value=fees.money(b.fulfillment_fee))
        e.add_field(name="Payment fee", value=fees.money(b.payment_fee))
        e.add_field(name="ESTIMATED profit", value=f"**{fees.money(b.profit)}**")
        e.add_field(name="Margin / ROI", value=f"{b.margin_pct:.1f}% / {b.roi_pct:.1f}%")
        e.set_footer(text=NOTE)
        await i.response.send_message(embed=e)

    @product.command(name="remove", description="Delete a saved product")
    async def remove(self, i: discord.Interaction, product_id: int):
        used = await db.fetch("SELECT 1 FROM orders WHERE product_id=? LIMIT 1", (product_id,))
        if used:
            return await i.response.send_message("Product has orders; it can't be removed.", ephemeral=True)
        await db.execute("DELETE FROM products WHERE id=?", (product_id,))
        await i.response.send_message(f"Removed product `#{product_id}` (if it existed).")

    @app_commands.command(name="products", description="Saved products ranked by estimated profit")
    async def products(self, i: discord.Interaction):
        rows = await db.fetch("SELECT * FROM products")
        if not rows:
            return await i.response.send_message("No products yet. Use `/product add`.")
        ranked = sorted(rows, key=lambda p: _row_est(p).profit, reverse=True)[:20]
        lines = []
        for n, p in enumerate(ranked, 1):
            b = _row_est(p)
            lines.append(f"{n}. `#{p['id']}` **{p['name'][:60]}** - est. {fees.money(b.profit)}/unit ({b.margin_pct:.0f}%)")
        await i.response.send_message("**Products by ESTIMATED profit**\n" + "\n".join(lines) + f"\n_{NOTE}_")

    @app_commands.command(name="research", description="Screen saved products against your margin threshold")
    async def research(self, i: discord.Interaction):
        rows = await db.fetch("SELECT * FROM products")
        if not rows:
            return await i.response.send_message("Nothing to screen. Add candidates with `/product add`.")
        res = research.screen(rows)[:15]
        lines = [f"{'PASS' if r['passes'] else 'fail'} `#{r['id']}` {r['name'][:50]} - {r['b'].margin_pct:.0f}% est. margin"
                 for r in res]
        await i.response.send_message(
            "**Margin screen** (no external market data connected, so no demand/sales claims are made)\n" + "\n".join(lines))


async def setup(bot):
    await bot.add_cog(Products(bot))
