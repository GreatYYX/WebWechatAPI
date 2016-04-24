from web_wechat_api import WebWechatApi

def sync_handler(wx, data):
    print 'New data comes:', data

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