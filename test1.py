# 導入Discord.py模組
import discord
# 導入commands指令模組
from discord.ext import commands
import datetime
import os

# 設定機器人的權限
intents = discord.Intents.default()
intents.message_content = True

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# 使用commands.Bot來初始化機器人
bot = commands.Bot(command_prefix="/", intents=intents)

# 當機器人完成啟動
@bot.event
async def on_ready():
    print(f"目前登入身份 --> {bot.user}")

# 當頻道有新訊息
@bot.event
async def on_message(message):
    # 排除機器人本身的訊息，避免無限循環
    print(f"收到訊息: {message.content}")
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

    # 新訊息包含Hello，回覆Hello, world!
    if message.content == "Hello":
        await message.channel.send("Hello, world!")


# 輸入/Hello呼叫指令
@bot.command()
async def Hello(ctx):
    # 回覆Hello, world!
    await ctx.send("Hello, world!")

@bot.command()
async def 現在時間(ctx):
    # 獲取當前時間
    now = datetime.datetime.now()
    # 格式化時間
    time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
    # 回覆當前時間
    await ctx.send(f"現在時間是: {time_str}")

# 啟動機器人
bot.run("DISCORD_TOKEN")