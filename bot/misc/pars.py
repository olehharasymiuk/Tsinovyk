import asyncio
import datetime
import logging
import random

import aiohttp
import requests
import tldextract
from bs4 import BeautifulSoup
from fake_headers import Headers

from bot.data.texts import reply_to_start_tracking
from bot.database.models.goods import OrdersPrices, Url, User, Order, UsersOrders
from bot.misc.functions import Shop, my_hash, clear_price
from googlesearch import search as g_search
from bot.middlewares.locale_middleware import get_text as _


class Product:

    def __init__(self, url):
        self.url = url
        self.product_title = None
        self.ware_id = None

    def get_price_and_title(self, shop):

        user_agent = Headers(headers=True).generate()
        user_agent['Accept-Encoding'] = 'identity'
        resp = requests.get(self.url, headers=user_agent)

        if not resp.ok:
            logg.error(f'{self.url}, {shop.product_title_class, shop.product_price_class}, {resp.status_code}')

        try:
            resp.encoding = resp.apparent_encoding
            f = BeautifulSoup(resp.text, "lxml")
            print(shop.product_price_class, shop.product_title_class)
            product_price = f.find(class_=shop.product_price_class).text
            self.product_title = f.find(class_=shop.product_title_class).text
            self.ware_id = my_hash(self.product_title)

            return clear_price(product_price.strip()), self.product_title.strip()

        except AttributeError as e:
            logg.exception(f'{e}, {self.url}, {shop.product_price_class, shop.product_title_class}')
            return False, False

    async def find_in_another_store(self):

        first_domain = tldextract.extract(self.url).domain
        domains = [first_domain]
        tasks = []

        for url in g_search(self.product_title, pause=5, stop=100, lang='uk'):
            await asyncio.sleep(0.01)
            shop = Shop(url)
            if shop and shop.domain not in domains:
                task = asyncio.create_task(self.save_from_others_stores(url))
                tasks.append(task)

        await asyncio.gather(*tasks)

    async def save_from_others_stores(self, url=None, ware_id=None):
        if not ware_id:
            ware_id = self.ware_id
        if not url:
            url = self.url
            
        connector = aiohttp.TCPConnector(force_close=True)
        user_agent = Headers(headers=True).generate()
        user_agent['Accept-Encoding'] = 'identity'
        shop = Shop(url)
        price = None

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=user_agent) as response:

                # if not response.ok:
                #     logg.warning(url, params, response.status_code)

                try:
                    f = BeautifulSoup(await response.text(), "lxml")

                    product_price = f.find(class_=shop.product_price_class)
                    if product_price and product_price != 0:
                        product_price = product_price.text

                        price = clear_price(product_price.strip())

                except AttributeError as e:
                    logg.exception(f'{e}, {url}, {shop.product_price_class, shop.product_title_class}')

                if isinstance(price, int):
                    if not Url.get_or_none(Url.ware_id == ware_id):
                        Url.create(ware_id=ware_id, url=url).save()
                    OrdersPrices.create(ware_id=ware_id, date=datetime.date.today(), price=price,
                                        store=shop.domain).save()

    def save_to_db(self, user_id: int, price: int) -> [int, str]:
        today = datetime.date.today()
        domain = tldextract.extract(self.url).domain

        if not User.get_or_none(User.user_id == user_id):
            User.create(user_id=user_id).save()

        if not Order.get_or_none(Order.name == self.product_title):

            Order.create(ware_id=self.ware_id, name=self.product_title, date=today, url=self.url).save()
            UsersOrders.create(user_id=user_id, ware_id=self.ware_id, date=today).save()
            OrdersPrices.create(ware_id=self.ware_id, date=today, price=price, store=domain).save()
            Url.create(ware_id=self.ware_id, url=self.url)
            code, message = 200, _(random.choice(reply_to_start_tracking))

        else:

            if UsersOrders.check_availability_on_user(user_id, self.ware_id):
                code, message = 300, _('Already following 😎')

            else:

                UsersOrders.create(user_id=user_id, ware_id=self.ware_id, date=today).save()
                code, message = 200, _('Started following 🫡')

        return code, message



# def big_parser(url: str, params: list):
#     user_agent = Headers(headers=True).generate()
#     user_agent['Accept-Encoding'] = 'identity'
#     resp = requests.get(url, headers=user_agent)
#
#     if not resp.ok:
#         logg.error(f'{url}, {params}, {resp.status_code}')
#
#     try:
#         resp.encoding = resp.apparent_encoding
#         f = BeautifulSoup(resp.text, "lxml")
#         product_price = f.find(class_=params[0]).text
#         product_title = f.find(class_=params[1]).text
#
#         return clear_price(product_price.strip()), product_title.strip()
#
#     except AttributeError as e:
#         logg.exception(f'{e}, {url}, {params}')
#         return False, False


# async def small_parser(url, ware_id):
#
#     user_agent = Headers(headers=True).generate()
#     user_agent['Accept-Encoding'] = 'identity'
#     shop = Shop(url)
#
#     if shop:
#
#         price = None
#         connector = aiohttp.TCPConnector(force_close=True)
#
#         async with aiohttp.ClientSession(connector=connector) as session:
#             async with session.get(url, headers=user_agent) as response:
#
#                 # if not response.ok:
#                 #     logg.warning(url, params, response.status_code)
#
#                 try:
#                     f = BeautifulSoup(await response.text(), "lxml")
#
#                     product_price = f.find(class_=shop.product_price_class)
#                     if product_price and product_price != 0:
#                         product_price = product_price.text
#
#                         price = clear_price(product_price.strip())
#
#                 except AttributeError as e:
#                     logg.exception(f'{e}, {url}, {shop.product_price_class, shop.product_title_class}')
#
#                 if not isinstance(price, int):
#                     price = None
#
#                 OrdersPrices.create(ware_id=ware_id, date=datetime.date.today(), price=price, store=shop.domain).save()


# async def save_from_others_stores(url, ware_id):
#     user_agent = Headers(headers=True).generate()
#     user_agent['Accept-Encoding'] = 'identity'
#     shop = Shop(url)
#     price = None
#     connector = aiohttp.TCPConnector(force_close=True)
#
#     async with aiohttp.ClientSession(connector=connector) as session:
#         async with session.get(url, headers=user_agent) as response:
#
#
#             # if not response.ok:
#             #     logg.warning(url, params, response.status_code)
#
#             try:
#                 f = BeautifulSoup(await response.text(), "lxml")
#
#                 product_price = f.find(class_=shop.product_price_class)
#                 if product_price and product_price != 0:
#                     product_price = product_price.text
#
#                     price = clear_price(product_price.strip())
#
#             except AttributeError as e:
#                 logg.exception(f'{e}, {url}, {shop.product_price_class, shop.product_title_class}')
#
#             if isinstance(price, int):
#                 Url.create(ware_id=ware_id, url=url).save()
#                 OrdersPrices.create(ware_id=ware_id, date=datetime.date.today(), price=price, store=shop.domain).save()


# async def find_product_in_another_store(product_name, first_domain):
#
#     ware_id = my_hash(product_name)
#     domains = [first_domain]
#     tasks = []
#
#     for url in g_search(product_name, pause=5, stop=100, lang='uk'):
#         await asyncio.sleep(0.01)
#         shop = Shop(url)
#         if shop and shop.domain not in domains:
#             task = asyncio.create_task(save_from_others_stores(url, ware_id))
#             tasks.append(task)
#
#     await asyncio.gather(*tasks)


def log():
    # Create a custom logger
    logger = logging.getLogger(__name__)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('file.log')
    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


logg = log()