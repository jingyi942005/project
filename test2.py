import discord
from discord.ext import commands
from openai import AzureOpenAI
import requests
import os

# 設定機器人的權限
intents = discord.Intents.default()
intents.message_content = True

# Discord 機器人 Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# OpenAI API Key
endpoint = "https://test1029.openai.azure.com/"
model_name = "gpt-35-turbo"

# 初始化 Azure OpenAI 客戶端
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_version="2024-02-01",
    api_key=os.getenv("api_key")
)

# 使用 commands.Bot 來初始化機器人
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'機器人已登入為 {bot.user}')

@bot.command()
async def getdata(ctx):
    """獲取資料的命令"""
    print("接收到 /getdata 命令")
    try:
        # 從第三方 API 抓取資料
        response = requests.get("https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=CWA-31DEE846-5779-4C70-B266-EDB06792458D&locationName=%E9%AB%98%E9%9B%84%E5%B8%82")
        response.raise_for_status()  # 檢查請求是否成功
        data = response.json()  # 假設返回的資料是 JSON 格式
        print("API 返回數據:", data)  # 日誌輸出 API 返回的數據

        # 初始化 formatted_data
        formatted_data = ""

        if "records" in data and "location" in data["records"]:
            locations = data['records']['location']
            formatted_data = []

            for location in locations:
                location_name = location['locationName']
                weather_elements = location['weatherElement']

                for element in weather_elements:
                    element_name = element['elementName']
                    times = element['time']

                    for time in times:
                        start_time = time['startTime']
                        end_time = time['endTime']
                        parameter = time['parameter']
                        parameter_name = parameter['parameterName']
                        parameter_value = parameter.get('parameterValue', '')
                        parameter_unit = parameter.get('parameterUnit', '')

                        # 構建格式化的字符串
                        formatted_data.append(
                            f"{location_name} - {element_name} ({start_time} 至 {end_time}): {parameter_name} {parameter_value} {parameter_unit}"
                        )

            # 將格式化資料連接成一個大字符串
            processed_data = "\n".join(formatted_data)

            # 檢查資料長度，若超過4000字符則截斷
            if len(processed_data) > 4000:
                processed_data = processed_data[:4000] + '... (內容過長，已截斷)'

            # 將格式化資料發送到Discord
            await ctx.send(processed_data)

        else:
            await ctx.send("獲取的資料格式不正確，請稍後再試。")

    except requests.RequestException as req_err:
        await ctx.send("從 API 獲取資料時發生錯誤，請稍後再試。")
        print("API 請求錯誤:", req_err)
    except Exception as e:
        await ctx.send("發生未知錯誤，請稍後再試。")
        print("未知錯誤：", e)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f"收到消息: {message.content}")

    if message.content.lower() == "hi":
        await message.channel.send("Hello!")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)