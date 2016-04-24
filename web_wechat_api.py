#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

import ssl
import os
import signal
import requests
import time
import re
import xml.dom.minidom
import sys
import subprocess
import webbrowser
import json
import threading
import random

# Constants
DEBUG = True
TEMP_PATH = os.path.join(os.getcwd(), 'tmp')
QR_IMAGE_PATH = os.path.join(TEMP_PATH, 'qrcode.jpg')
DEVICE_ID = 'e000000000000000'
HEARTBEAT_FREQENCY = 10
# map of push_uri and base_uri
MAP_URI = (
    ('wx2.qq.com', 'webpush2.weixin.qq.com'),
    ('qq.com', 'webpush.weixin.qq.com'),
    ('web1.wechat.com', 'webpush1.wechat.com'),
    ('web2.wechat.com', 'webpush2.wechat.com'),
    ('wechat.com', 'webpush.wechat.com'),
    ('web1.wechatapp.com', 'webpush1.wechatapp.com'),
)
SPECIAL_USER = (
    'newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage',
    'tmessage', 'qmessage', 'qqsync', 'floatbottle', 'lbsapp', 'shakeapp',
    'medianote', 'qqfriend', 'readerapp', 'blogapp', 'facebookapp', 'masssendapp',
    'meishiapp', 'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
    'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts',
    'notification_messages', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil',
    'userexperience_alarm', 'notification_messages'
)
# SYNC_HOST = (
#     'webpush.weixin.qq.com',
#     'webpush2.weixin.qq.com',
#     'webpush.wechat.com',
#     'webpush1.wechat.com',
#     'webpush2.wechat.com',
#     'webpush1.wechatapp.com',
#     # 'webpush.wechatapp.com'
# )

def print_msg(msg_type, content):
    if not isinstance(content, tuple):
        content = (content,)
    printf_msg(msg_type, '%s', ' '.join(str(x) for x in content))

def printf_msg(msg_type, format, content):
    # type: INFO , WARN , ERROR, DEBUG
    if not DEBUG and msg_type == 'DEBUG': return
    if not isinstance(content, tuple):
        content = (content,)
    print '[%s] ' % (msg_type,) + format % content

def write_to_file(name, data, mode = 'wb'):
    with open(os.path.join(TEMP_PATH, name), mode) as f:
        f.write(data)

