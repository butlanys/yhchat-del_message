from flask import Flask, request, jsonify
import json
import requests
import os
TOKEN = ""  # 可在官网后台获取
app = Flask(__name__)
data_path = 'data.json'
if not os.path.exists(data_path):
    with open(data_path, 'w') as f:
        json.dump({}, f)
def yhchat_push(recvId, recvType, contentType, text):
    url = f"https://chat-go.jwzhd.com/open-apis/v1/bot/send?token={TOKEN}"
    payload = json.dumps({
        "recvId": recvId,
        "recvType": recvType,
        "contentType": contentType,
        "content": {
            "text": text,
        }
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print(json.loads(response.text))
    return "OK"
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
    print(json.loads(response.text))
    return "OK"
def load_data():
    with open(data_path, 'r') as f:
        return json.load(f)
def save_data(data):
    with open(data_path, 'w') as f:
        json.dump(data, f)
def handle_message(json_data):
    event_type = json_data.get("header", {}).get("eventType")
    if event_type == "message.receive.normal":
        chat_id = json_data["event"]["chat"]["chatId"]
        msg_id = json_data["event"]["message"]["msgId"]
        content = json_data["event"]["message"]["content"]["text"]
        user_id = json_data["event"]["sender"]["senderId"]
        user_name = json_data["event"]["sender"]["senderNickname"]
        data = load_data()
        forbidden_words = data.get(chat_id, {}).get("woafca", {}).get("value", "").split('\n')
        for word in forbidden_words:
            if word in content:
                del_message(msg_id, chat_id)
                yhchat_push(chat_id, "group", "text", f"你发送的消息包含违规词，已被自动撤回")

                # 获取群主 ID、群名称并发送私聊通知
                owner_id = data.get(chat_id, {}).get("ebxulq", {}).get("value", "")
                group_name = data.get(chat_id, {}).get("enkfum", {}).get("value", "")
                if owner_id:
                    message = f"群 [{group_name}({chat_id})] 中的一条消息因包含违规词被撤回\n" \
                              f"被撤回用户：{user_name}\n" \
                              f"被撤回用户id：{user_id}\n" \
                              f"原消息内容：{content}\n" \
                              f"命中的违规词：{word}"
                    yhchat_push(owner_id, "user", "text", message)
                break
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
        handle_message(json_data)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=56669)