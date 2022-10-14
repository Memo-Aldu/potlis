import os
import hikari
import lightbulb
import logging
import json
import numpy as np
from datetime import datetime
from fake_useragent import UserAgent
from pytz import timezone

plugin = lightbulb.Plugin("BestBuy-plugin")

BEST_BUY_PRODUCT_API = os.getenv("BB_PRODUCT_API")
BB_STOCK_API = os.getenv("BB_STOCK_API")
BB_DEFAULT_LOCATION = os.getenv("DEFAULT_STORE_LOCATION")
BB_DEFAULT_URL = 'https://www.bestbuy.ca'
BB_AUTHOR_IMAGE_URL = 'https://upload.wikimedia.org/wikipedia/' \
                      'commons/thumb/f/f5/Best_Buy_Logo.svg/1200px-Best_Buy_Logo.svg.png'
EMBED_COLOR = '#eb9834'
log = logging.getLogger(__name__)
ua = UserAgent()
tz = timezone('US/Eastern')
header = {
    'authority': 'sdk.split.io',
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': ua.safari
}


@plugin.command
@lightbulb.command("bestbuy",
                   "Best buy scraping commands",
                   auto_defer=True
                   )
@lightbulb.implements(lightbulb.SlashCommandGroup, lightbulb.PrefixCommandGroup)
async def best_buy(ctx: lightbulb.Context) -> None:
    pass  # as slash commands cannot have their top-level command ran, we simply pass here


@best_buy.child()
@lightbulb.option(
    "query", "The product to search.", str, required=True
)
@lightbulb.command(
    "product",
    "Get product and stock info of a best buy product.",
    auto_defer=True
)
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def get_bestbuy_product_by_search_term(ctx: lightbulb.Context) -> None:
    query = ctx.options.query
    product_api_call = BEST_BUY_PRODUCT_API.format("ON", query)
    log.info(f"Best Buy query {query}"
             f" requested buy {ctx.user}")
    products = (
        await make_api_call(
            product_api_call, ctx.bot.d.session
        ))['products']
    log.info(f"Api response: {products}")
    if len(products) > 0:
        inventory_api_call = await build_inventory_api_call(products)
        inventory = (
            await make_api_call(
                inventory_api_call, ctx.bot.d.session
            ))['availabilities']
        log.info(f"Api response: {inventory}")
        embeds = make_embed(products=products, availabilities=inventory)
        log.info(f"Created {len(embeds)} embeds")
        embeds = np.array_split(embeds, len(embeds) // 10)
        for array in embeds:
            log.info(f"Sent {len(array)} embeds to channel"
                     f" {ctx.channel_id}")
            await ctx.respond(embeds=array)
        return
    elif len(products) == 0:
        log.info(f"Sending no product found for query {query}")
        await ctx.respond(
            f"No product was found with query {query}", components=[]
        )
    else:
        log.info("Sending API call fail message")
        await ctx.respond(
            f"Failed to get data for query {query}", components=[]
        )


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)


async def build_inventory_api_call(products: list) -> str:
    log.info("Building inventory api call for"
             f" {list}")
    sku_query = ''
    for product in products:
        sku_query += product['sku'] + "%7C"
    return BB_STOCK_API.format(BB_DEFAULT_LOCATION, sku_query)


async def make_api_call(api_call, session) -> any:
    log.info(f"Making api call with"
             f" {api_call}")
    start_time = datetime.now()
    async with session.get(api_call, headers=header) \
            as response:
        api_call_time = datetime.now() - start_time
        log.info(f"Best Buy API request {api_call}"
                 f" took {api_call_time}")
        if response.ok:
            raw_text = await response.text()
            text_without_bom = raw_text.encode().decode('utf-8-sig')
            json.loads(text_without_bom)
            return json.loads(text_without_bom)
        else:
            log.error(f"API call {api_call} FAILED"
                      f" server returned status {response.status}."
                      f" server returned {response}")
    return None


def make_embed(products, availabilities):
    date = datetime.now(tz).replace(microsecond=0)
    embed_list = []
    index = 0
    for product in products:
        availability = availabilities[index]
        index += 1
        if str(availability['pickup']['purchasable']) == 'false' and \
                str(availability['shipping']['purchasable']) == 'false':
            continue

        product_desc_hyper = get_description_hyperlink(
            product['shortDescription'], BB_DEFAULT_URL + product['productUrl'])
        embed = (
            hikari.Embed(title=product['name'],
                         description=product_desc_hyper,
                         colour=hikari.Colour.of(EMBED_COLOR))
            .add_field("Regular💸", product['regularPrice'], inline=True)
            .add_field("Sale💸", product['salePrice'], inline=True)
            .set_image(product['thumbnailImage'])
            .set_footer(f"SKU: {product['sku']} "
                        f"requested at: {date}")
            .set_author(name="Best Buy", icon=BB_AUTHOR_IMAGE_URL)
        )
        online_quantity = availability['shipping']['quantityRemaining']
        pickup_location = ''
        total_in_store_quantity = 0
        if len(availability['pickup']['locations']) > 0:
            for location in availability['pickup']['locations']:
                store_quantity = int(location['quantityOnHand'])
                if store_quantity > 0:
                    pickup_location += "**" + location['name'] + "**" + " has: " + \
                                       str(store_quantity) + " | "
                    total_in_store_quantity += store_quantity
        online_store_status = filter_status(availability['shipping']['status'])
        store_status = filter_status(availability['pickup']['status'])

        if online_quantity > 0:
            online_store_status += ": " + str(online_quantity)
        embed.add_field(name="Online Store", value=online_store_status, inline=True)
        if total_in_store_quantity > 0:
            embed.add_field(name="📍", value=pickup_location, inline=False)
            store_status += ": " + str(total_in_store_quantity)
        embed.add_field(name="In Store", value=store_status, inline=True)
        embed_list.append(embed)
    return embed_list


def get_description_hyperlink(desc, hyperlink):
    half = slice(0, len(desc) // 2)
    return "[" + desc[half] + "...]" + \
           "(" + hyperlink + ")"


def filter_status(status):
    if status == "OutOfStock":
        return "Out Of Stock"
    elif status == "ComingSoon":
        return "Coming Soon"
    elif status == "BackOrder":
        return "Back Order-able"
    elif status == "InStock":
        return "In Stock"
    elif status == "SoldOutOnline":
        return "Sold Out"
    elif status == "NotAvailable":
        return "Not Available"
    else:
        return status