class WebWechatApi():

    uuid = ''
    requests = None
    base_request = {}
    pass_ticket = ''
    tip = 0 # for QR code
    base_uri = ''
    push_uri = ''
    user_info = {}
    sync_key = {}

    member_list = []
    contact_list = []
    group_list = []
    special_user_list = []
    public_user_list = []

    heartbeat_thread_handler = None
    sync_listener = []

    #############
    #  BaseApi  #
    #############

    def __init__(self):
        # create requests object
        headers = {'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36'}
        self.requests = requests.Session()
        self.requests.headers.update(headers)

    def _get(self, url, params = None):
        r = self.requests.get(url = url, params = params)
        r.encoding = 'utf-8'
        return r

    def _post(self, url, data = None, json = False):
        headers = {'content-type': 'application/json; charset=UTF-8'} if json else {}
        r = self.requests.post(url = url, data = data, headers = {})
        r.encoding = 'utf-8'
        return r

    def _get_uuid(self):

        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()),
        }
        data = self._get(url = url, params = params).text
        print_msg('DEBUG', data)

        # response format:
        # window.QRLogin.code = 200; window.QRLogin.uuid = "oZwt_bFfRg==";
        regexp = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regexp, data)
        state_code, self.uuid = pm.group(1), pm.group(2)

        return state_code == '200'

    def get_qr_image(self):
        if not self._get_uuid():
            return None
        return 'https://login.weixin.qq.com/qrcode/' + self.uuid

    def wait_for_login(self):
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
            self.tip, self.uuid, int(time.time()))
        data = self._get(url = url).text
        print_msg('DEBUG', data)

        # response format:
        # window.code=200;window.redirect_uri="<strong>https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=80e3b62801bd4063ae6cf1928540da6d&uuid=787fef9712bd46&lang=zh_CN&scan=1434694049</strong>";
        regexp = r'window.code=(\d+);'
        pm = re.search(regexp, data)
        state_code = pm.group(1)

        if state_code == '201':  # scanned
            print_msg('INFO', 'QR Scanned. Please allow web login from Wechat mobile app')
            self.tip = 0
        elif state_code == '200':  # login...
            print_msg('INFO', 'Login...')

            regexp = r'window.redirect_uri="(\S+?)";'
            pm = re.search(regexp, data)
            redirect_uri = pm.group(1) + '&fun=new'
            self.base_uri = redirect_uri[:redirect_uri.rfind('/')]
            print_msg('DEBUG', (redirect_uri, self.base_uri))

            self.push_uri = self.base_uri
            for (s, p) in MAP_URI:
                if self.base_uri.find(s) >= 0:
                    self.push_uri = 'https://%s/cgi-bin/mmwebwx-bin' % p
                    break

            data = self._get(url = redirect_uri).text
            print_msg('DEBUG', data)

            doc = xml.dom.minidom.parseString(data)
            root = doc.documentElement
            for node in root.childNodes:
                if node.nodeName == 'skey':
                    skey = node.childNodes[0].data
                elif node.nodeName == 'wxsid':
                    wxsid = node.childNodes[0].data
                elif node.nodeName == 'wxuin':
                    wxuin = node.childNodes[0].data
                elif node.nodeName == 'pass_ticket':
                    self.pass_ticket = node.childNodes[0].data
            printf_msg('DEBUG', 'skey: %s, wxsid: %s, wxuin: %s, pass_ticket: %s', (skey, wxsid, wxuin, self.pass_ticket))

            if not all((skey, wxsid, wxuin, self.pass_ticket)):
                print_msg('ERROR', 'Login error #2')

            self.base_request = {
                'Uin': int(wxuin),
                'Sid': wxsid,
                'Skey': skey,
                'DeviceID': DEVICE_ID,
            }

            # close QR image and remove
            pass

        elif state_code == '408':  # timeout
            print_msg('ERROR', 'Time out')
        else:
            print_msg('ERROR', 'Login error')

        return state_code

    def response_state(self, func, base_response):
        err_msg = base_response['ErrMsg']
        ret = base_response['Ret']
        if ret == '1101':
            print_msg('INFO', 'logout')
            exit(1)
        if ret != 0:
            printf_msg('ERROR', 'Func: %s, Ret: %d, ErrMsg: %s', (func, ret, err_msg))
        elif DEBUG:
            printf_msg('INFO', 'Func: %s, Ret: %d, ErrMsg: %s', (func, ret, err_msg))

        return ret == 0

    def init(self):
        url = '%s/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            self.base_uri, self.pass_ticket, self.base_request['Skey'], int(time.time()))
        params = {'BaseRequest': self.base_request}

        r = self._post(url = url, data = json.dumps(params), json = True)
        data = r.json()

        state = self.response_state('webwxinit', data['BaseResponse'])
        if not state:
            return False

        if DEBUG:
            with open(os.path.join(TEMP_PATH, 'webwxinit.json'), 'wb') as f:
                f.write(r.content)
            f.close()

        # self.contact_list = data['ContactList']
        self.user_info = data['User']
        self.sync_key = data['SyncKey']

        return self._init_contact()

    def _init_contact(self):
        url = '%s/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.base_uri, self.pass_ticket, self.base_request['Skey'], int(time.time()))

        r = self._post(url = url, json = True)
        data = r.json()

        state = self.response_state('webwxgetcontact', data['BaseResponse'])
        if not state:
            return False

        if DEBUG:
            write_to_file('webwxgetcontact.json', r.content)

        self.member_list = data['MemberList']
        self.contact_list = self.member_list[:]

        for i in xrange(len(self.member_list) - 1, -1, -1):
            contact = self.contact_list[i]
            if contact['VerifyFlag'] & 8 != 0:  # public / service
                del self.contact_list[i]
                self.public_user_list.append(contact)
            elif contact['UserName'] in SPECIAL_USER:  # special user
                del self.contact_list[i]
                self.special_user_list.append(contact)
            elif contact['UserName'].find('@@') != -1:  # group
                del self.contact_list[i]
                self.group_list.append(contact)
            elif contact['UserName'] == self.user_info['UserName']:  # self
                del self.contact_list[i]

        if DEBUG:
            write_to_file('webwxgetcontact_contact.json', json.dumps(self.contact_list, indent = 4))
            write_to_file('webwxgetcontact_group.json', json.dumps(self.group_list, indent = 4))
            write_to_file('webwxgetcontact_special.json', json.dumps(self.special_user_list, indent = 4))
            write_to_file('webwxgetcontact_public.json', json.dumps(self.public_user_list, indent = 4))

        return True

    def add_sync_listener(self, callback):
        self.sync_listener.append(callback)

    def start_heartbeat_loop(self):
        self.heartbeat_thread_handler = threading.Thread(target = self._heartbeat_thread)
        print_msg('DEBUG', 'heartbeat loop start...')
        self.heartbeat_thread_handler.start()

    def _heartbeat_thread(self):
        while True:
            selector = self._sync_check()
            if selector != '0':
                data = self._sync()
                if not self._sync():
                    print_msg('ERROR', 'heartbeat thread sync')

                if selector == '2': # new message
                    for callback in self.sync_listener:
                        callback(self, data)

            time.sleep(HEARTBEAT_FREQENCY)

    def _sync_key_str(self):
        return '|'.join(['%s_%s' % (item['Key'], item['Val']) for item in self.sync_key['List']])

    def _sync_check(self):
        print_msg('DEBUG', 'heartbeat syncheck')
        url = self.push_uri + '/synccheck'
        params = {
            'skey': self.base_request['Skey'],
            'sid': self.base_request['Sid'],
            'uin': self.base_request['Uin'],
            'deviceId': self.base_request['DeviceID'],
            'synckey': self._sync_key_str(),
            'r': int(time.time()),
            '_': int(time.time()),
        }

        data = self._get(url = url, params = params).text

        # response format
        # window.synccheck={retcode:"0", selector:"2"}
        regexp = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
        pm = re.search(regexp, data)
        retcode, selector = pm.group(1), pm.group(2)

        if retcode != '0':
            print_msg('INFO', 'logout')
            exit(1)

        return selector

    def _sync(self):
        url = '%s/webwxsync?lang=zh_CN&skey=%s&sid=%s&pass_ticket=%s' % (
            self.base_uri, self.base_request['Skey'], self.base_request['Sid'], self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time()),
        }

        r = self._post(url = url, data = json.dumps(params))
        data = r.json()
        # print(data)

        state = self.response_state('webwxsync', data['BaseResponse'])
        if not state:
            return None

        self.sync_key = data['SyncKey']
        return data

    def _transcoding(self, data):
        ret = None
        if type(data) == unicode:
            ret = data
        elif type(data) == str:
            ret = data.decode('utf-8')
        return ret

    def send_message(self, to_user, content):
        url = '%s/webwxsendmsg?pass_ticket=%s' % (self.base_uri, self.pass_ticket)
        client_msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        params = {
            'BaseRequest': self.base_request,
            'Msg': {
                "Type": 1,
                "Content": self._transcoding(content),
                "FromUserName": self.user_info['UserName'],
                "ToUserName": to_user,
                "LocalID": client_msg_id,
                "ClientMsgId": client_msg_id
            }
        }
        params = json.dumps(params, ensure_ascii = False).encode('utf8')
        data = self._post(url = url, data = params, json = True).json()
        return self.response_state('webwxsendmsg', data['BaseResponse'])

    def logout(self):
        url = '%s/webwxlogout?redirect=1&type=0&skey=%s' % (self.base_uri, self._sync_key_str())
        params = {
            'sid': self.base_request['Sid'],
            'uin': self.base_request['Uin']
        }
        self._post(url = url, data = params)
        print_msg('INFO', 'logout')


    #############
    #  Utility  #
    #############

    # method could be local, web
    def show_qr_image(self, url, method = 'local'):
        print_msg('INFO', 'Please use Wechat mobile app to scan QR image')
        self.tip = 1

        if method == 'web':
            webbrowser.open_new_tab(url)
            return
        else:
            params = {
                't': 'webwx',
                '_': int(time.time()),
            }
            data = self._get(url = url, params = params).content

            with open(QR_IMAGE_PATH, 'wb') as f:
                f.write(data)
            time.sleep(1)

            if sys.platform.find('darwin') >= 0: subprocess.call(('open', QR_IMAGE_PATH))
            elif sys.platform.find('linux') >= 0: subprocess.call(('xdg-open', QR_IMAGE_PATH))
            elif sys.platform.find('win32') >= 0: subprocess.call(('cmd', '/C', 'start', QR_IMAGE_PATH))
            else: os.startfile(QR_IMAGE_PATH)

    def get_user_id(self, name):
        for m in self.member_list:
            if name == m['RemarkName'] or name == m['NickName']:
                return m['UserName']
        return None

    def get_user_remark_name(self, id):
        if id == self.user_info['UserName']: # self
            return self.user_info['NickName']

        if id[:2] == '@@': # group
            for m in self.group_list:
                pass # need to handle
        else:
            # contact
            for m in self.contact_list:
                if m['UserName'] == id:
                    return m['RemarkName'] if m['RemarkName'] else m['NickName']

            # special
            for m in self.special_user_list:
                if m['UserName'] == id:
                    name = m['RemarkName'] if m['RemarkName'] else m['NickName']
                    return name

            # public
            for m in self.public_user_list:
                if m['UserName'] == id:
                    return m['RemarkName'] if m['RemarkName'] else m['NickName']

            # group member
            # for m in self.group_member_list:
            #     if m['UserName'] == id:
            #         return m['DisplayName'] if m['DisplayName'] else m['NickName']

        return 'unknown'
