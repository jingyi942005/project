import random
import discord
import openai
from discord.ext import commands
import os

# 設定機器人的權限
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 設定 OpenAI API 金鑰
openai.api_key = '5fYbhQWQp6nZWpKF76OKRQLRycykW7oVJogrk8SyMkPr5prZ16swJQQJ99AKACfhMk5XJ3w3AAAAACOGRo7x'
openai.api_base = 'https://c1121-m3su23q5-swedencentral.cognitiveservices.azure.com/'
openai.api_type = "azure"
openai.api_version = "2024-08-01-preview"

DEPLOYMENT_NAME = "bot"

# Discord 機器人 Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# 問題庫和回應
questions = [
    {"question": "在戀愛中，最重要的是什麼?", "answers": ["信任", "誠實", "溝通", "愛"]},
    {"question": "你認為約會時，應該做什麼活動?", "answers": ["看電影", "吃晚餐", "去散步", "玩遊戲"]},
    {"question": "如果你和伴侶吵架了，會怎麼做?", "answers": ["冷靜下來", "找朋友傾訴", "與對方溝通", "暫時分開"]},
    {"question": "你覺得在戀愛中，最浪漫的事情是什麼?", "answers": ["一起旅行", "送花", "寫情書", "做手工禮物"]},
    {"question": "遠距離戀愛時，你最擔心的是什麼?", "answers": ["信任問題", "缺少陪伴", "溝通困難", "生活節奏不同"]},
    {"question": "如果你愛上了不該愛的人，你會怎麼辦?", "answers": ["放棄", "嘗試與對方在一起", "保持距離", "尋求朋友幫助"]},
    {"question": "你認為戀愛中的爭吵該如何處理?", "answers": ["冷靜下來再討論", "立刻道歉", "找第三方調解", "忽略爭執"]},
    {"question": "約會時最理想的時間長度是多久?", "answers": ["1-2小時", "3-4小時", "整個下午", "整個晚上"]},
    {"question": "你會願意與伴侶分享你的秘密嗎?", "answers": ["是", "不確定", "不會", "取決於對方"]},
    {"question": "如果你和伴侶的愛情出現危機，你會怎麼做?", "answers": ["溝通", "尋求外部幫助", "冷靜一下", "放手"]},
    {"question": "你覺得最好的約會地點是哪裡?", "answers": ["海邊", "咖啡館", "公園", "博物館"]},
    {"question": "如果你愛上一個很忙碌的人，你會怎麼做?", "answers": ["理解並支持", "自己也忙起來", "試著多見面", "尋求更多的關心"]},
    {"question": "如何知道對方是否愛你?", "answers": ["他會關心你的一切", "他會不斷努力維持關係", "他會尊重你的決定", "他會願意與你分享未來"]},
    {"question": "如果對方對你的戀愛方式不滿意，你會怎麼辦?", "answers": ["理解並改變", "討論並妥協", "不改變，堅持自己的方式", "放手讓他選擇"]},
    {"question": "在戀愛中，怎樣才能增進親密感?", "answers": ["多花時間相處", "分享更多感受", "共同做一些事情", "彼此支持"]},
    {"question": "如果你的伴侶遇到困難，你會怎麼做?", "answers": ["給予支持", "陪伴他度過難關", "幫助他找到解決辦法", "讓他自己解決"]},
    {"question": "你最喜歡和伴侶一起做的事情是?", "answers": ["旅行", "吃飯", "聊天", "運動"]},
    {"question": "你覺得戀愛中最困難的部分是?", "answers": ["保持信任", "維持激情", "處理衝突", "理解彼此"]},
]

responses = [
    "這是一個很好的選擇！",
    "這是一種非常健康的方式！",
    "這聽起來不錯，值得嘗試！",
    "真的是一個值得深思的選擇！",
]

# 全域變數控制是否啟用OpenAI回應
is_openai_enabled = True

# 分割長消息的函數
def split_message(message, chunk_size=2000):
    """將長消息分割為不超過 chunk_size 的片段"""
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]

# 當機器人啟動時觸發
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# 當機器人收到訊息時觸發
@bot.event
async def on_message(message):

    if message.content.startswith("!") or not is_openai_enabled:
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        return
    
    if message.author == bot.user:
        return

    user_input = message.content.strip()

    try:
        # 使用 OpenAI API 進行對話生成
        response = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,  # Azure 部署名稱
            messages=[{"role": "system", "content": "你是一個溫暖且有同理心的戀愛諮詢師，專注於幫助解決感情問題。"},
                      {"role": "user", "content": user_input}],
            max_tokens=500  # 可根據需要調整
        )

        bot_reply = response["choices"][0]["message"]["content"].strip()

        # 如果回應內容過長，分段回傳
        for chunk in split_message(bot_reply):
            await message.channel.send(chunk)

    except Exception as e:
        print(f"錯誤: {e}")
        await message.channel.send("抱歉，我暫時無法處理您的請求。")

    await bot.process_commands(message)

# 啟動戀愛遊戲的命令
@bot.command()
async def 戀愛遊戲(ctx):
    """啟動戀愛小遊戲"""
    global is_openai_enabled
    is_openai_enabled = False  # 禁用 OpenAI 回應
    
    await ctx.send("歡迎來到戀愛小遊戲！讓我們開始吧！")
    
    # 隨機抽取 10 題問題
    selected_questions = random.sample(questions, 10)
    
    score = 0
    for item in selected_questions:
        # 顯示問題及選項
        question = item["question"]
        options = "\n".join([f"{i + 1}. {answer}" for i, answer in enumerate(item["answers"])])
        question_message = f"{question}\n{options}"
        await ctx.send(question_message)
        
        # 等待用戶回答
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30)  # 等待30秒
            answer = msg.content.strip()
            
            # 檢查玩家選擇的答案是否在選項中
            try:
                answer_index = int(answer) - 1
                if 0 <= answer_index < len(item["answers"]):
                    correct_answer = item["answers"][answer_index]
                    score += 1
                    await ctx.send(random.choice(responses))
                else:
                    await ctx.send("這不是有效的選項，請重新選擇。")
            except ValueError:
                await ctx.send("請輸入一個有效的數字選項。")
        
        except Exception as e:
            await ctx.send("抱歉，時間過長，我們不能等待了！")
            break

    await ctx.send(f"遊戲結束！你總共得了 {score}/{len(selected_questions)} 分！")
    if score == len(selected_questions):
        await ctx.send("恭喜你！你是戀愛達人！")
    else:
        await ctx.send("不錯，繼續努力，成為戀愛高手！")
    
    is_openai_enabled = True  # 重新啟用 OpenAI 回應

# 啟動 Discord Bot
bot.run(DISCORD_TOKEN)