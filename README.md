![image](https://github.com/user-attachments/assets/21374ba7-ae76-4d06-827f-0d8a33299e3d)



## [Functionality](https://github.com/Fairmont77/OKX_Racer_bot/blob/main/bot/config/config.py)
| Functionality                                            | Supported |
|-------------------------------------------------------|:---------:|
| Unlimited number of accounts                          |     ✅     |
| Binding a proxy to a session                          |     ✅     |
| Auto-purchase of boosts                               |     ✅     |
| Random sleep time                                     |     ✅     |
| Random number of clicks per request                   |     ✅     |
| Support tdata / pyrogram .session / telethon .session |     ✅     |

## [⚙Settings](https://github.com/Fairmont77/OKX_Racer_bot/blob/main/.env-example)
| Settings                | Description                                                                |
|-------------------------|----------------------------------------------------------------------------|
| **API_ID / API_HASH**   | Platform data from which to launch a Telegram session (stock - Android)    |
| **SLEEP_TIME**          | Random amount of sleep time                                                |
| **AUTO_BOOST**          | Applies boost automatically if available (True / False)                    |
| **AUTO_TASK**           | Automatically performs tasks (True / False)                                |
| **PREDICTION**          | Predict price (0 - MOON, 1 - DOOM, 2 - random)                             |
| **BOOSTERS**            | Auto upgrade boosters  (True / False)                                      |
| **USE_PROXY_FROM_FILE** | Whether to use proxy from the `bot/config/proxies.txt` file (True / False) |

## Installation

## 📌Python
Before you begin, ensure you have the following installed:
- [Python](https://www.python.org/downloads/release/python-3119/) version 3.10 or 3.11

## 📃 Getting API Keys
1. Go to [my.telegram.org](https://my.telegram.org) and log in using your phone number.
2. Select **"API development tools"** and fill out the form to register a new application.
3. Note down the `API_ID` and `API_HASH` in `.env` file provided after registering your application.


## ⚡ Start

You can download [**Repository**](https://github.com/Fairmont77/OKX_Racer_bot.git) by cloning it to your system and installing the necessary dependencies:
```shell
~ >>> git clone https://github.com/Fairmont77/OKX_Racer_bot.git
~ >>> cd OKX_Racer_bot

#Linux
~/MemeFiBot >>> python3 -m venv venv
~/MemeFiBot >>> source venv/bin/activate
~/MemeFiBot >>> pip3.11 install -r requirements.txt
~/MemeFiBot >>> cp .env-example .env
~/MemeFiBot >>> nano .env # Here you must specify your API_ID and API_HASH , the rest is taken by default
~/MemeFiBot >>> python3.11 main.py

#Windows
~/MemeFiBot >>> python -m venv venv
~/MemeFiBot >>> venv\Scripts\activate
~/MemeFiBot >>> pip install -r requirements.txt
~/MemeFiBot >>> copy .env-example .env
~/MemeFiBot >>> # Specify your API_ID and API_HASH, the rest is taken by default
~/MemeFiBot >>> python main.py
```
