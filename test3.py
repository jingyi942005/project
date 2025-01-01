from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageSendMessage
import os
import requests
from PIL import Image
import json
from openai import AzureOpenAI

app = Flask(__name__)

# LINE 频道访问令牌和密钥
LINE_CHANNEL_ACCESS_TOKEN = '6kzjaoBGNTAHp2PuD3cY7duVYuUpWKjF9G3whiM35QA/JChWfGjdfkHJAzwqtbwds0TX7yfP1vAt9s+iwhCMQtfY4M6F6s7xcwY/SHDxytOQIRGIfadyce/sl7WQtnFhwRa8nxeJaHgjjBp/Z2UjWwdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '3e9966afb77aff7b9504108e5d9aa79d'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 确保 'static' 目录存在
if not os.path.exists('static'):
    os.makedirs('static')

# Azure OpenAI 客户端配置
client = AzureOpenAI(
    api_version="2024-02-01",  
    api_key="5fYbhQWQp6nZWpKF76OKRQLRycykW7oVJogrk8SyMkPr5prZ16swJQQJ99AKACfhMk5XJ3w3AAAAACOGRo7x",  
    azure_endpoint="https://c1121-m3su23q5-swedencentral.cognitiveservices.azure.com/openai/deployments/darling/images/generations?api-version=2024-02-01"
)

@app.route("/callback", methods=['POST'])
def callback():
    # 获取 X-Line-Signature 头部值
    signature = request.headers['X-Line-Signature']

    # 获取请求体的文本
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 处理 webhook 内容
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_message = event.message.text  # 获取用户发送的文字

    # 调用生成图像的函数
    generated_image_path = generate_image(user_message)

    # 回复生成的图像
    image_message = ImageSendMessage(
        original_content_url=f"https://813a-115-165-205-73.ngrok-free.app/static/{generated_image_path}",
        preview_image_url=f"https://813a-115-165-205-73.ngrok-free.app/static/{generated_image_path}"
    )
    line_bot_api.reply_message(event.reply_token, image_message)

@app.route('/static/<filename>')
def serve_static(filename):
    # 提供 'static' 文件夹中的静态文件
    return send_from_directory('static', filename)

def generate_image(prompt):
    # 调用 DALL-E 生成图像
    result = client.images.generate(
        model="mydall-e",  # the name of your DALL-E 3 deployment
        prompt=prompt,  # the prompt for generating the image
        n=1
    )

    json_response = json.loads(result.model_dump_json())

    # 设置存储图像的路径
    image_dir = os.path.join(os.curdir, 'static')  # 保存到 static 目录

    # 如果目录不存在，创建它
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    # 初始化图像路径
    image_path = os.path.join(image_dir, 'generated_image.png')

    # 获取生成的图像 URL
    image_url = json_response["data"][0]["url"]
    generated_image = requests.get(image_url).content  # 下载图像

    # 将图像保存到本地
    with open(image_path, "wb") as image_file:
        image_file.write(generated_image)

    return 'generated_image.png'  # 返回保存的图像文件名

if __name__ == "__main__":
    app.run(debug=True)
