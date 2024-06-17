import os
import json
import requests
from flask import Flask, request, jsonify
import zxing
from threading import Thread

id_1 = ""  # 敏感词的表单id
id_2 = ""  # 群主的用户id的表单id
id_3 = ""  # 群名称的表单id
id_4 = ""  # 图片二维码识别开关的表单id
id_5 = ""  # 违规网址链接的表单id

TOKEN = ""  # 可在官网后台获取
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
    # print(json.loads(response.text))
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
    # print(json.loads(response.text))
    return json.loads(response.text)


def load_data():
    with open(data_path, 'r') as f:
        return json.load(f)


def save_data(data):
    with open(data_path, 'w') as f:
        json.dump(data, f)


def is_forbidden_url(url, forbidden_urls):
    for forbidden_url in forbidden_urls:
        if forbidden_url in url:
            return True
    return False


def extract_urls_from_html(html_content):
    import re
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
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


def check_image_for_qr_code(image_url, image_name, forbidden_urls):
    try:
        response = requests.get(image_url)
        image_path = os.path.join(tmp_dir, image_name)
        with open(image_path, 'wb') as f:
            f.write(response.content)

        reader = zxing.BarCodeReader()
        barcode = reader.decode(image_path, try_harder=True)
        if barcode:
            qr_url = barcode.parsed

            final_url = get_redirect_url(qr_url)
            if final_url and is_forbidden_url(final_url, forbidden_urls):
                os.remove(image_path)
                return True, final_url

            if 'http' in qr_url:
                response = requests.get(qr_url)
                if response.status_code == 200:
                    html_content = response.text
                    urls_in_html = extract_urls_from_html(html_content)
                    for url_in_html in urls_in_html:
                        if is_forbidden_url(url_in_html, forbidden_urls):
                            os.remove(image_path)
                            return True, url_in_html
        else:
            print("No QR code found in the image")

        os.remove(image_path)
        return False, None

    except Exception as e:
        print(f"Error during QR code check: {e}")
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

        forbidden_words = data.get(chat_id, {}).get(id_1, {}).get("value", "").split('\n')
        forbidden_urls = data.get(chat_id, {}).get(id_5, {}).get("value", "").split('\n')
        enable_qr_check = data.get(chat_id, {}).get(id_4, {}).get("value", False)

        if content_type == "text" or content_type == "markdown":
            content = json_data["event"]["message"]["content"]["text"]
            for word in forbidden_words:
                if word in content:
                    del_message(msg_id, chat_id)
                    yhchat_push(chat_id, "group", "text", {"text": "你发送的消息包含违规词，已被自动撤回"})

                    owner_id = data.get(chat_id, {}).get(id_2, {}).get("value", "")
                    group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                    if owner_id:
                        message = f"群 [{group_name}({chat_id})] 中的一条消息因包含违规词被撤回\n" \
                                  f"被撤回用户：{user_name}\n" \
                                  f"被撤回用户id：{user_id}\n" \
                                  f"原消息内容：{content}\n" \
                                  f"命中的违规词：{word}"
                        yhchat_push(owner_id, "user", "markdown", {"text": message})
                    break

        elif content_type == "image" and enable_qr_check:
            image_url = json_data["event"]["message"]["content"]["imageUrl"]
            image_name = json_data["event"]["message"]["content"]["imageName"]
            is_forbidden, matched_url = check_image_for_qr_code(image_url, image_name, forbidden_urls)
            if is_forbidden:
                del_message(msg_id, chat_id)
                # yhchat_push(chat_id, "group", "text", {"text": f"你发送的图片包含违规二维码链接({matched_url})，已被自动撤回"})
                yhchat_push(chat_id, "group", "text", {"text": f"你发送的图片包含违规二维码链接，已被自动撤回"})

                owner_id = data.get(chat_id, {}).get(id_2, {}).get("value", "")
                group_name = data.get(chat_id, {}).get(id_3, {}).get("value", "")
                if owner_id:
                    message = f"群 [{group_name}({chat_id})] 中的一条图片消息因包含违规二维码链接被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"图片链接：![图片]({image_url})\n" \
                              f"命中的违规链接：{matched_url}"
                    yhchat_push(owner_id, "user", "markdown", {"text": message})

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
        # 使用多线程处理消息
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
    app.run(host='0.0.0.0', port=56669)
