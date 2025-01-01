import discord
import openai
from discord.ext import commands
import asyncio
import os

# 設定機器人的權限
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# 設定 OpenAI API 金鑰
openai.api_key = '5fYbhQWQp6nZWpKF76OKRQLRycykW7oVJogrk8SyMkPr5prZ16swJQQJ99AKACfhMk5XJ3w3AAAAACOGRo7x'
openai.api_base = 'https://c1121-m3su23q5-swedencentral.cognitiveservices.azure.com'
openai.api_type = "azure"
openai.api_version = "2024-08-01-preview"

DEPLOYMENT_NAME = "bot"

# Discord 機器人 Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# 當機器人啟動時觸發
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_input = message.content.strip()

    try:
        response = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,  # Azure 部署名稱
            messages=[
                {"role": "system", "content": "你是一個溫暖且有同理心的戀愛諮詢師，專注於幫助解決感情問題。"},
                {"role": "user", "content": user_input}
            ],
            max_tokens=500  # 可根據需要調整
        )
        print(f"OpenAI response: {response}")
        if 'choices' in response and len(response['choices']) > 0:
            bot_reply = response["choices"][0]["message"]["content"].strip()
            print(f"Bot reply: {bot_reply}")

            # 如果回應內容過長，分段回傳
            if len(bot_reply) > 2000:  # 這裡加入對長訊息的判斷
                for chunk in split_message(bot_reply):
                    print(f"Sending chunk: {chunk}")
                    await message.channel.send(chunk)
            else:
                await message.channel.send(bot_reply)

        else:
            await message.channel.send("抱歉，我無法處理您的請求，請稍後再試。")

    except openai.error.RateLimitError as e:
        print("超出令牌限制，稍後重試...")
        await asyncio.sleep(40)  
        await message.channel.send("請稍等一下，正在重試...")  # 可根據需要發送提示

    except Exception as e:
        print(f"錯誤: {e}")
        await message.channel.send("抱歉，我暫時無法處理您的請求。")

# 分割長消息的函數
def split_message(message, chunk_size=2000):
    """將長消息分割為不超過 chunk_size 的片段"""
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]
# 啟動 Discord Bot
bot.run(DISCORD_TOKEN)
