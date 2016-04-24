# -*- coding: UTF-8 -*-
from web_wechat_api import WebWechatApi
import requests
import codecs

req = requests.Session()

def auto_replay(content):
    def _xiaodoubi(content):
        url = 'http://www.xiaodoubi.com/bot/chat.php'
        try:
            r = req.post(url, data = {'chat': content})
            data = r.content
            if data[:3] == codecs.BOM_UTF8:
                data = data[3:]
            return data.decode('utf-8')
        except:
            return 'Oops!'

    def _stupid(content):
        return 'I don\'t know [Frown]'

    return _xiaodoubi(content)

def sync_handler(wx, data):
    for msg in data['AddMsgList']:
        msg_type = msg['MsgType']
        if msg_type == 1:
            from_user = msg['FromUserName']
            to_user = msg['ToUserName']
            msg_content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            msg_time = msg['CreateTime']

            if from_user == wx.get_user_id(u'GreatYYX大帅哥'):
                reply = auto_replay(msg_content)
                wx.send_message(from_user, reply)

if __name__ == '__main__':
    try:
        wx = WebWechatApi()
        wx.add_sync_listener(sync_handler)

        wx.show_qr_image(wx.get_qr_image())
        while wx.wait_for_login() != '200':
            pass
        if not wx.init():
            raise Exception('wxinit')
        wx.start_heartbeat_loop()

    except Exception as e:
        print e