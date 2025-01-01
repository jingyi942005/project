import random
import discord
import openai
from discord.ext import commands
from discord.ui import Select, View
import sqlite3
from datetime import datetime
import datetime
from collections import Counter
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

# 初始化資料庫
conn = sqlite3.connect('emotion_calendar.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS emotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        emotion TEXT,
        timestamp DATETIME
    )
''')
conn.commit()

# 重新排列情緒記錄 ID
def reorder_emotions(user_id):
    c.execute('SELECT id FROM emotions WHERE user_id = ? ORDER BY timestamp', (user_id,))
    records = c.fetchall()
    
    # 重新排序 ID
    for new_id, (old_id,) in enumerate(records, start=1):
        c.execute('UPDATE emotions SET id = ? WHERE id = ?', (new_id, old_id))
    conn.commit()

class EmotionSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="開心", value="開心"),
            discord.SelectOption(label="難過", value="難過"),
            discord.SelectOption(label="生氣", value="生氣"),
            discord.SelectOption(label="焦慮", value="焦慮"),
            discord.SelectOption(label="疲倦", value="疲倦"),
            discord.SelectOption(label="其他", value="其他"),
        ]
        super().__init__(placeholder="選擇你的情緒", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        emotion = self.values[0]
        if emotion == "其他":
            await interaction.response.send_message("請輸入你的情緒：")
            def check(msg):
                return msg.author == interaction.user and msg.channel == interaction.channel
            msg = await bot.wait_for('message', check=check)
            emotion = msg.content
        
        # 記錄情緒
        await self.record_emotion(interaction.user, emotion, interaction)

    async def record_emotion(self, user, emotion, interaction):
        user_id = str(user.id)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')  # 只保留小時和分鐘
        c.execute('INSERT INTO emotions (user_id, emotion, timestamp) VALUES (?, ?, ?)', (user_id, emotion, timestamp))
        conn.commit()

        # 重新排列 ID
        reorder_emotions(user_id)
        
        if not interaction.response.is_done():
            await interaction.response.send_message(f'情緒 "{emotion}" 已記錄於 {timestamp}！')
        else:
            await interaction.followup.send(f'情緒 "{emotion}" 已記錄於 {timestamp}！')

        # 重新啟用 OpenAI
        global is_openai_enabled
        is_openai_enabled = True

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

# OpenAI 聊天功能
@bot.event
async def on_message(message):
    # 檢查是否啟用聊天功能
    if not is_openai_enabled:
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
        return

    # 避免回應機器人本身的訊息
    if message.author == bot.user:
        return

    # 判斷是否為聊天指令
    if message.content.startswith("!聊天"):
        user_input = message.content.replace("!聊天", "").strip()  # 移除指令前綴，留下使用者輸入

        if not user_input:
            await message.channel.send("請輸入問題或內容，我可以幫助您解決感情相關問題！")
            return

        try:
            # 使用 OpenAI API 進行對話生成
            response = openai.ChatCompletion.create(
                engine=DEPLOYMENT_NAME,  # Azure 部署名稱
                messages=[
                    {"role": "system", "content": "你是一個溫暖且有同理心的戀愛諮詢師，專注於幫助解決感情問題。"},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=500  # 可根據需要調整
            )

            bot_reply = response["choices"][0]["message"]["content"].strip()

            # 如果回應內容過長，分段回傳
            for chunk in split_message(bot_reply):
                await message.channel.send(chunk)

        except Exception as e:
            print(f"錯誤: {e}")
            await message.channel.send("抱歉，我暫時無法處理您的請求。")

    # 處理其他指令
    await bot.process_commands(message)

# 分段訊息處理函數
def split_message(message, chunk_size=2000):
    """將長訊息分段，以免超出 Discord 單次訊息限制（2000 字符）"""
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]

# 啟動戀愛遊戲的命令
@bot.command(name="問答")
async def 戀愛遊戲(ctx):
    """啟動戀愛小遊戲"""
    global is_openai_enabled
    is_openai_enabled = False  # 禁用 OpenAI 回應
    
    await ctx.send("歡迎來到戀愛快問快答！讓我們開始吧！")
    await ctx.send("請輸入你要回答的題數(共有118題)")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    msg = await bot.wait_for('message', check=check, timeout=150)
    a = int(msg.content.strip())  # 將輸入的訊息轉換為整數
        
    # 隨機抽取問題
    selected_questions = random.sample(questions, a)
    await ctx.send(f"已選擇 {a} 題，開始遊戲！")
    
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
            msg = await bot.wait_for('message', check=check, timeout=20)  # 等待幾秒
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

# 記錄情緒
@bot.command()
async def 記錄情緒(ctx, emotion: str = None):
    global is_openai_enabled
    is_openai_enabled = False
    # 創建下拉選單並顯示
    select = EmotionSelect()
    view = View()
    view.add_item(select)
    await ctx.send("請選擇你的情緒：", view=view)

# 查看情緒日曆
@bot.command()
async def 查看情緒日曆(ctx):
    user_id = str(ctx.author.id)
    c.execute('SELECT id, emotion, timestamp FROM emotions WHERE user_id = ?', (user_id,))
    records = c.fetchall()
    if not records:
        await ctx.send("目前沒有任何情緒記錄！")
        return
    response = "你的情緒記錄如下：\n"
    for record in records:
        response += f"編號：{record[0]}，情緒：{record[1]}，時間：{record[2]}\n"

    await ctx.send(response)

# 刪除記錄
@bot.command()
async def 刪除記錄(ctx, *record_ids: int):
    if not record_ids:
        await ctx.send("請提供要刪除的記錄編號！例如：`!刪除記錄 1 2 3`")
        return

    user_id = str(ctx.author.id)
    deleted_count = 0

    for record_id in record_ids:
        c.execute('SELECT * FROM emotions WHERE id = ? AND user_id = ?', (record_id, user_id))
        record = c.fetchone()

        if record:
            c.execute('DELETE FROM emotions WHERE id = ?', (record_id,))
            deleted_count += 1

    # 重新排列編號
    if deleted_count > 0:
        c.execute('SELECT id FROM emotions WHERE user_id = ? ORDER BY timestamp', (user_id,))
        records = c.fetchall()

        # 依次更新記錄的 id
        for new_id, (old_id,) in enumerate(records, start=1):
            c.execute('UPDATE emotions SET id = ? WHERE id = ?', (new_id, old_id))

    conn.commit()

    if deleted_count == 0:
        await ctx.send("沒有找到符合條件的記錄或記錄不屬於你！")
    else:
        await ctx.send(f"已成功刪除 {deleted_count} 條情緒記錄！")

# 按週分析情緒
@bot.command()
async def 每週分析(ctx):
    user_id = str(ctx.author.id)
    today = datetime.datetime.now()
    start_of_week = today - datetime.timedelta(days=today.weekday())  # 本週週一
    end_of_week = start_of_week + datetime.timedelta(days=6)  # 本週週日

    # 將時間設置為一天的開始和結束
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)

    # 查詢本週情緒記錄
    c.execute('SELECT emotion FROM emotions WHERE user_id = ? AND timestamp BETWEEN ? AND ?', 
              (user_id, start_of_week, end_of_week))
    records = c.fetchall()

    if not records:
        await ctx.send("本週沒有記錄！")
        return

    # 統計情緒
    emotions = [record[0] for record in records]
    emotion_counts = Counter(emotions)
    summary = "\n".join([f"{emotion}: {count} 次" for emotion, count in emotion_counts.items()])

    await ctx.send(f"本週情緒分析：\n{summary}")

# 自定義區間分析情緒
@bot.command()
async def 分析區間(ctx, start_date: str, end_date: str):
    user_id = str(ctx.author.id)
    
    # 解析用戶輸入的日期
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        await ctx.send("日期格式錯誤，請使用 YYYY-MM-DD 格式。")
        return
    
    # 確保結束日期不早於開始日期
    if end_date < start_date:
        await ctx.send("結束日期不能早於開始日期。")
        return
    
    # 設置時間範圍
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # 查詢區間內的情緒記錄
    c.execute('SELECT emotion FROM emotions WHERE user_id = ? AND timestamp BETWEEN ? AND ?', 
              (user_id, start_date, end_date))
    records = c.fetchall()

    if not records:
        await ctx.send(f"{start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 之間沒有情緒記錄！")
        return

    # 統計情緒
    emotions = [record[0] for record in records]
    emotion_counts = Counter(emotions)
    summary = "\n".join([f"{emotion}: {count} 次" for emotion, count in emotion_counts.items()])

    await ctx.send(f"情緒分析（{start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}）：\n{summary}")

# 啟動 Discord Bot
bot.run(DISCORD_TOKEN)