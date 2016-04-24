# Web Wechat API

微信Web版API的Python封装（并非直接的功能实现），及利用该Wrapper进行的功能开发。

Web微信协议及程序实现少量原创，大量参（抄）考（袭）了Urinx的[WeixinBot](https://github.com/Urinx/WeixinBot)和0x5e的[wechat-deleted-friends](https://github.com/0x5e/wechat-deleted-friends)，在此表示感谢！

欢迎Fork & Pull Request，欢迎提出新的TODO。

# 结构

- API
	- `web_wechat_api.py` API Wrapper
- Sample
	- `basic.py` 最小实现
	- `schedule_msg.py` 定时消息
	- `auto_reply.py` 自动回复

# TODO

## Base method

- [x] 获取二维码，登陆，获取好友列表
- [x] 同步线程，接收消息
- [x] 发送消息
- [ ] 群内成员
- [ ] 更新好友列表的修改

## Utility method

- [ ] 接收文本消息
- [ ] 接收位置消息
- [ ] 接收分享
- [ ] 接收名片
- [ ] 接收文件

## Application

- [ ] 定时消息
- [ ] 自动回复