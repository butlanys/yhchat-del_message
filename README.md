# 云湖敏感词bot
*群管理难？总是有广告哥来群里捣乱？*

来试试云湖敏感词bot帮助你管理群聊！

* 支持文本、markdown、图片、表情包、文章识别
* 支持敏感词正则表达式
* 支持顶级域以及子域屏蔽（例如*.top）
* 支持自定义撤回后的提示消息
* …………

- 默认监听http://server_ip:56669/yhchat

>部署示例：
>下载main.py后
>在当前目录下新建一个.env
>然后填写
>```
>ID_1=<表单id>
>…………
>ID_10=<表单id>
>TOKEN=<机器人token>
>
>pip3 install flask requests zxing pillow python-dotenv #zxing需要java环境，请自行安装
>python main.py

* 表单示例

![](images/1.png)

- 使用管理员权限撤回涉及到用户token，所以一般情况下不需要添加

如果想获得用户token，请在bash终端输入
```
curl 'https://chat-go.jwzhd.com/v1/user/email-login' \
  -H 'Accept: */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6' \
  -H 'Connection: keep-alive' \
  -H 'Origin: https://chat.yhchat.com' \
  -H 'Referer: https://chat.yhchat.com/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: cross-site' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0' \
  -H 'content-type: application/json' \
  -H 'sec-ch-ua: "Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'token;' \
  --data-raw '{"email":"邮箱","password":"密码","deviceId":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0","platform":"Web"}'
  ```
  CMD
  ```
  curl "https://chat-go.jwzhd.com/v1/user/email-login" ^
  -H "Accept: */*" ^
  -H "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6" ^
  -H "Connection: keep-alive" ^
  -H "Origin: https://chat.yhchat.com" ^
  -H "Referer: https://chat.yhchat.com/" ^
  -H "Sec-Fetch-Dest: empty" ^
  -H "Sec-Fetch-Mode: cors" ^
  -H "Sec-Fetch-Site: cross-site" ^
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0" ^
  -H "content-type: application/json" ^
  -H ^"sec-ch-ua: ^\^"Not/A)Brand^\^";v=^\^"8^\^", ^\^"Chromium^\^";v=^\^"126^\^", ^\^"Microsoft Edge^\^";v=^\^"126^\^"^" ^
  -H "sec-ch-ua-mobile: ?0" ^
  -H ^"sec-ch-ua-platform: ^\^"Windows^\^"^" ^
  -H "token;" ^
  --data-raw ^"^{^\^"email^\^":^\^"邮箱^\^",^\^"password^\^":^\^"密码^\^",^\^"deviceId^\^":^\^"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0^\^",^\^"platform^\^":^\^"Web^\^"^}^"
  ```