import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

import config
import db


class RedactFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        for s in config.SECRETS:
            msg = msg.replace(s, "[REDACTED]")
        record.msg, record.args = msg, ()
        return True


handler = logging.StreamHandler(sys.stdout)
handler.addFilter(RedactFilter())
logging.basicConfig(level=logging.INFO, handlers=[handler],
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dropbot")


class DropBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())

    async def setup_hook(self):
        await db.init()
        for ext in ("cogs.products", "cogs.orders", "cogs.reports"):
            await self.load_extension(ext)
        if config.GUILD_ID:
            g = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()
        log.info("Commands synced. SIMULATION_MODE=%s DB=%s", config.SIMULATION_MODE, config.DB_PATH)

    async def on_ready(self):
        log.info("Online as %s", self.user)


bot = DropBot()


@bot.tree.error
async def on_app_error(i: discord.Interaction, err: app_commands.AppCommandError):
    if isinstance(err, app_commands.MissingPermissions):
        msg = "You need the Manage Server permission for that."
    else:
        log.error("Command error: %r", err)
        msg = "Something went wrong. It has been logged."
    if i.response.is_done():
        await i.followup.send(msg, ephemeral=True)
    else:
        await i.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        sys.exit("DISCORD_TOKEN is not set. Add it in Railway > Variables.")
    bot.run(config.DISCORD_TOKEN, log_handler=None, reconnect=True)
