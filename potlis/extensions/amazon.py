import lightbulb
import logging

plugin = lightbulb.Plugin("Amazon-plugin")
log = logging.getLogger(__name__)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
