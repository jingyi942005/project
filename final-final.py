import random
import discord
import openai
from discord.ext import commands
from discord.ui import Select, View
from discord import app_commands
import aiomysql
from datetime import datetime
import datetime
from collections import Counter
import logging
import asyncio
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定機器人的權限
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 設定 OpenAI API 金鑰
openai.api_key = os.getenv("api_key")
openai.api_base = 'https://discordbot.openai.azure.com/'
openai.api_type = "azure"
openai.api_version = "2024-05-01-preview"

DEPLOYMENT_NAME = "bot"

# Discord 機器人 Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# 分段訊息處理函數
def split_message(message, chunk_size=2000):
    """將長訊息分段，以免超出 Discord 單次訊息限制(2000 字符)"""
    if len(message) <= chunk_size: # 如果訊息長度小於等於 2000 字符，直接返回
        return [message]
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)] # 分段


# 連接到 MySQL 資料庫
async def get_db_pool():
    return await aiomysql.create_pool(
        host="localhost",  # MySQL 主機地址
        port=3306,         # MySQL 埠
        user="root",       # MySQL 使用者名稱
        password="",  # MySQL 密碼
        db="emotion_database",   # 資料庫名稱
        autocommit=True,
    )

# 初始化資料庫
async def init_db():
    pool = await get_db_pool()
    # 使用 async with 獲取資料庫連線
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 執行建立表格的 SQL 指令
            await cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS emotions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    emotion VARCHAR(255),
                    timestamp DATETIME
                )
            ''')

# 分段發送訊息
async def send_long_message(interaction, content):
    messages = split_message(content)
    for msg in messages:
        if not interaction.response.is_done():
            await interaction.response.send_message(msg)
        else:
            await interaction.followup.send(msg)

# 分割長訊息
def split_message(content, limit=2000):
    return [content[i:i+limit] for i in range(0, len(content), limit)]

# 負面情緒關懷訊息
def get_caring_message(negative_count, total_count):
    if negative_count > total_count / 2:
        caring_messages = [
            "最近是不是有點累了？記得好好休息哦！:smiling_face_with_3_hearts:",
            "一切都會好起來的，有什麼需要幫助的可以告訴我！:smile:",
            "即使生活有時很難，也不要忘了照顧自己！:hugging:",
            "試著找些讓自己開心的事情做吧！:blush:"
        ]
        return random.choice(caring_messages)
    return None

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
    {"question": "你認為什麼最能增強伴侶間的親密感?", "answers": ["更多相處時間", "分享內心想法", "共同經歷挑戰", "支持彼此的目標"]},
    {"question": "你覺得什麼情況下最能激發激情?", "answers": ["製造浪漫驚喜", "旅行中的冒險", "情感的坦露", "長時間的分別後重逢"]},
    {"question": "你認為什麼樣的行為能夠展現承諾?", "answers": ["公開表達愛意", "為對方做長期規劃", "堅持陪伴", "尊重對方的選擇"]},
    {"question": "如果親密感減少，你會怎麼辦?", "answers": ["增加相處時間", "坦誠討論問題", "製造更多共同經歷", "重新定義關係目標"]},
    {"question": "你認為愛情中最能保持激情的是什麼?", "answers": ["嘗試新鮮事物", "不斷製造驚喜", "彼此保持吸引力", "營造浪漫氛圍"]},
    {"question": "你認為承諾的基石是什麼?", "answers": ["忠誠", "信任", "共同的未來願景", "無條件的支持"]},
    {"question": "你覺得激情消退後，愛情是否能維持?", "answers": ["可以，只要有親密和承諾", "需要重新尋找激情", "不一定", "取決於雙方的努力"]},
    {"question": "你認為什麼樣的活動最能增進親密感?", "answers": ["深入的談話", "一起完成目標", "製造專屬回憶", "共度輕鬆時光"]},
    {"question": "當對方對承諾猶豫時，你會怎麼做?", "answers": ["給對方時間", "坦誠面對問題", "確認彼此需求", "重新評估關係"]},
    {"question": "你覺得激情在愛情中是否必要?", "answers": ["非常必要", "有時候必要", "不是必需的", "可以被其他因素取代"]},
    {"question": "當承諾受到挑戰時，你會怎麼應對?", "answers": ["堅守自己的決定", "與伴侶溝通", "重新考慮關係", "尋求外部幫助"]},
    {"question": "你覺得親密感應該如何持續增強?", "answers": ["分享內心感受", "學習對方的興趣", "尊重並理解彼此", "多創造共同經歷"]},
    {"question": "在愛情中，什麼最能象徵激情?", "answers": ["熱烈的擁抱", "深情的眼神", "驚喜的告白", "旅行中的刺激"]},
    {"question": "你認為承諾應該如何表現出來?", "answers": ["規劃未來", "遵守約定", "對彼此忠誠", "願意為對方犧牲"]},
    {"question": "你覺得當親密感減弱時，如何改善?", "answers": ["更多溝通", "製造浪漫時刻", "尋找共同興趣", "花更多時間陪伴"]},
    {"question": "激情是否會隨時間減弱?", "answers": ["是的，但可以努力保持", "不一定", "完全取決於雙方", "需要特意維護"]},
    {"question": "你覺得承諾能否彌補親密和激情的不足?", "answers": ["能", "不能", "部分能", "取決於情況"]},
    {"question": "如果對方表達對激情的需求，你會怎麼回應?", "answers": ["努力創造激情", "與對方溝通需求", "專注於親密感", "尋求平衡"]},
    {"question": "你認為什麼行為會損害承諾?", "answers": ["欺騙", "冷漠", "不尊重", "忽視對方的感受"]},
    {"question": "愛情中，你認為親密、激情和承諾哪個最重要?", "answers": ["親密", "激情", "承諾", "三者同樣重要"]},
    {"question": "當伴侶不回訊息時，你的第一反應是什麼?", "answers": ["感到被忽視", "耐心等待", "假裝不在意", "覺得很受傷"]},
    {"question": "你覺得在關係中最重要的是什麼?", "answers": ["穩定和安全", "得到更多關注", "保有自由和距離", "理解彼此的行為"]},
    {"question": "如果你和伴侶分開幾天，你會有什麼感受?", "answers": ["感到平靜", "開始擔心對方的態度", "覺得輕鬆", "有點混亂和不安"]},
    {"question": "當伴侶表現冷漠時，你會怎麼反應?", "answers": ["試著溝通", "更加黏著對方", "選擇保持距離", "感到情緒崩潰"]},
    {"question": "你認為伴侶的關注應該占多大的比重?", "answers": ["剛剛好，彼此平衡", "越多越好", "不需要太多", "很難確定"]},
    {"question": "當伴侶過於親密時，你的感覺是什麼?", "answers": ["很開心", "希望對方更親密", "有點不舒服", "既期待又害怕"]},
    {"question": "如果伴侶提出需要更多空間，你會怎麼做?", "answers": ["理解並尊重", "感到不安並尋求更多關注", "感到鬆了一口氣", "不知道該怎麼處理"]},
    {"question": "你如何看待承諾在關係中的作用?", "answers": ["必要且穩固", "需要不斷被肯定", "可以選擇性承諾", "讓人感到矛盾"]},
    {"question": "當你覺得伴侶忽略你時，你的應對方式是什麼?", "answers": ["表達你的感受", "更加努力引起注意", "假裝不在乎", "變得更冷漠"]},
    {"question": "你覺得什麼樣的行為能增強關係的安全感?", "answers": ["穩定的溝通", "更多的陪伴", "給予對方自由", "建立清晰的界限"]},
    {"question": "你認為過度親密的關係會帶來什麼影響?", "answers": ["促進感情發展", "讓人感到不安", "感到壓力很大", "情緒變得複雜"]},
    {"question": "當伴侶不願分享他的想法時，你會怎麼反應?", "answers": ["試著詢問原因", "擔心關係是否出問題", "給予對方時間和空間", "感到被拒絕和受傷"]},
    {"question": "你認為在親密關係中，保持獨立的重要性是什麼?", "answers": ["適度獨立有助於關係穩定", "覺得獨立會疏遠彼此", "非常重要，避免過度依賴", "獨立和親密讓人難以抉擇"]},
    {"question": "當伴侶有壓力時，你會怎麼支持他?", "answers": ["提供情感支持", "持續關注他的一切", "保持距離以免干擾", "試圖找機會解決他的問題"]},
    {"question": "你如何看待『分開一段時間對感情是否有益』?", "answers": ["可以增強彼此的信任", "會讓人感到焦慮", "能幫助彼此更冷靜", "感到矛盾和不安"]},
    {"question": "當你需要安慰時，你會希望伴侶怎麼做?", "answers": ["主動陪伴", "表達愛意和支持", "給我一點時間", "讓我自己處理情緒"]},
    {"question": "你如何表達對伴侶的關愛?", "answers": ["通過細心照顧對方", "持續表達對他的依賴", "尊重他的個人空間", "不時給予驚喜和承諾"]},
    {"question": "你認為逃避型人格在戀愛中最大的挑戰是什麼?", "answers": ["建立親密關係", "接受伴侶的關注", "維持獨立性", "理解自己的情感需求"]},
    {"question": "你覺得什麼情況最能破壞一段關係?", "answers": ["信任的缺失", "安全感的不足", "過度親密或疏遠", "反覆無常的行為"]},
    {"question": "你認為愛情中最重要的平衡是什麼?", "answers": ["親密與獨立", "激情與理性", "承諾與自由", "安全感與挑戰"]},
    {"question": "當你和伴侶約會時，你更傾向於做什麼？", "answers": ["和他一起參加聚會", "在家安靜地聊天", "計劃一個冒險旅行", "嘗試他喜歡的活動"]},
    {"question": "如果伴侶忘記了一個重要的紀念日，你會如何反應？","answers": ["理性地和他討論這件事", "感到受傷想要他的道歉", "忽略這件事", "期待未來不會再發生"]},
    {"question": "你認為愛情中最重要的特質是什麼？","answers": ["彼此分享生活的細節", "共同制定未來計劃", "維持穩定的情感連結", "解決問題的能力"]},
    {"question": "你如何處理與伴侶的分歧？","answers": ["以冷靜的方式進行討論", "優先考慮對方的感受", "尋求靈活解決方法", "設定規則避免未來重複"]},
    {"question": "當伴侶需要空間時，你會怎麼做？","answers": ["給予他足夠的空間", "試圖找時間和他溝通", "耐心等待，專注自己", "不斷想著他是否不愛我了"]},
    {"question": "你認為如何讓一段感情保持激情？","answers": ["計劃浪漫的驚喜", "嘗試新的約會活動", "經常交流彼此的需求", "保持個人空間以增加吸引力"]},
    {"question": "如果你需要對一段感情做出長期承諾，你會怎麼考慮？","answers": ["制定一個穩定的未來計劃", "觀察彼此是否有共同的價值觀", "根據直覺和感覺做決定", "考慮如何平衡自己的自由和關係"]},
    {"question": "你最擅長表達愛意的方式是什麼？", "answers": ["行動上支持對方", "浪漫的語言表達", "策劃驚喜或旅行", "細心留意對方的需求"]},
    {"question": "當你和伴侶發生爭執時，最可能的原因是什麼？", "answers": ["對未來計劃的不同看法","對某件事處理方式的分歧", "缺乏足夠的陪伴", "過於注重個人空間"]},
    {"question": "你最理想的伴侶類型是什麼樣的？","answers": ["能與我討論深層問題的", "願意尊重我的自由的", "能和我分享生活小事的", "總能在情緒上支持我的"]},
    {"question": "如果伴侶生日快到了，你會怎麼做？","answers": ["提前準備驚喜派對","買個實用的禮物","手寫一封感人的信","只是口頭說生日快樂"]},
    {"question": "如果伴侶不開心，你會怎麼安慰他/她？","answers": ["帶他/她去吃好吃的","陪他/她靜靜地待著","直接問清楚問題所在","給對方空間自己處理"]},
    {"question": "你們約會時，對方遲到了半小時，會怎麼反應？","answers": ["開玩笑調侃對方","表示理解，但心裡有點不高興","當面生氣批評","乾脆自己離開"]},
    {"question": "當伴侶和異性朋友單獨出去，你的感覺是？","answers": ["完全信任，沒問題","心裡會有點不安","要求報備細節","嚴格禁止"]},
    {"question": "如果伴侶沒主動回覆你的訊息，你會怎麼想？","answers": ["對方可能很忙","開始懷疑他/她的行蹤","覺得他/她可能對你冷淡了","無所謂，回就回，不回就算了"]},
    {"question": "在戀愛中，你認為最重要的是？","answers": ["相互信任","物質基礎","共同興趣","外貌吸引"]},
    {"question": "如果要挑選結婚對象，首要條件是？","answers": ["感情穩定","經濟實力","家庭背景","外在條件"]},
    {"question": "當伴侶遇到困難時，你會？","answers": ["全力支持","提供實際建議","看對方需要什麼再行動","只在必要時幫忙"]},
    {"question": "你認為戀愛中的爭吵應該如何處理？","answers": ["當下解決","冷靜一段時間再溝通","一方妥協","覺得爭吵是沒必要的"]},
    {"question": "你覺得愛情的最佳狀態是什麼？","answers": ["激情四溢","平淡而穩定","每天都有新鮮感","雙方獨立但互相關心"]},
    {"question": "如果你發現伴侶有不可告人的秘密，你會？","answers": ["當面質問","慢慢試探真相","假裝不知道","直接分手"]},
    {"question": "如果伴侶提出短暫分開冷靜一下，你會？","answers": ["完全接受並支持","試圖挽留","覺得這是分手的徵兆","不同意，要求面對面解決"]},
    {"question": "如果對方要求你放棄某個愛好，你會？","answers": ["為了他/她放棄","嘗試妥協","堅持自己的選擇","覺得這段關係有問題"]},
    {"question": "如果你的家人不喜歡你的伴侶，你會怎麼辦？","answers": ["說服家人接受","慢慢觀察再決定","順從家人意見","完全不理會家人的看法"]},
    {"question": "當伴侶有嚴重缺點時，你會？","answers": ["試著幫他/她改變","包容並接受","暗中觀察是否影響感情","無法忍受，直接分手"]},
    {"question": "如果可以安排一次約會，你會選擇？","answers": ["看一場電影","去主題樂園","一起做飯","靜靜地看書或聽音樂"]},
    {"question": "你們在一起時，最喜歡做的事情是？","answers": ["一起吃東西","聊天分享生活","出去旅行","玩遊戲或看影集"]},
    {"question": "在戀愛中，你覺得自己的角色比較像？","answers": ["照顧者","被照顧者","平等夥伴","領導者"]},
    {"question": "如果和伴侶一起養寵物，你希望養什麼？","answers": ["狗","貓","魚或爬蟲類","其他"]},
    {"question": "如果你們要一起開車旅行，你會選擇哪條路線？","answers": ["海邊公路","山區小道","大城市觀光","鄉村風光"]},
    {"question": "如果伴侶在社群媒體上跟異性互動頻繁，你會？","answers": ["覺得無所謂","私下表達自己的不安","要求減少這種互動","直接質問對方"]},
    {"question": "當伴侶的朋友對你態度不好時，你會？","answers": ["跟伴侶反映情況","嘗試和朋友和解","選擇忍耐","希望伴侶減少與這些朋友的來往"]},
    {"question": "伴侶因為工作繁忙忘記重要紀念日，你會？","answers": ["表示理解，自己處理","提醒他/她注意這類事情","感到不被重視並生氣","當天不提，但記在心裡"]},
    {"question": "如果你發現伴侶有輕微說謊習慣，但不是重大事情，你會？","answers": ["完全包容","跟對方好好談談","嚴肅對待，要求改正","逐漸對這段感情失去信心"]},
    {"question": "如果你的伴侶被前任聯絡，你會怎麼看待？","answers": ["覺得很正常","要求伴侶保持距離","內心不安但不表現出來","完全無法接受"]},
    {"question": "如果你的伴侶提出兩人一起學習新技能，你會選擇什麼？","answers": ["學做料理","一起運動健身","學習一門新語言","學習音樂或舞蹈"]},
    {"question": "當伴侶在公開場合對你表現冷淡時，你會？","answers": ["當場詢問原因","回家後再討論","裝作不在意","覺得很受傷"]},
    {"question": "如果你的伴侶忽然計畫改變未來生活方向，你會？","answers": ["全力支持","試著說服他/她改變主意","一起探討可能性","覺得對方太自私"]},
    {"question": "在戀愛中，你更希望伴侶給你什麼樣的支持？","answers": ["精神上的鼓勵","實際行動的幫助","情緒上的安慰","彼此獨立但信任"]},
    {"question": "你對公開展示親密行為的看法是？","answers": ["自然隨意","能接受但不多","不喜歡","完全不能接受"]},
    {"question": "如果伴侶突然想搬到另一個城市生活，你會？","answers": ["毫不猶豫跟隨","一起討論是否適合","希望他/她放棄","考慮分手"]},
    {"question": "如果伴侶開始對某件事情特別著迷，你會？","answers": ["一起參與其中","表示支持但不參與","嘗試讓他/她分散注意","感到疏遠"]},
    {"question": "你對婚姻的態度是什麼？","answers": ["非常期待","可以考慮，但不急","可有可無","完全不考慮"]},
    {"question": "如果伴侶在外遇到麻煩，你會？","answers": ["立刻趕去幫忙","提供建議但不親自參與","讓他/她自己解決","視情況而定"]},
    {"question": "如果你的伴侶有經濟困難，你會？","answers": ["主動提供財務幫助","幫助他/她規劃財務","情感上支持，但不提供金錢","建議他/她尋求其他方法"]},
    {"question": "你更喜歡與伴侶一起去哪種旅行？","answers": ["豪華度假村","背包客自助旅行","文化探索之旅","短途休閒旅行"]},
    {"question": "當伴侶提出結束關係時，你會？","answers": ["嘗試挽回","希望對方解釋原因","接受並祝福對方","立刻切斷所有聯繫"]},
    {"question": "如果伴侶經常和朋友聚會，你會？","answers": ["完全支持","希望他/她分出更多時間陪你","覺得他/她忽略了你","逐漸疏遠對方"]},
    {"question": "你認為兩人相處時，最好的溝通方式是？","answers": ["直接表達心情","循序漸進溝通","先觀察對方的態度","避免談論敏感話題"]},
    {"question": "你希望伴侶對你的朋友表現如何？","answers": ["熱情主動","適度友好","禮貌但保持距離","完全不需要互動"]},
    {"question": "如果伴侶的某些行為讓你不滿，你會？","answers": ["直接告訴他/她","觀察一段時間再說","不提但心裡記住","默默改變自己的態度"]},
    {"question": "你希望與伴侶過哪種節日慶祝方式？","answers": ["大型聚會","安靜的兩人時光","與家人朋友一起慶祝","不需要特別慶祝"]},
    {"question": "當伴侶工作壓力很大時，你會？","answers": ["幫他/她分擔一些事情","鼓勵對方調整狀態","建議他/她休假","陪伴但不干涉"]},
    {"question": "如果伴侶對你的外表提出建議，你會？","answers": ["欣然接受並改變","接受但有選擇性調整","覺得被冒犯","直接拒絕"]},
    {"question": "當你們意見不合時，通常會怎麼處理？","answers": ["冷靜溝通找到折衷方案","暫時擱置，稍後再討論","一方讓步","選擇忽略問題"]},
    {"question": "如果伴侶要求你嘗試一些新事物，但你不喜歡，你會？","answers": ["嘗試但告知對方感受","婉拒並解釋原因","強迫自己接受","直接拒絕"]},
    {"question": "當你感到壓力時，希望伴侶怎麼做？","answers": ["主動安慰","幫忙解決問題","靜靜陪伴","讓我自己處理"]},
    {"question": "當你與伴侶的朋友或家人相處不愉快時，你會？","answers": ["試著改善關係","請伴侶調停","選擇少接觸","直接向伴侶表達不滿"]},
    {"question": "你認為理想的戀愛時長是多久？","answers": ["一年以內","兩到三年","五年以上","沒有期限，順其自然"]},
    {"question": "如果你的伴侶開始對你冷淡，你會？","answers": ["積極溝通尋找原因","給予空間和時間","嘗試用行動挽回","認為感情已經結束"]}
]

responses = [
    "這是一個很好的選擇！",
    "這是一種非常健康的方式！",
    "這聽起來不錯，值得嘗試！",
    "真的是一個值得深思的選擇！",
]


# 分割長消息的函數
def split_message(message, chunk_size=2000):
    """將長消息分割為不超過 chunk_size 的片段"""
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]

# 當機器人啟動時觸發
@bot.event
async def on_ready():
    slash = await bot.tree.sync()
    try:
        await bot.tree.sync()  # 將斜線指令同步到 Discord
        print(f"已登入為 {bot.user} 並同步{len(slash)}個斜線指令。")
    except Exception as e:
        print(f"同步斜線指令時發生錯誤：{e}")

# OpenAI 聊天功能
@bot.tree.command(name="聊天", description="openai聊天功能")
@app_commands.describe(prompt="輸入您的問題或內容")
async def chat(interaction: discord.Interaction, prompt: str):
    """處理聊天功能的斜線指令"""
    if not prompt.strip():
        await interaction.response.send_message("請輸入有效的內容，我可以幫助您解決感情相關問題！", ephemeral=True)
        return
    
    await interaction.response.defer()  # 延遲回應

    try:
        # 使用 OpenAI API 生成回應
        response = openai.ChatCompletion.create(
            engine='gpt-4o',  # Azure 部署名稱
            messages=[
                {"role": "system", "content": "你是一個溫暖且有同理心的戀愛諮詢師，專注於幫助解決感情問題。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500  # 可根據需要調整
        )

        response_text = response["choices"][0]["message"]["content"].strip()

        # 如果回應內容過長，分段回傳
        for chunk in split_message(response_text):
            await interaction.followup.send(chunk)

    except openai.error.RateLimitError:
        logger.error("超過 API 配額限制")
        await interaction.followup.send("抱歉，目前請求量過多，請稍後再試。")
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI 錯誤: {e}")
        await interaction.followup.send("抱歉，我暫時無法處理您的請求。")
    except Exception as e:
        logger.exception("未知錯誤")
        await interaction.followup.send("發生未知錯誤，請稍後再試。")


# 啟動戀愛遊戲的命令
@bot.tree.command(name="問答", description="戀愛快問快答")
async def 戀愛遊戲(interaction: discord.Interaction):
    """啟動戀愛小遊戲"""
    
    await interaction.response.send_message("歡迎來到戀愛快問快答！讓我們開始吧！請輸入你要回答的題數(共有118題)")


    def check(msg):
        return msg.author == interaction.user and msg.channel == interaction.channel
    
    max_attempts = 3  # 最大嘗試次數
    attempts = 0

    while attempts < max_attempts:
        try:
            # 等待用戶輸入題數
            msg = await bot.wait_for('message', check=check, timeout=150)
            a = int(msg.content.strip())

            # 檢查題數是否有效
            if 1 <= a <= len(questions):
                break  # 輸入正確，跳出循環
            else:
                await interaction.followup.send(f"題數必須在 1 到 {len(questions)} 之間，請重新輸入！")
        except asyncio.TimeoutError:
            await interaction.followup.send("超時未回應，遊戲結束！")
            return
        except ValueError:
            await interaction.followup.send("請輸入有效的數字！")

        attempts += 1

    if attempts == max_attempts:
        await interaction.followup.send("嘗試次數過多，遊戲結束！")
        return
        
    # 隨機抽取問題
    selected_questions = random.sample(questions, a)
    await interaction.followup.send(f"已選擇 {a} 題，開始遊戲！")
    
    score = 0
    for item in selected_questions:
        # 顯示問題及選項
        question = item["question"]
        options = "\n".join([f"{i + 1}. {answer}" for i, answer in enumerate(item["answers"])])
        question_message = f"{question}\n{options}"
        await interaction.followup.send(question_message)
        
        # 等待用戶回答
        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=20)  # 等待幾秒
            answer = msg.content.strip()
            
            # 檢查玩家選擇的答案是否在選項中
            try:
                answer_index = int(answer) - 1
                if 0 <= answer_index < len(item["answers"]):
                    correct_answer = item["answers"][answer_index]
                    score += 1
                    await interaction.followup.send(random.choice(responses))
                else:
                    await interaction.followup.send("這不是有效的選項，請重新選擇。")
            except ValueError:
                await interaction.followup.send("請輸入一個有效的數字選項。")
        
        except Exception as e:
            await interaction.followup.send("抱歉，時間過長，我們不能等待了！")
            break

    await interaction.followup.send(f"遊戲結束！你總共得了 {score}/{len(selected_questions)} 分！")
    if score == len(selected_questions):
        await interaction.followup.send("恭喜你！你是戀愛達人！")
    else:
        await interaction.followup.send("不錯，繼續努力，成為戀愛高手！")
    

# 記錄情緒
@bot.tree.command(name="記錄情緒", description="記錄情緒")
async def 記錄情緒(interaction: discord.Interaction):
    class EmotionSelect(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="開心", value="開心"),
                discord.SelectOption(label="幸福", value="幸福"),
                discord.SelectOption(label="興奮", value="興奮"),
                discord.SelectOption(label="期待", value="期待"),
                discord.SelectOption(label="難過", value="難過"),
                discord.SelectOption(label="生氣", value="生氣"),
                discord.SelectOption(label="焦慮", value="焦慮"),
                discord.SelectOption(label="疲倦", value="疲倦"),
                discord.SelectOption(label="其他", value="其他")
            ]
            super().__init__(placeholder="選擇你的情緒", options=options)

        async def callback(self, interaction: discord.Interaction):
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        'INSERT INTO emotions (user_id, emotion, timestamp) VALUES (%s, %s, %s)',
                        (str(interaction.user.id), self.values[0], datetime.datetime.now())
                    )
            await interaction.response.send_message(f"已記錄你的情緒：{self.values[0]}！", ephemeral=True)

    view = View()
    view.add_item(EmotionSelect())
    await interaction.response.send_message("請選擇你的情緒：", view=view)

# 查看情緒日曆
@bot.tree.command(name="查看情緒日曆", description="查看情緒日曆")
async def 查看情緒日曆(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    pool=await get_db_pool()
    async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT id, emotion, timestamp FROM emotions WHERE user_id = %s', (user_id,))
                records = await cursor.fetchall()
    if not records:
        await interaction.response.send_message("目前沒有任何情緒記錄！")
        return
    response = "你的情緒記錄如下：\n"
    for record in records:
        timestamp = record[2]
        formatted_time = timestamp.strftime('%Y-%m-%d %H:%M')
        response += f"編號：{record[0]}，情緒：{record[1]}，時間：{formatted_time}\n"
    await send_long_message(interaction, response)

# 刪除記錄
@bot.tree.command(name="刪除記錄", description="刪除指定的記錄")
@app_commands.describe(record_ids="要刪除的記錄編號，以空格分隔，例如:1 2 3")
async def 刪除記錄(interaction: discord.Interaction, record_ids: str):
    try:
        record_ids_list = [int(id.strip()) for id in record_ids.split() if id.strip().isdigit()]
        if not record_ids_list:
            await interaction.response.send_message("請提供有效的記錄編號！", ephemeral=True)
            return
        user_id = str(interaction.user.id)
        pool=await get_db_pool()
        async with pool.acquire() as conn:
                deleted_count = 0
                for record_id in record_ids_list:
                    async with conn.cursor() as cursor:
                        await cursor.execute('DELETE FROM emotions WHERE id = %s AND user_id = %s', (record_id, user_id))
                        deleted_count += 1
                if deleted_count == 0:
                    await interaction.response.send_message("沒有找到符合條件的記錄！")
                else:
                    await interaction.response.send_message(f"已成功刪除 {deleted_count} 條情緒記錄！")
                await conn.commit()
    except Exception as e:
        await interaction.response.send_message("刪除記錄時發生錯誤，請稍後再試！", ephemeral=True)
        print(f"錯誤: {e}")

# 按週分析情緒
@bot.tree.command(name="每週分析", description="顯示本週的情緒記錄")
async def 每週分析(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    today = datetime.datetime.now()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    pool=await get_db_pool()
    async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT emotion FROM emotions WHERE user_id = %s AND timestamp BETWEEN %s AND %s', 
                                     (user_id, start_of_week, end_of_week))
                records = await cursor.fetchall()
    if not records:
        await interaction.response.send_message("本週沒有記錄！")
        return
    emotions = [record[0] for record in records]
    emotion_counts = Counter(emotions)
    total_emotions = sum(emotion_counts.values())
    negative_emotions = sum(emotion_counts[emotion] for emotion in emotion_counts if emotion in ["悲傷", "憤怒", "焦慮", "疲倦", "生氣", "難過", "EMO", "憂鬱", "擔心", "煩惱", "煩躁", "煩悶", "苦惱", "煩憂", "無聊"])
    summary = "\n".join([f"{emotion}: {count} 次" for emotion, count in emotion_counts.items()])
    caring_message = get_caring_message(negative_emotions, total_emotions)
    response_message = f"本週情緒分析：\n{summary}"
    if caring_message:
        response_message += f"\n\n💡 {caring_message}"
    await interaction.response.send_message(response_message)

# 自定義區間分析情緒
@bot.tree.command(name="分析區間", description="顯示區間內的情緒記錄")
@app_commands.describe(start_date="開始日期(格式:YYYY-MM-DD)", end_date="結束日期(格式:YYYY-MM-DD)")
async def 分析區間(interaction: discord.Interaction, start_date: str, end_date: str):
    user_id = str(interaction.user.id)

    # 解析用戶輸入的日期
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        await interaction.response.send_message("日期格式錯誤，請使用 YYYY-MM-DD 格式。")
        return

    # 確保結束日期不早於開始日期
    if end_date < start_date:
        await interaction.response.send_message("結束日期不能早於開始日期。")
        return

    # 設置時間範圍
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # 查詢資料庫區間內的情緒記錄
    pool=await get_db_pool()
    async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    'SELECT emotion FROM emotions WHERE user_id = %s AND timestamp BETWEEN %s AND %s',
                    (user_id, start_date, end_date)
                )
                records = await cursor.fetchall()

    if not records:
        await interaction.response.send_message(f"{start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 之間沒有情緒記錄！")
        return

    # 統計情緒
    emotions = [record[0] for record in records]
    emotion_counts = Counter(emotions)
    total_emotions = sum(emotion_counts.values())
    negative_emotions = sum(
        emotion_counts[emotion] for emotion in emotion_counts
        if emotion in ["悲傷", "憤怒", "焦慮", "疲倦", "生氣", "難過", "EMO", "憂鬱", "擔心", "煩惱", "煩躁", "煩悶", "苦惱", "煩憂", "無聊"]
    )
    summary = "\n".join([f"{emotion}: {count} 次" for emotion, count in emotion_counts.items()])
    caring_message = get_caring_message(negative_emotions, total_emotions)


    # 構造回應訊息
    response_message = f"情緒分析 ({start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}):\n{summary}"
    if caring_message:
        response_message += f"\n\n💡 {caring_message}"

    await interaction.response.send_message(response_message)

# 啟動 Discord Bot
bot.run(DISCORD_TOKEN)