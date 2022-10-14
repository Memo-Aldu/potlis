from __future__ import annotations
import asyncio
import os
import miru
import json
from dotenv import load_dotenv
import hikari
import lightbulb
import logging
from __init__ import __version__
from aiohttp import ClientSession
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)
load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILDS = [944703399360860200]
OWNERS = json.loads(os.environ['OWNER_ID'])
STDOUT_CHANNEL_ID = os.getenv("STDOUT_CHANNEL_ID")

print(OWNERS)


def setup() -> None:
    log.info("Running bot setup...")


bot = lightbulb.BotApp(
    token=TOKEN,
    default_enabled_guilds=GUILDS,
    owner_ids=OWNERS,
    help_slash_command=True,
    case_insensitive_prefix_commands=True,
    prefix="$",
    intents=hikari.Intents.ALL

)
bot.d.scheduler = AsyncIOScheduler()
bot.d.scheduler.configure(timezome=timezone('US/Eastern'))
bot.load_extensions_from("../potlis/extensions")
miru.load(bot)


def run() -> None:
    setup()
    bot.run(
        activity=hikari.Activity(
            name=f"/help | Version {__version__}",
            type=hikari.ActivityType.WATCHING
        )
    )


@bot.listen(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    bot.d.scheduler.start()
    bot.d.session = ClientSession(trust_env=True)
    log.info("AIOHTTP session started")


@bot.listen(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    await bot.rest.create_message(
        int(STDOUT_CHANNEL_ID),
        f"Potlis is now online! (Version {__version__})"
    )


@bot.listen(hikari.StoppingEvent)
async def on_stopping(event: hikari.StoppingEvent) -> None:
    await bot.d.session.close()
    log.info("AIOHTTP session closed")
    bot.d.scheduler.shutdown()
    await bot.rest.create_message(
        int(STDOUT_CHANNEL_ID),
        f"Potlis is shutting down. (Version {__version__})"
    )


@bot.command
@lightbulb.command('ping', 'say pong!')
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def ping(ctx):
    await ctx.respond(
        f"Pong! DWSP latency: {ctx.bot.heartbeat_latency * 1_000:,.0f} ms.")


@bot.listen(lightbulb.CommandErrorEvent)
async def on_command_error(event: lightbulb.CommandErrorEvent) -> None:
    exc = getattr(event.exception, "__cause__", event.exception)

    if isinstance(exc, lightbulb.NotOwner):
        await event.context.respond("You need to be an owner to do that.")
        return
    raise event.exception
