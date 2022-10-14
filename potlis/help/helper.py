import lightbulb


def is_admin(ctx: lightbulb.Context) -> bool:
    return ctx.user.id in ctx.bot.owner_ids
