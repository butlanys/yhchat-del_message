import os
import json
import requests
from flask import Flask, request, jsonify
import zxing
from threading import Thread
import base64
import re
from dotenv import load_dotenv

load_dotenv()

id_1 = os.getenv("ID_1")  # 敏感词的表单id
id_2 = os.getenv("ID_2")  # 群主的用户id的表单id
id_3 = os.getenv("ID_3")  # 群名称的表单id
id_4 = os.getenv("ID_4")  # 图片二维码识别开关的表单id
id_5 = os.getenv("ID_5")  # 违规网址链接的表单id
id_6 = os.getenv("ID_6")  # 撤回后的提示消息的表单id
id_7 = os.getenv("ID_7")  # 使用管理员权限撤回开关的表单id
id_8 = os.getenv("ID_8")  # 撤回所有带二维码的图片
id_9 = os.getenv("ID_9")  # 白名单表单id
id_10 = os.getenv("ID_10")  # 黑名单表单id

TOKEN = os.getenv("TOKEN")  # 可在官网后台获取
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # 管理员token

app = Flask(__name__)
data_path = 'data.json'
tmp_dir = 'tmp'

if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)

def yhchat_push(recvId, recvType, contentType, content):
    url = f"https://chat-go.jwzhd.com/open-apis/v1/bot/send?token={TOKEN}"
    payload = json.dumps({
        "recvId": recvId,
        "recvType": recvType,
        "contentType": contentType,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)

def yhchat_batch_push(recvIds, recvType, contentType, content):
    url = f"https://chat-go.jwzhd.com/open-apis/v1/bot/batch_send?token={TOKEN}"
    payload = json.dumps({
        "recvIds": recvIds,
        "recvType": recvType,
        "contentType": contentType,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)


def del_message(msgId, chatId):
    url = f"https://chat-go.jwzhd.com/open-apis/v1/bot/recall?token={TOKEN}"
    payload = json.dumps({
        "msgId": msgId,
        "chatId": chatId,
        "chatType": "group"
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)

def del_message_admin(msgId, chatId):
    start = ["0x12", "0x20"]
    unknown_symbol = "  "
    combined = unknown_symbol + chatId
    encoded_combined = base64.b64encode(combined.encode()).decode()
    data = ''.join(chr(int(value, 16)) for value in start) + msgId + base64.b64decode(encoded_combined).decode()

    headers = {
        "User-Agent": "windows 1.5.47",
        "Accept": "application/x-protobuf",
        "Accept-Encoding": "gzip",
        "Host": "chat-go.jwzhd.com",
        "Content-Type": "application/x-protobuf",
        "token": ADMIN_TOKEN
    }

    response = requests.post("https://chat-go.jwzhd.com/v1/msg/recall-msg", data=data,headers=headers)
    return response

def load_data():
    with open(data_path, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(data_path, 'w') as f:
        json.dump(data, f)

def is_forbidden_url(url, forbidden_urls):
    for forbidden_url in forbidden_urls:
        if "*" in forbidden_url:
            regex = forbidden_url.replace(".", r"\.").replace("*", ".*")
            if re.search(regex, url):
                return True
        else:
            if forbidden_url in url:
                return True
    return False

def extract_urls_from_html(html_content):
    urls = re.findall(
        r'(?:(?:https?://)?(?:(?:[a-zA-Z0-9\-_.]+)\.)+(?:[a-zA-Z]{2,6})+(?:/[\w\-\.]*)*(?:\?[\w\-\.\=\&]*)?(?:\#[\w\-]+)?)',
        html_content)
    return urls

def get_redirect_url(url, max_redirects=5):
    try:
        for _ in range(max_redirects):
            response = requests.head(url, allow_redirects=False)
            if 300 <= response.status_code < 400 and 'Location' in response.headers:
                url = response.headers['Location']
            else:
                break
        return url
    except Exception as e:
        print(f"Error during redirection: {e}")
        return None

def check_image_for_qr_code(image_url, image_name, forbidden_urls, recall_all_qr_images):
    try:
        response = requests.get(image_url)
        image_path = os.path.join(tmp_dir, os.path.basename(image_name))
        with open(image_path, 'wb') as f:
            f.write(response.content)

        reader = zxing.BarCodeReader()
        barcode = reader.decode(image_path, try_harder=True)

        if barcode:
            qr_url = barcode.parsed

            if recall_all_qr_images:
                return True, qr_url

            final_url = get_redirect_url(qr_url)
            if final_url and is_forbidden_url(final_url, forbidden_urls):
                return True, final_url

            if 'http' not in qr_url:
                qr_url = 'http://' + qr_url
            response = requests.get(qr_url)
            if response.status_code == 200:
                html_content = response.text
                urls_in_html = extract_urls_from_html(html_content)
                for url_in_html in urls_in_html:
                    if is_forbidden_url(url_in_html, forbidden_urls):
                        return True, url_in_html
        else:
            print("此图像没有二维码")

        return False, None

    except Exception as e:
        print(f"扫描图像中的二维码失败: {e}")
        return False, None
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


def check_forbidden_word(content, forbidden_words):
    for word in forbidden_words:
        if re.search(word, content, re.IGNORECASE):
            return True, word
    return False, None

def handle_message(json_data):
    event_type = json_data.get("header", {}).get("eventType")
    if event_type == "message.receive.normal":
        chat_id = json_data["event"]["chat"]["chatId"]
        msg_id = json_data["event"]["message"]["msgId"]
        content_type = json_data["event"]["message"]["contentType"]
        user_id = json_data["event"]["sender"]["senderId"]
        user_name = json_data["event"]["sender"]["senderNickname"]
        data = load_data()

        forbidden_words = data.get(chat_id, {}).get(id_1, {}).get("value", "")
        if forbidden_words:
            forbidden_words = forbidden_words.split('\n')
        forbidden_urls = data.get(chat_id, {}).get(id_5, {}).get("value", "").split('\n')
        enable_qr_check = data.get(chat_id, {}).get(id_4, {}).get("value", False)
        use_admin_token = data.get(chat_id, {}).get(id_7, {}).get("value", False)
        recall_all_qr_images = data.get(chat_id, {}).get(id_8, {}).get("value", False)
        white_list = data.get(chat_id, {}).get(id_9, {}).get("value", "").split("\n")
        black_list = data.get(chat_id, {}).get(id_10, {}).get("value", "").split("\n")

        if user_id in black_list:
            del_message(msg_id, chat_id)
            yhchat_push(chat_id, "group", "text", {"text": "你已被禁言，如有异议请联系管理员解封"})
            return

        if user_id in white_list:
            return

        content = json_data["event"]["message"]["content"].get("text", "")

        if "parent" in json_data["event"]["message"]["content"]:
            parent_content = json_data["event"]["message"]["content"]["parent"]
            is_parent_forbidden, matched_word_parent = check_forbidden_word(parent_content,forbidden_words)
            if is_parent_forbidden:
                if use_admin_token:
                    del_message_admin(msg_id, chat_id)
                else:
                    del_message(msg_id, chat_id)
                warn_message = data.get(chat_id, {}).get(id_6, {}).get("value", "")
                if warn_message:
                    formatted_warn_message = warn_message.format(user_name=user_name,word=matched_word_parent)
                    yhchat_push(chat_id, "group", "text",{"text": formatted_warn_message})
                else:
                    yhchat_push(chat_id, "group", "text",{"text": "你发送的消息中引用的内容包含违规词，已被自动撤回"})
                owner_ids = data.get(chat_id, {}).get(id_2, {}).get("value", "").split("\n")
                group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                if owner_ids:
                    message = f"群 [{group_name}({chat_id}) 中的一条消息因引用内容包含违规词被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"原消息内容：{content}\n" \
                              f"命中的违规词：{matched_word_parent}"
                    yhchat_batch_push(owner_ids, "user", "markdown", {"text": message})

        if content_type == "post":
            content = json_data["event"]["message"]["content"]["postContent"]
            is_forbidden, matched_word = check_forbidden_word(content, forbidden_words)
            if is_forbidden:
                if use_admin_token:
                    del_message_admin(msg_id, chat_id)
                else:
                    del_message(msg_id, chat_id)
                warn_message = data.get(chat_id, {}).get(id_6, {}).get("value", "")
                if warn_message:
                    formatted_warn_message = warn_message.format(user_name=user_name,word=matched_word)
                    yhchat_push(chat_id, "group", "text",{"text": formatted_warn_message})
                else:
                    yhchat_push(chat_id, "group", "text",{"text": "你发送的文章内容包含违规词，已被自动撤回"})
                owner_ids = data.get(chat_id, {}).get(id_2, {}).get("value", "").split("\n")
                group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                if owner_ids:
                    message = f"群 [{group_name}({chat_id}) 中的一条文章因包含违规词被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"文章内容：{content}\n" \
                              f"命中的违规词：{matched_word}"
                    yhchat_batch_push(owner_ids, "user", "markdown", {"text": message})

        elif forbidden_words and (content_type == "text" or content_type == "markdown"):
            is_forbidden, matched_word = check_forbidden_word(content, forbidden_words)
            if is_forbidden:
                if use_admin_token:
                    del_message_admin(msg_id, chat_id)
                else:
                    del_message(msg_id, chat_id)
                warn_message = data.get(chat_id, {}).get(id_6, {}).get("value", "")
                if warn_message:
                    formatted_warn_message = warn_message.format(user_name=user_name,word=matched_word)
                    yhchat_push(chat_id, "group", "text", {"text": formatted_warn_message})
                else:
                    yhchat_push(chat_id, "group", "text", {"text": "你发送的消息包含违规词，已被自动撤回"})
                owner_ids = data.get(chat_id, {}).get(id_2, {}).get("value", "").split("\n")
                group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                if owner_ids:
                    message = f"群 [{group_name}({chat_id}) 中的一条消息因包含违规词被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"原消息内容：{content}\n" \
                              f"命中的违规词：{matched_word}"
                    yhchat_batch_push(owner_ids, "user", "markdown", {"text": message})

        elif (content_type == "image" or content_type == "expression") and enable_qr_check:
            if content_type == "image":
                image_url = json_data["event"]["message"]["content"]["imageUrl"]
                image_name = json_data["event"]["message"]["content"]["imageName"]
            else:
                image_name = json_data["event"]["message"]["content"]["imageName"]
                image_url = f"https://chat-img.jwznb.com/{image_name}"

            is_forbidden, matched_url = check_image_for_qr_code(image_url, image_name, forbidden_urls, recall_all_qr_images)
            if is_forbidden:
                if use_admin_token:
                    del_message_admin(msg_id, chat_id)
                else:
                    del_message(msg_id, chat_id)
                if recall_all_qr_images:
                    yhchat_push(chat_id, "group", "text", {"text": "禁止发送二维码图片"})
                else:
                    yhchat_push(chat_id, "group", "text", {"text": f"你发送的图片包含违规二维码链接，已被自动撤回"})
                owner_ids = data.get(chat_id, {}).get(id_2, {}).get("value", "").split("\n")
                group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                if owner_ids:
                    message = f"群 [{group_name}({chat_id}) 中的一条图片消息因包含违规二维码链接被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"图片链接：![图片]({image_url})\n" \
                              f"命中的违规链接：{matched_url}"
                    yhchat_batch_push(owner_ids, "user", "markdown", {"text": message})

    elif event_type == "bot.setting":
        chat_id = json_data["event"]["groupId"]
        setting_json = json_data["event"]["settingJson"]
        data = load_data()
        data[chat_id] = json.loads(setting_json)
        save_data(data)


@app.route('/yhchat', methods=['POST'])
def receive_message():
    try:
        json_data = request.get_json()
        thread = Thread(target=handle_message, args=(json_data,))
        thread.start()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    if not os.path.exists(data_path):
        with open(data_path, 'w') as f:
            json.dump({}, f)
    app.run(host='0.0.0.0', port=34436)