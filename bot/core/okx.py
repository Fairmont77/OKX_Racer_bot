import asyncio
from copy import deepcopy
from time import time
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw import functions
from pyrogram.raw.functions.messages import RequestWebView
from bot.core.agents import generate_random_user_agent
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers

from random import randint


class OKX:
    def __init__(self, tg_client: Client):
        self.first_run = True
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''
        self.lock = asyncio.Lock()
        self.max_level_boosts = set()
        self.token_live_time = randint(3500, 3600)
        self.previous_boosts = []

    async def connect_tg_client(self, proxy: str):
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        if not self.tg_client.is_connected:
            try:
                await self.tg_client.connect()
            except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                raise InvalidSession(self.session_name)

    async def start_bot(self):
        peer = await self.tg_client.resolve_peer('OKX_official_bot')
        await self.tg_client.invoke(
            functions.messages.StartBot(
                bot=peer,
                peer=peer,
                start_param='linkCode_85739062',
                random_id=randint(1, 9999999),
            )
        )

    async def fetch_tg_web_data(self):
        try:
            peer = await self.tg_client.resolve_peer('OKX_official_bot')
            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url="https://www.okx.com/",
            ))
            return web_view.url
        except FloodWait as fl:
            await asyncio.sleep(fl.value + 3)
            return await self.fetch_tg_web_data()

    async def parse_tg_web_data(self, url):
        tg_web_data = unquote(
            string=unquote(string=url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
        query_id = tg_web_data.split('query_id=')[1].split('&user=')[0]
        user = quote(tg_web_data.split("&user=")[1].split('&auth_date=')[0])
        auth_date = tg_web_data.split('&auth_date=')[1].split('&hash=')[0]
        hash_ = tg_web_data.split('&hash=')[1]

        self.user_id = tg_web_data.split('"id":')[1].split(',"first_name"')[0]
        self.first_name = tg_web_data.split('"first_name":"')[1].split('","last_name"')[0]
        self.last_name = tg_web_data.split('"last_name":"')[1].split('","username"')[0]

        return f"query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}"

    async def get_tg_web_data(self, proxy: str | None) -> str:
        await self.connect_tg_client(proxy)
        bot_chat = await self.tg_client.get_chat("OKX_official_bot")
        user_messages = []
        async for message in self.tg_client.get_chat_history(bot_chat.id, limit=10):
            if message.from_user and message.from_user.is_self:
                user_messages.append(message.text)

        if "/start" not in user_messages:
            await self.start_bot()

        auth_url = await self.fetch_tg_web_data()
        return await self.parse_tg_web_data(auth_url)

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "extUserId": self.user_id,
                "extUserName": self.first_name + ' ' + self.last_name,
                "gameId": 1,
                "linkCode": 85739062
            }
            response = await http_client.post(f'https://www.okx.com/priapi/v1/affiliate/game/racer/info?t={int(time() * 1000)}', json=json_data)
            response.raise_for_status()
            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def process_task(self, http_client: aiohttp.ClientSession, task):
        try:
            payload = {"extUserId": self.user_id, "id": task['id']}
            response = await http_client.post(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/task?t={int(time() * 1000)}', json=payload)
            response.raise_for_status()
            response_json = await response.json()
            logger.success(f"{self.session_name} | Task <lc>{task['context']['name']}</lc> completed! | Reward: <e>+{task['points']}</e> points")
            return response_json
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while completing task {task['id']} | Error: {e}")

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/tasks?extUserId={self.user_id}&t={int(time() * 1000)}')
            response.raise_for_status()
            tasks = (await response.json())['data']

            for task in tasks:
                if task['state'] == 0 and task['id'] not in {5, 9}:
                    await self.process_task(http_client, task)
                    await asyncio.sleep(delay=randint(5, 10))
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when completing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def get_boosts(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/boosts?extUserId={self.user_id}&t={int(time() * 1000)}')
            response.raise_for_status()
            response_data = await response.json()
            boosts = response_data.get('data', [])
            if boosts != self.previous_boosts:
                if not self.first_run:
                    logger.info(f"{self.session_name} | Boosts have changed, updating statistics.")
                self.print_boosts_statistics(boosts)
                self.previous_boosts = deepcopy(boosts)
            self.first_run = False
            return boosts
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting boosts | Error: {e}")

    def can_buy_boost(self, balance: str, boost: dict) -> bool:
        cost = boost['pointCost']
        cur_stage = boost['curStage']
        total_stage = boost['totalStage']
        if cur_stage >= total_stage:
            self.max_level_boosts.add(boost['id'])
            return False
        return balance > cost and cur_stage < total_stage

    async def buy_boost(self, http_client: aiohttp.ClientSession, boost_id: int, boost_name: str) -> bool:
        try:
            payload = {"extUserId": self.user_id, "id": boost_id}
            response = await http_client.post(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/boost?t={int(time() * 1000)}', json=payload)
            response.raise_for_status()
            if (await response.json()).get('code') == 0:
                logger.success(f"{self.session_name} | Successful purchase <lc>{boost_name}</lc>")
                return True
            return False
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while buying boost | Error: {e}")

    async def sleeper(self, ms):
        await asyncio.sleep(ms / 1000)

    async def get_current_price(self):
        url = 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=url) as response:
                    response_data = await response.json()
                    if response_data['code'] == '0' and 'data' in response_data and len(response_data['data']) > 0:
                        return float(response_data['data'][0]['last'])
                    else:
                        raise Exception('Unknown error while getting current price')
            except Exception as error:
                raise Exception(f'The current price is {error}')

    async def make_assess(self, http_client: aiohttp.ClientSession):
        try:
            price1 = await self.get_current_price()
            await self.sleeper(4000)
            price2 = await self.get_current_price()
            prediction = 0 if price1 > price2 else 1

            json_data = {
                "extUserId": self.user_id,
                "predict": prediction,
                "gameId": 1
            }
            response = await http_client.post(f'https://www.okx.com/priapi/v1/affiliate/game/racer/assess?t={int(time() * 1000)}', json=json_data)

            response_json = await response.json()
            if response_json.get('code') == 499004:
                logger.warning(f"{self.session_name} | Authorization error | Refreshing token...")
                return None

            response.raise_for_status()
            response_data = response_json['data']

            if response_data["won"]:
                added_points = response_data['basePoint'] * response_data['multiplier']
                logger.success(
                    f"{self.session_name} | <e>Win x </e><m>{response_data['multiplier']}</m> | Receive: <y>{added_points}</y> points | "
                    f"New balance: <lc>{response_data['balancePoints']}</lc> | "
                    f"Chances: <m>{response_data['numChance']}</m> | "
                    f"Combo: <m>x{response_data['curCombo']}</m>")
            else:
                logger.info(
                    f"{self.session_name} | <m>Lose</m> | Balance: <lc>{response_data['balancePoints']}</lc> |"
                    f" Chances: <m>{response_data['numChance']}</m>")

            return response_data

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when making assess: {error}")
            await asyncio.sleep(delay=3)

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        while True:
            try:
                if time() - access_token_created_time >= self.token_live_time:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    http_client.headers["X-Telegram-Init-Data"] = tg_web_data
                    user_info = await self.get_info_data(http_client=http_client)
                    access_token_created_time = time()

                    balance = user_info['data']['balancePoints']
                    logger.info(f"{self.session_name} | Balance: <e>{balance}</e>")
                    await self.processing_tasks(http_client=http_client)
                    await asyncio.sleep(delay=randint(10, 15))

                user_info = await self.get_info_data(http_client=http_client)
                chances = user_info['data']['numChances']
                refresh_time = user_info['data']['secondToRefresh']
                balance = user_info['data']['balancePoints']

                if settings.AUTO_BOOST:
                    boosts = await self.get_boosts(http_client=http_client)
                    for boost in boosts:
                        if boost['id'] in self.max_level_boosts:
                            continue

                        boost_name = boost['context']['name']
                        boost_id = boost['id']
                        if (boost_id == 2 or boost_id == 3) and settings.BOOSTERS[boost_name]:
                            if self.can_buy_boost(balance, boost):
                                result = await self.buy_boost(http_client=http_client, boost_id=boost_id, boost_name=boost_name)
                                if result:
                                    logger.info(f"{self.session_name} | <lc>{boost_name}</lc> upgraded to <m>{boost['curStage'] + 1}</m> lvl")

                if chances == 0 and refresh_time > 0:
                    logger.info(f"{self.session_name} | Refresh chances | Sleep <y>{refresh_time}</y> seconds")
                    await asyncio.sleep(refresh_time)
                    chances += 1

                sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                for _ in range(chances):
                    response_data = await self.make_assess(http_client=http_client)
                    if response_data is None:
                        await asyncio.sleep(delay=sleep_time)
                        break
                    else:
                        if response_data.get('numChance') == 0 and settings.AUTO_BOOST:
                            boost = next((boost for boost in boosts if boost['id'] == 1), None)
                            if self.can_buy_boost(balance, boost):
                                if await self.buy_boost(http_client=http_client, boost_id=boost['id'], boost_name=boost['context']['name']):
                                    sleep_time = randint(1, 3)
                                    continue
                            else:
                                break
                    await asyncio.sleep(delay=randint(1, 3))

                if settings.AUTO_BOOST:
                    boosts = await self.get_boosts(http_client=http_client)
                    for boost in boosts:
                        if boost['id'] in self.max_level_boosts:
                            continue

                        boost_name = boost['context']['name']
                        boost_id = boost['id']
                        if (boost_id == 2 or boost_id == 3) and settings.BOOSTERS[boost_name]:
                            if self.can_buy_boost(balance, boost):
                                result = await self.buy_boost(http_client=http_client, boost_id=boost_id, boost_name=boost_name)
                                if result:
                                    logger.info(f"{self.session_name} | <lc>{boost_name}</lc> upgraded to <m>{boost['curStage'] + 1}</m> lvl")

                logger.info(f"{self.session_name} | Sleep <y>{sleep_time}</y> seconds")
                await asyncio.sleep(sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

    def print_boosts_statistics(self, boosts):
        auto_driving = next((boost for boost in boosts if boost['id'] == 8), None)
        reload_fuel_tank = next((boost for boost in boosts if boost['id'] == 1), None)
        fuel_tank = next((boost for boost in boosts if boost['id'] == 2), None)
        turbo_charger = next((boost for boost in boosts if boost['id'] == 3), None)

        auto_driving_status = "Available" if auto_driving and not auto_driving['isLocked'] else "Unavailable"
        reload_fuel_tank_count = reload_fuel_tank['curStage'] if reload_fuel_tank else 0
        fuel_tank_level = fuel_tank['curStage'] if fuel_tank else 0
        fuel_tank_max = fuel_tank['totalStage'] if fuel_tank else 0
        turbo_charger_level = turbo_charger['curStage'] if turbo_charger else 0
        turbo_charger_max = turbo_charger['totalStage'] if turbo_charger else 0

        logger.info(
            f"{self.session_name} | Auto-driving: <e>{auto_driving_status}</e> | "
            f"Reload Fuel Tank: <e>{reload_fuel_tank_count}</e> | "
            f"Fuel Tank: <e>{fuel_tank_level}/{fuel_tank_max}</e> | "
            f"Turbo Charger: <e>{turbo_charger_level}/{turbo_charger_max}</e>")


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await OKX(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
