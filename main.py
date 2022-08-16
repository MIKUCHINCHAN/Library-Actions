from urllib.parse import unquote_plus
import requests
import datetime
import urllib3
import hashlib
import urllib
import base64
import json
import time
import hmac
import pytz
import re
import os


# github的云函数env定义的值是字符串，所以对于字典或者列表先要将其还原成原来的格式,当某一项留空时，传递的值为空字符串
USERNAME=eval(os.environ["USERNAME"])  # 账号-->学号
PASSWORD=os.environ["PASSWORD"]  # 密码
AREA_ID=eval(os.environ["AREA_ID"])  # 想要预约的房间编号，默认是10、8，若想添加其他的，可以先运行脚本，会显示出其他房间的编号，再自行添加或者更改，同时优先考虑高楼层，且房间中优先考虑大座位号
BANNED_SEAT=eval(os.environ["BANNED_SEAT"]) if os.environ["BANNED_SEAT"] else ''  # 绝对不要的座位号  {房间1号ID:[座位号1,座位号2,座位号3,.....]，房间2号ID:...,...}
OK_SEAT=eval(os.environ["OK_SEAT"]) if os.environ["OK_SEAT"] else ''  # 除了BANNED_SEAT以外座位号的倾向，即一个房间中哪些位置比较喜欢   房间ID对应的列表内，越靠前的列表越是倾向（倾向分级）
DD_BOT_ACCESS_TOKEN = os.environ["DD_BOT_ACCESS_TOKEN"]  # 当只填写了一个通知方式时，未填写的os.environ["xxx"]返回None，所以不影响
DD_BOT_SECRET = os.environ["DD_BOT_SECRET"]
BARK_TOKEN=os.environ["BARK_TOKEN"]
ALWAYS_SPARE_AREA=eval(os.environ["ALWAYS_SPARE_AREA"]) if os.environ["ALWAYS_SPARE_AREA"] else ''  #配合救援模式，填写一个总是坐不满的房间
SELECT_WAY=eval(os.environ["SELECT_WAY"]) if os.environ["SELECT_WAY"] else ''  # 筛选座位的方式，可选的为1和2
              # 1 优先级在于房间,优先一个房间的所有位置，其次为第二个房间的所有位置，该情况下，同一房间中的大号优先
              # 2 优先级在于座位号,一级优先的是某几个房间的某些位置，二级优先为某几个房间的另外某些位置……(具体见readme.md)


# 救场用户的账号密码，当OTHERS_ACCOUNT={}即不启用救援模式,用于解决由于意外不能在30min内完成签到的情况，账号越靠前越快用到，且对于账号可用性无需保证都能用，会每次检查账号密码是否正确;如果能收集到很多账号这里可添加无数个
# 创建动态变量
OTHERS_ACCOUNT = {}
dynamic_variable = locals()
for i in range(1,11):
    dynamic_variable[f'OTHERS_ACCOUNT_USERNAME_{i}'] =eval(os.environ[f"OTHERS_ACCOUNT_USERNAME_{i}"]) if os.environ[f"OTHERS_ACCOUNT_USERNAME_{i}"] else ''
    dynamic_variable[f'OTHERS_ACCOUNT_PASSWORD_{i}'] =os.environ[f"OTHERS_ACCOUNT_PASSWORD_{i}"]
    if dynamic_variable[f'OTHERS_ACCOUNT_USERNAME_{i}']:
        OTHERS_ACCOUNT[dynamic_variable[f'OTHERS_ACCOUNT_USERNAME_{i}']]=dynamic_variable[f'OTHERS_ACCOUNT_PASSWORD_{i}']


def get_inform_way():
    """
    同时考虑到本地和github云端执行，先判断变量是否存在-对于本地是不存在的、云端是存在的但为None，再判断是否是None
    当填写多个通知方式时，越在前面越是优先，若都没填写那么终止运行程序
    :return: 0-钉钉 1-BARK
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    if 'DD_BOT_ACCESS_TOKEN' in globals().keys():
        if DD_BOT_ACCESS_TOKEN:
            INFORMED_WAY = 0
            print('■■■通知方式为 钉钉')
            return 0
    if 'BARK_TOKEN' in globals().keys():
        if BARK_TOKEN:
            INFORMED_WAY = 1
            print('■■■通知方式为 BARK')
            return 1
    if 'INFORMED_WAY' not in globals().keys():
        print('■■■通知方式未设置或设置错误，请检查')
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        quit()
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")

def inform_by_bark(str):
    """
    通过bark进行通知结果
    """
    requests.get(BARK_TOKEN+str)

def inform_by_dingding(error_msg=''):
    """
    通过dingding进行通知结果
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    timestamp = str(round(time.time() * 1000))  # 时间戳
    secret_enc = DD_BOT_SECRET.encode("utf-8")
    string_to_sign = "{}\n{}".format(timestamp, DD_BOT_SECRET)
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))  # 签名
    print("■■■开始使用【钉钉机器人】", end="")
    url = f"https://oapi.dingtalk.com/robot/send?access_token={DD_BOT_ACCESS_TOKEN}&timestamp={timestamp}&sign={sign}"
    headers = {"Content-Type": "application/json;charset=utf-8"}
    if IS_UTC:
        now=datetime.datetime.now()+datetime.timedelta(hours=8)
    else:
        now=datetime.datetime.now()
    if RESERVED_SEAT:
        data = {
            "msgtype": "text",
            "text": {
                "content": f"📖 图书馆预约结果通知\n---------\n预约用户：{PRINT_NAME}\n\n预约项目：{str(PRINT_AREA_NAME)}\n\n预约情况：✅{AREA_ID_AND_NAME[RESERVED_SEAT[2]]}{RESERVED_SEAT[1]}号\n\n预约时间：{str(now)[0:16]}\n\n健康状况：{STATUS}\n\n今日剩余可取消次数：{check_cancel_chance(USERNAME)}\n\n场外救援状态：{'关闭' if  not OTHERS_ACCOUNT else '开启' if check_cancel_chance(USERNAME)==1 else '不可使用场外救援,请在30分钟内完成签到'}\n\n场外救援有效性：{f'{len(VALID_OTHERS_ACCOUNT)}/{len(OTHERS_ACCOUNT)}'}"
            },
        }
    else:
        data = {
            "msgtype": "text",
            "text": {
                "content": f"📖 图书馆预约结果通知\n---------\n预约用户：{PRINT_NAME}\n\n预约项目：{str(PRINT_AREA_NAME)}\n\n预约情况：❌{error_msg}\n\n预约时间：{str(now)[0:16]}\n\n健康状况：{STATUS}\n\n今日剩余可取消次数：{check_cancel_chance(USERNAME)}\n\n场外救援状态：{'关闭' if  not OTHERS_ACCOUNT else '开启' if check_cancel_chance(USERNAME)==1 else '不可使用场外救援,请在30分钟内完成签到'}\n\n场外救援有效性：{f'{len(VALID_OTHERS_ACCOUNT)}/{len(OTHERS_ACCOUNT)}'}"
            },
        }
    return_msg = requests.post(url=url, data=json.dumps(data), headers=headers, timeout=15).json()
    if not return_msg['errcode']:
        print('【推送成功】')
    else:
        print("■■■dingding:" + str(return_msg['errcode']) + ": " + str(return_msg['errmsg']))
        print('【推送失败，请检查错误信息】')

def get(url,headers,):
    """
    处理连接超时的情况
    """
    try:
        response = requests.get(url=url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response
    except requests.exceptions.Timeout or requests.exceptions.ReadTimeout or urllib3.exceptions.ReadTimeoutError or requests.exceptions.ConnectionError:
        global NETWORK_STATUS
        NETWORK_STATUS = False # 请求超时改变状态

        if NETWORK_STATUS == False:
            '''请求超时'''
            for i in range(1, 30):
                print(f'请求超时，第{i}次重复请求')
                # timeout单位为s
                try:
                    response = requests.get(url=url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        return response
                except (requests.exceptions.Timeout,requests.exceptions.ReadTimeout,urllib3.exceptions.ReadTimeoutError,requests.exceptions.ConnectionError):
                    continue
    return -1  # 当所有请求都失败，返回  -1  ，此时有极大的可能是网络问题或IP被封。

def post(url,headers,data):
    """
    处理连接超时的情况
    """
    try:
        response = req.post(url=url, headers=headers, timeout=5,data=data)
        if response.status_code == 200:
            return response
    except requests.exceptions.Timeout or requests.exceptions.ReadTimeout:
        global NETWORK_STATUS
        NETWORK_STATUS = False # 请求超时改变状态

        if NETWORK_STATUS == False:
            '''请求超时'''
            for i in range(1, 30):
                print(f'请求超时，第{i}次重复请求')
                # timeout单位为s
                try:
                    response = req.post(url=url, headers=headers, timeout=5, data=data)
                    if response.status_code == 200:
                        return response
                except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout,urllib3.exceptions.ReadTimeoutError, requests.exceptions.ConnectionError):
                    continue

    return -1  # 当所有请求都失败，返回  -1  ，此时有极大的可能是网络问题或IP被封。

def COOKIE_STATUS():
    """
    检查cookie是否失效，寿命为5分钟
    :return: 0-失效 1-未失效
    """
    expire = datetime.datetime.strptime(unquote_plus(req.cookies.get('expire')), '%Y-%m-%d %H:%M:%S')
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).now().replace(microsecond=0)  #注意在云上的时间是国际标准时间,把微秒去掉
    if (expire -now).seconds>60:
        return 1
    else:
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        print('■■■COOKIE已失效（寿命<=60s）')
        print('■■■COOKIE失效时间   \t',expire)
        print('■■■当前上海时间   \t',now)
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0



# def expand_cookie_lifetime():
#
#     headers={
#     "Cookie": cookie_moudle.get_local_cookies_style2(),
#     "Host": "rg.lib.xauat.edu.cn",
#     "Origin": "http://rg.lib.xauat.edu.cn",
#     "Referer": "http://rg.lib.xauat.edu.cn/web/seat3?area=10&segment=1319909&day=2021-11-14&startTime=20:11&endTime=23:00",
#     "User-Agent": spider_UA.User_Agent,
#     "X-Requested-With": "XMLHttpRequest",
#     }
#
#     # 请求不存在的选座页面,随便选择一个座位
#     # 正常来说预约是post，但是用get一样可以延长cookie寿命
#     res=requests.get("http://rg.lib.xauat.edu.cn/api.php/spaces/3787/book",headers=headers)
#
#     # 将新的cookie写入
#     cookie_moudle.write_cookies_to_local(res.headers['Set-Cookie'])
#
#     print("cookie延时成功")

def login_in_1(USERNAME=USERNAME,PASSWORD=PASSWORD):
    """
    多用来登录获取cookie，当登录失败时会调用钉钉进行通知
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = post(url="http://rg.lib.xauat.edu.cn/api.php/login",
                   headers={"Referer": "http://www.skalibrary.com/",
                            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74"},
                   data={"username": USERNAME, "password": PASSWORD, "from": "mobile"})
    if json.loads(res.content)['status']:
        print(f"■■■ 姓名   \t{json.loads(res.content)['data']['list']['name']}")
        print(f"■■■登录状态\t{json.loads(res.content)['msg']}")
        global PRINT_NAME
        PRINT_NAME =json.loads(res.content)['data']['list']['name']
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 1
    else:
        print(f"■■■登录失败\t{json.loads(res.content)['msg']}")
        if INFORMED_WAY==0:
            inform_by_dingding(f"登录失败 {json.loads(res.content)['msg']}")
        if INFORMED_WAY == 1:
            inform_by_bark(f"登录失败 {json.loads(res.content)['msg']}")
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0

def login_in_2(USERNAME=USERNAME,PASSWORD=PASSWORD):
    """
    登录获取cookie，当登录失败时不会调用钉钉进行通知
    多用来检查账号的密码的可用性，0-不可用，1-可用，
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = post(url="http://rg.lib.xauat.edu.cn/api.php/login",
                   headers={"Referer": "http://www.skalibrary.com/",
                            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74"},
                   data={"username": USERNAME, "password": PASSWORD, "from": "mobile"})
    if json.loads(res.content)['status']:
        print(f"■■■ 姓名   \t{json.loads(res.content)['data']['list']['name']}")
        print(f"■■■登录状态\t{json.loads(res.content)['msg']}")
        global PRINT_NAME
        PRINT_NAME =json.loads(res.content)['data']['list']['name']
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 1
    else:
        print(f"■■■登录失败\t{json.loads(res.content)['msg']}")
        # if INFORMED_WAY==0:
        #     inform_by_dingding(f"登录失败 {json.loads(res.content)['msg']}")
        # if INFORMED_WAY == 1:
        #     inform_by_bark(f"登录失败 {json.loads(res.content)['msg']}")
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0

def check_OTHERS_ACCOUNT_valid():
    """
    检查救场用户的可用性,过程中会将密码有效的且取消次数为1的用户放到VALID_OTHERS_ACCOUNT内，密码无效的用户放到INVALID_OTHERS_ACCOUNT内
    """
    # 检查救场用户的可用性
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    global VALID_OTHERS_ACCOUNT
    global INVALID_OTHERS_ACCOUNT
    _={}  #用于存放密码正确但取消预约次数=0的用户
    for others_account_name, others_account_password in OTHERS_ACCOUNT.items():
        # login_in函数中的全局变量会产生bug，每次登陆完他人的账号，**最后都要登陆一下自己的**
        if login_in_2(others_account_name,others_account_password):
            if check_cancel_chance(others_account_name)==1:
                VALID_OTHERS_ACCOUNT[others_account_name]=others_account_password
            else:
                _[others_account_name]=others_account_password
        else:
            INVALID_OTHERS_ACCOUNT[others_account_name] = others_account_password
    print(f'■■■救场用户有效占比:{len(VALID_OTHERS_ACCOUNT)}/{len(OTHERS_ACCOUNT)}')
    if list(INVALID_OTHERS_ACCOUNT.keys()):
        print(f'■■■因密码错误而失效：{list(INVALID_OTHERS_ACCOUNT.keys())}')
    if list(_.keys()):
        print(f'■■■因取消次数不足而失效：{list(_.keys())}')
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")

def get_area_id():
    """
    获取区域信息,不需要cookie即可直接调用
    :return 0-失败，1-成功
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = get(url="http://rg.lib.xauat.edu.cn/api.php/areas?tree=1",headers={"Referer": "http://www.skalibrary.com/"})
    if json.loads(res.content)['status']:
        # 第一层-图书馆信息（可能是两个图书馆），第二层-楼层信息，第三层-空间信息
        for library_info in json.loads(res.content)['data']['list']:
            for floor_info in library_info['_child']:
                for area_info in floor_info['_child']:
                    if area_info['id'] in AREA_ID:
                        print(f"■■■\tid-{area_info['id']}\t{area_info['nameMerge']}")
                        PRINT_AREA_NAME.append(area_info['nameMerge'])
                    else:
                        print(f"   \tid-{area_info['id']}\t{area_info['nameMerge']}")
                    AREA_ID_AND_NAME.update({area_info['id']:area_info['nameMerge']})
                    # 部分未列出的参数，可作为(若某些区域禁止预约)判断依据，尤其注意'isValid'
                    # print(area_info['isValid'])
                    # print(area_info['levels'])
                    # print(area_info['sort'])
                    # print(area_info['type'])
                    # print(area_info['ROW_NUMBER'])
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    else:
        print(f"■■■获取区域信息失败 {json.loads(res.content)['msg']}")
        if INFORMED_WAY==0:
            inform_by_dingding(f"获取区域信息失败 {json.loads(res.content)['msg']}")
        if INFORMED_WAY==1:
            inform_by_bark(f"获取区域信息失败 {json.loads(res.content)['msg']}")
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        quit()


def url_info():
    """
    获取url信息,不需要cookie
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    for area_id in AREA_ID:
        res = get(
            url=f"http://rg.lib.xauat.edu.cn/api.php/space_time_buckets?area={area_id}&day={datetime.date.today()}",
            headers={"Referer": "http://www.skalibrary.com/"})
        if json.loads(res.content)['status']:
            #  spaceId代表这一房间的id，永远不变，SEGMENT=id=bookTimeId，每个房间每天都不一样，含房间和时间信息
            spaceId = json.loads(res.content)['data']['list'][0]['spaceId']
            id = json.loads(res.content)['data']['list'][0]['id']
            endTime = json.loads(res.content)['data']['list'][0]['endTime']
            day = json.loads(res.content)['data']['list'][0]['day']
            startTime = json.loads(res.content)['data']['list'][0]['startTime']
            seat_info_url=f"http://rg.lib.xauat.edu.cn/api.php/spaces_old?area={area_id}&day={day}&endTime={endTime}&segment={id}&startTime={startTime}"
            SEGMENT.append(id)
            SEAT_INFO_URL.append(seat_info_url)
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        else:
            print(f"■■■获取可预约时间段失败 {json.loads(res.content)['msg']}")
            if INFORMED_WAY == 0:
                inform_by_dingding(f"获取可预约时间段失败 {json.loads(res.content)['msg']}")
            if INFORMED_WAY == 1:
                inform_by_bark(f"获取可预约时间段失败 {json.loads(res.content)['msg']}")
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
            quit()

def seat_info(seat_info_url):
    """
    根据链接中的area_id 来获取对应的中文名，并获取空闲座位的信息
    :param seat_info_url: 传入的网址类似http://rg.lib.xauat.edu.cn/api.php/spaces_old?area=8&day=2022-07-09&endTime=22:00&segment=1403926&startTime=14:50
    :return:
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    area_name=AREA_ID_AND_NAME[int(re.search('\?area=(\d*)&day', seat_info_url).group(1))]
    # 获取seat信息,不需要cookie
    res = get(
        url=seat_info_url,
        headers={"Referer": "http://www.skalibrary.com/",
                 "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74"})
    if json.loads(res.content)['status']:
        all_seat_info=json.loads(res.content)['data']['list']
        all_seat_info.reverse()  #同一房间中大号优先append到RESERVE_SEAT
        for seat_info in all_seat_info:
            seat_id = seat_info['id']
            seat_name = seat_info['name']
            seat_status_name = seat_info['status_name']
            seat_area=seat_info['area']
            # area_name = seat_info['area_name']  #不可以从这里取得房间名称，因为对于三楼移动设备或者四楼移动设备区显示都是'移动设备区'
            if seat_status_name == "空闲":
                RESERVE_SEAT.append([seat_id,seat_name,seat_area,SEGMENT[SEAT_INFO_URL.index(seat_info_url)]])
        now = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).now().replace(
            microsecond=0)  # 注意在云上的时间是国际标准时间,把微秒去掉
        print(f'■■■{now}\t{area_name}\t可预约的座位\t',RESERVE_SEAT)
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 1
    else:
        print(f"■■■获取空间预约信息失败 {json.loads(res.content)['msg']}")
        inform_by_dingding(f"获取空间预约信息失败 {json.loads(res.content)['msg']}")
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0

def reserve(USERNAME=USERNAME):
    """
    预约
    :return: 0-预约失败，所有空闲位置都是banned，1-成功
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    if SELECT_WAY==2:
        # 先对OK_SEAT按优先级进行遍历
        results=[]
        __ = []
        for key_area_id, items_seat_ids in OK_SEAT.items():
            for item_seat_id in items_seat_ids:
                __.append((key_area_id, item_seat_id))
        while __:
            for key_area_id in list(OK_SEAT.keys()):
                for _ in __:
                    if _[0] == key_area_id:
                        results.append(_)
                        __.remove(_)
                        break
        # 再对RESERVE_SEAT进行遍历排序
        global RESERVE_SEAT_SORTED
        # RESERVE_SEAT---[seat_id,seat_name,seat_area,SEGMENT[SEAT_INFO_URL.index(seat_info_url)]]
        for result in results:
            for SEAT in RESERVE_SEAT:
                for a in result[1]:
                    if result[0] == SEAT[2] and a == SEAT[1]:
                        RESERVE_SEAT_SORTED.append(SEAT)
        for _ in RESERVE_SEAT_SORTED:
            RESERVE_SEAT.remove(_)
        for key_area_id in OK_SEAT.keys():
            for _ in RESERVE_SEAT:
                if _[2]==key_area_id:
                    RESERVE_SEAT_SORTED.append(_)
        for  key_area_id in AREA_ID:
            for _ in RESERVE_SEAT:
                if _[2]==key_area_id:
                    RESERVE_SEAT_SORTED.append(_)
    else:
        RESERVE_SEAT_SORTED=RESERVE_SEAT


    for SEAT in RESERVE_SEAT_SORTED:
        # 跳过banned的座位号
        if BANNED_SEAT:
            if SEAT[2] in BANNED_SEAT.keys():
                if SEAT[1] in BANNED_SEAT[SEAT[2]]:
                    print('■■■{AREA_ID_AND_NAME[SEAT[2]]}■■座位号-{SEAT[1]}■■该座位banned，正在预约其他座位')
                    # RESERVE_SEAT.remove(SEAT)  #不需要global声明即可全局生效 #不可remove，否则会和for循环产生bug
                    continue

        # 预约,需要cookie
        res = post(
            url=f"http://rg.lib.xauat.edu.cn/api.php/spaces/{SEAT[0]}/book",
            headers={"Referer": "http://www.skalibrary.com/",
                     "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74"},
            data = {"access_token": req.cookies.get("access_token"), "userid": USERNAME, "type": 1,"id": SEAT[0],"segment": SEAT[3]})
        if json.loads(res.content)['status']:
            # json.loads(res.content)['msg']--->预约成功<br/>您已违约2次,详情请登录web端或联系管理员
            if "违约" in json.loads(res.content)['msg']:
                global STATUS
                STATUS=re.search("已违约\w次", json.loads(res.content)['msg']).group()
            else:
                STATUS = json.loads(res.content)['msg']
                if STATUS=='预约成功':
                    STATUS='已违约0次'
            RESERVED_SEAT.extend(SEAT)
            print(f'■■■预约信息■■seat_id {SEAT[0]}■■seat_name {SEAT[1]}■■area_id {SEAT[2]}■■area_segment {SEAT[3]}■■')
            print(f"■■■{AREA_ID_AND_NAME[SEAT[2]]}■■座位号-{SEAT[1]}■■{STATUS}")
            if INFORMED_WAY == 0:
                inform_by_dingding()
            if INFORMED_WAY == 1:
                inform_by_bark(f"■■■{AREA_ID_AND_NAME[SEAT[2]]}■■座位号-{SEAT[1]}■■{STATUS}")
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
            return 1
        elif json.loads(res.content)['status']==0 and json.loads(res.content)['msg']=='该空间当前状态不可预约':
            print(f'■■■预约信息■■seat_id {SEAT[0]}■■seat_name {SEAT[1]}■■area_id {SEAT[2]}■■area_segment {SEAT[3]}■■')
            print(f"■■■{AREA_ID_AND_NAME[SEAT[2]]}■■座位号■■{SEAT[1]}")
            print('该空间当前状态不可预约，正在预约其他座位')
        else:
            print(f"■■■预约失败 {json.loads(res.content)['msg']}")
            if INFORMED_WAY == 0:
                inform_by_dingding(f"预约失败 {json.loads(res.content)['msg']}")
            if INFORMED_WAY == 1:
                inform_by_bark(f"预约失败 {json.loads(res.content)['msg']}")
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
            quit()
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    return 0

def check_cancel_chance(USERNAME):
    """
    查询今日还可取消的次数
    """
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = get(
        url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/",
        headers={
            "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
            'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'})

    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).now().replace(microsecond=0)  # 注意在云上的时间是国际标准时间,把微秒去掉

    cancel_chance = 1  # 从1开始减

    # 检查今日记录的时间，如"202207072021"
    for record in json.loads(res.content)['data']['list']:

        # 筛选出今天的记录
        if record['no'][:8]==str(now.date()).replace('-',''):
            if record['statusName'] == '预约开始提醒':
                pass
            elif record['statusName'] == '使用中':
                pass
            elif record['statusName'] == '已使用':
                pass
            elif record['statusName'] == '已关闭':
                pass
            elif record['statusName'] == '用户取消':
                cancel_chance-=1
    # 包含今天没有记录的情况
    if cancel_chance==1:
        print('■■■今日还可以取消一次')
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 1
    elif cancel_chance==0:
        print('■■■今日不可以取消')
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0

def check_status(USERNAME=USERNAME):
    """
    今天的记录中最新的那条的状态，return返回的，0-今日无记录，3-使用中，4-已使用，6-用户取消，8-已关闭，9-预约开始提醒
    """
    # 注意这里会先查询历史记录，并向RESERVE_SEAT里append一个id编号，不要与自动刷新座位时的append混用
    # 获取预约历史信息,需要cookie:userid=2102210421;access_token=d810f72e23effcd671571dba9d9726df
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = get(
        url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/",
        headers={
            "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
            'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'})

    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).now().replace(microsecond=0)  # 注意在云上的时间是国际标准时间,把微秒去掉

    # 检查今日记录的时间，如"202207072021"
    for record in json.loads(res.content)['data']['list']:

        # 筛选出今天的记录 0-今日无记录，3-使用中，4-已使用，6-用户取消，8-已关闭，9-预约开始提醒
        if record['no'][:8]==str(now.date()).replace('-',''):
            # 这里return的值对应json.loads(res.content)['data']['list'][0]["status"]
            if record['statusName'] == '使用中':
                print('■■■今日最新状态   \t使用中,在馆')
                if INFORMED_WAY == 0:
                    inform_by_dingding('检测到人在馆')
                if INFORMED_WAY == 1:
                    inform_by_bark('检测到人在馆')
                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                return 3
            elif record['statusName'] == '已使用':
                print('■■■今日最新状态   \t已使用')
                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                return 4
            elif record['statusName'] == '用户取消':
                print('■■■今日最新状态   \t用户取消')
                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                return 6
            elif record['statusName'] == '已关闭':
                print('■■■今日最新状态   \t已关闭')
                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                return 8
            elif record['statusName'] == '预约开始提醒':
                print('■■■今日最新状态   \t预约中&未签到')
                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                return 9

    print('■■■今日无记录')
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    return 0

def get_now_seat(USERNAME=USERNAME):
    """
    当今天最新一条为'使用中'状态时,获取当前座位的id而不是座位号及房间id,int类型
    """
    # 注意这里会先查询历史记录，并向RESERVE_SEAT里append一个id编号，不要与自动刷新座位时的append混用
    # 获取预约历史信息,需要cookie:userid=2102210421;access_token=d810f72e23effcd671571dba9d9726df
    res = get(
        url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/",
        headers={
            "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
            'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'})

    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))  # 注意在云上的时间是国际标准时间
    now = now.now() + datetime.timedelta(microseconds=-now.microsecond)  ## 把微秒去掉

    # 检查今日记录的时间，如"202207072021"
    for record in json.loads(res.content)['data']['list']:

        # 筛选出今天的记录 0-今日无记录，3-使用中，4-已使用，6-用户取消，8-已关闭，9-预约开始提醒
        if record['no'][:8]==str(now.date()).replace('-',''):
            # 这里return的值对应json.loads(res.content)['data']['list'][0]["status"]
            if record['statusName'] == '使用中':
                return record['id'],record['spaceDetailInfo']["area"]

def cancel_reserve(USERNAME=USERNAME):
    """
    取消预约
    """
    # 注意这里会先查询历史记录，并向RESERVED_SEAT里append一个id编号，不要与自动刷新座位时的append混用
    # 获取预约历史信息,需要cookie:userid=2102210421;access_token=d810f72e23effcd671571dba9d9726df
    res = get(
        url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/",
        headers={
            "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
            'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'})
    if json.loads(res.content)['data']['list'][0]['statusName'] == '预约开始提醒':
        print('■■■预约状态   \t预约中&未签到')
        RESERVED_SEAT.append(json.loads(res.content)['data']['list'][0]['id'])
        # 取消预约
        res = post(
            url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/{RESERVED_SEAT[-1]}",
            headers={
                "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
                "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
                'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'},
            data={"access_token": req.cookies.get("access_token"), "userid": USERNAME, "_method": 'delete',
                  "id": RESERVED_SEAT[-1]})
        if json.loads(res.content)['status'] == 0:
            print('■■■取消预约   \t当日取消次数已达上限')
            if INFORMED_WAY == 0:
                inform_by_dingding('取消预约   \t当日取消次数已达上限')
            if INFORMED_WAY == 1:
                inform_by_bark('取消预约   \t当日取消次数已达上限')
                return 0
        elif json.loads(res.content)['status'] == 1:
            print('■■■取消预约   \t成功取消')
            if INFORMED_WAY == 0:
                inform_by_dingding('取消预约   \t成功取消')
            if INFORMED_WAY == 1:
                inform_by_bark('取消预约   \t成功取消')
                return 1
        else:
            print('■■■取消预约   \t取消预约失败：', json.loads(res.content))
            if INFORMED_WAY == 0:
                inform_by_dingding(f'取消预约   \t取消预约失败, {json.loads(res.content)}')
            if INFORMED_WAY == 1:
                inform_by_bark(f'取消预约   \t取消预约失败, {json.loads(res.content)}')
            return 0
    else:
        print('■■■取消预约   \t未预约或者预约超时，无需取消预约')
        if INFORMED_WAY == 0:
            inform_by_dingding('取消预约   \t未预约或者预约超时，无需取消预约')
        if INFORMED_WAY == 1:
            inform_by_bark('取消预约   \t未预约或者预约超时，无需取消预约')
        return 0

def checkIn():
    """
    签到-失效 中南大学和西建发送的报头一样
    """
    pass

def checkout(USERNAME):
    """
    签离,馆内签离
    """
    # 注意这里会先查询历史记录，并向RESERVED_SEAT里append一个id编号，不要与自动刷新座位时的append混用
    # 获取预约历史信息,需要cookie:userid=2102210421;access_token=d810f72e23effcd671571dba9d9726df
    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
    res = get(
        url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/",
        headers={
            "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
            "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
            'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'})
    if json.loads(res.content)['data']['list'][0]['statusName'] == '使用中':
        print('■■■当前状态   \t使用中')
        RESERVED_SEAT.append(json.loads(res.content)['data']['list'][0]['id'])
        # 取消预约
        res = post(
            url=f"http://rg.lib.xauat.edu.cn/api.php/profile/books/{RESERVED_SEAT[-1]}",
            headers={
                "Referer": "http://rg.lib.xauat.edu.cn/user/index/book",
                "User-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 Edg/99.0.4844.74",
                'Cookie': f'userid={USERNAME};access_token={req.cookies.get("access_token")}'},
            data={"access_token": req.cookies.get("access_token"), "userid": USERNAME, "_method": 'checkout',
                  "id": RESERVED_SEAT[-1]})
        if json.loads(res.content)['status'] == 1:
            print('■■■签离结果   \t成功签离')
            if INFORMED_WAY == 0:
                inform_by_dingding('签离结果   \t成功签离')
            if INFORMED_WAY == 1:
                inform_by_bark('签离结果   \t成功签离')
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
            return 1
        else:
            print('■■■签离结果   \t签离失败：', json.loads(res.content))
            if INFORMED_WAY == 0:
                inform_by_dingding(f'签离结果   \t签离失败, {json.loads(res.content)}')
            if INFORMED_WAY == 1:
                inform_by_bark(f'签离结果   \t签离失败, {json.loads(res.content)}')
            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
            return 0
    else:
        print('■■■签离结果   \t还未使用位置，无需签离')
        if INFORMED_WAY == 0:
            inform_by_dingding('签离结果   \t还未使用位置，无需签离')
        if INFORMED_WAY == 1:
            inform_by_bark('签离结果   \t还未使用位置，无需签离')
        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
        return 0

if __name__ == '__main__':



    IS_UTC=0

    AREA_ID_AND_NAME = {}
    SEAT_INFO_URL = []
    RESERVE_SEAT = []  # 可预约的所有座位列表，座位id,座位name,座位所在房间的编号,座位所在房间对应的segment
    RESERVE_SEAT_SORTED = []  # 对上面的座位进行排序
    RESERVED_SEAT = []  # 预约到的座位
    SEGMENT = []
    STATUS=''
    PRINT_NAME = ''
    PRINT_AREA_NAME = []
    VALID_OTHERS_ACCOUNT = {}  #筛选出的有效他人账号
    INVALID_OTHERS_ACCOUNT = {}  #筛选出的失效他人账号

    # 获取当前通知方式 0-钉钉 1-BARK
    INFORMED_WAY=get_inform_way()

    req = requests.session()
    if not login_in_1(USERNAME, PASSWORD):
        quit()

    while not RESERVED_SEAT:

        # 检查救场用户的可用性,过程中会将有效的用户放到VALID_OTHERS_ACCOUNT内，并返回有效账号的个数
        check_OTHERS_ACCOUNT_valid()

        # 登陆自己的帐号，如果自己账号未成功登陆就停止脚本
        if not login_in_1(USERNAME,PASSWORD):
            print( login_in_1(USERNAME,PASSWORD))
            quit()

        # 获取区域id信息，便于选择,仅作展示用，且只执行一次
        get_area_id()

        # 获取url信息，便于构造获取seat信息的url地址
        url_info()

        while COOKIE_STATUS() and not RESERVED_SEAT:

            # 以下为选座时，优先第一个房间的所有位置，其次是第二个房间的所有位置.....
            if SELECT_WAY == 1:
                for seat_info_url in SEAT_INFO_URL:
                    if COOKIE_STATUS() and not RESERVED_SEAT:
                        seat_info(seat_info_url)
                        if RESERVE_SEAT:
                            if COOKIE_STATUS():
                                reserve(USERNAME=USERNAME)
                                if not RESERVED_SEAT:
                                    RESERVE_SEAT = []
                                    RESERVE_SEAT_SORTED= []
                            else:
                                AREA_ID_AND_NAME = {}
                                SEAT_INFO_URL = []
                                RESERVE_SEAT = []  # 可预约的所有座位列表，座位id,座位name,座位所在房间的编号,座位所在房间对应的segment
                                RESERVE_SEAT_SORTED = []  # 对上面的座位进行排序
                                RESERVED_SEAT = []  # 预约到的座位
                                SEGMENT = []
                                STATUS = ''
                                PRINT_NAME = ''
                                PRINT_AREA_NAME = []
                                VALID_OTHERS_ACCOUNT = {}  # 筛选出的有效他人账号
                                INVALID_OTHERS_ACCOUNT = {}  # 筛选出的失效他人账号
                        ##################################################################################

            # 以下为选座时，优先第一个房间的一级位置，其次是第二个房间的一级位置，其次是第一个房间的二级位置，其次是第二个房间的二级位置.....
            if SELECT_WAY == 2:
                for seat_info_url in SEAT_INFO_URL:
                    if COOKIE_STATUS() and not RESERVED_SEAT:
                        seat_info(seat_info_url)
                if RESERVE_SEAT:
                    if COOKIE_STATUS():
                        reserve(USERNAME=USERNAME)
                        if not RESERVED_SEAT:
                            RESERVE_SEAT = []
                            RESERVE_SEAT_SORTED = []
                    else:
                        AREA_ID_AND_NAME = {}
                        SEAT_INFO_URL = []
                        RESERVE_SEAT = []  # 可预约的所有座位列表，座位id,座位name,座位所在房间的编号,座位所在房间对应的segment
                        RESERVE_SEAT_SORTED = []  # 对上面的座位进行排序
                        RESERVED_SEAT = []  # 预约到的座位
                        SEGMENT = []
                        STATUS = ''
                        PRINT_NAME = ''
                        PRINT_AREA_NAME = []
                        VALID_OTHERS_ACCOUNT = {}  # 筛选出的有效他人账号
                        INVALID_OTHERS_ACCOUNT = {}  # 筛选出的失效他人账号
                ########################################################################################################################

        if not COOKIE_STATUS():
            continue


    if RESERVED_SEAT:
        # 预约完成后立即检查自己账号今日还可取消预约的次数
        ##不可取消，立即发警告通知
        ##还剩一次，进行下面的步骤

        all_users = list(list(list(VALID_OTHERS_ACCOUNT.keys()).__reversed__()).__add__([USERNAME]).__reversed__())

        login_in_1(USERNAME,PASSWORD)

        if check_cancel_chance(USERNAME)==1 and len(all_users)>=2:

            for others_account_name,others_account_password in VALID_OTHERS_ACCOUNT.items():

                # 预约完成后等待25分钟再检查是否完成签到
                time.sleep(25*60)
                #检查自己的状态,return返回的，0-今日无记录，3-使用中，4-已使用，6-用户取消，8-已关闭，9-预约开始提醒
                #签到完成

                login_in_1(USERNAME,PASSWORD)

                if check_status() == 3:
                    # 检查所在房间是不是长期空房间
                    now_seat_id,now_area=get_now_seat(USERNAME)
                    # 是,更换座位;不是,不用管
                    if ALWAYS_SPARE_AREA:
                        if now_area==ALWAYS_SPARE_AREA:
                            checkout(USERNAME)
                            lastest_user_name=all_users[all_users.index(others_account_name)-1]
                            lastest_user_password=VALID_OTHERS_ACCOUNT[lastest_user_name]
                            login_in_1(lastest_user_name,lastest_user_password)
                            cancel_reserve(USERNAME=lastest_user_name)
                            login_in_1(USERNAME,PASSWORD)
                            reserve(USERNAME=USERNAME)
                            time.sleep(120)
                            now_seat_id, now_area = get_now_seat(USERNAME)
                            if check_status()==3 and now_area==RESERVED_SEAT[2]:
                                print('■■■成功完成座位的更换')
                                if INFORMED_WAY == 0:
                                    inform_by_dingding('成功完成座位的更换')
                                if INFORMED_WAY == 1:
                                    inform_by_bark('成功完成座位的更换')
                                print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                        else:
                            print('已通过选座机器选择了房间，脚本预约的房间将释放...')
                            if INFORMED_WAY == 0:
                                inform_by_dingding('已通过选座机器选择了房间，脚本预约的房间将释放...')
                            if INFORMED_WAY == 1:
                                inform_by_bark('已通过选座机器选择了房间，脚本预约的房间将释放...')
                            print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                    else:
                        print('您已经开启救援模式，但未填写ALWAYS_SPARE_AREA项！')
                #未签到
                elif check_status()==9:
                    # 将自己的账号取消预约
                    if cancel_reserve(USERNAME):
                        # 更换账号1，并进行通知
                        # 对-同一位置-进行预约，最好呢是重新发起预约请求，说不定有更好的位置，也避免了该座位恰好被人预约了，但因为写的像坨屎，无法实行
                        # 25分钟后再检查自己账号是否到馆
                        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                        print('■■■开始救场')
                        if INFORMED_WAY == 0:
                            inform_by_dingding('开始救场')
                        if INFORMED_WAY == 1:
                            inform_by_bark('开始救场')
                        login_in_1(others_account_name,others_account_password)
                        reserve(USERNAME=others_account_name)
                        print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                elif check_status() == 6:
                    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                    print('■■■开始救场')
                    if INFORMED_WAY == 0:
                        inform_by_dingding('开始救场')
                    if INFORMED_WAY == 1:
                        inform_by_bark('开始救场')
                    last_user_name = all_users[all_users.index(others_account_name) - 1]
                    last_user_password = VALID_OTHERS_ACCOUNT[last_user_name]
                    login_in_1(last_user_name, last_user_password)
                    cancel_reserve(USERNAME=last_user_name)
                    login_in_1(others_account_name,others_account_password)
                    reserve(USERNAME=others_account_name)
                    print("■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■")
                ####关于如何检查自己是否到馆，可以选定某个长期有空位的房间（最好永远没有坐满的那种），自己进馆后到机器上刷卡预约那个空房间的任一个位置
                ####再去检查自己的账号是否处于 今日-那个房间-已使用 状态
                ########若还没到馆，则更换另一个账号重复上述步骤
                ############若在不停重复过程中到馆了，那么登陆使用到的最后一个账号，在其25分钟时刻，取消该座位，登陆自己的账号-签离-预约这个座位，并进行通知

                ############若账号用完了还没到，那么在使用到的最后一个账号最后几分钟，取消其预约，并进行通知





# PC端抓包：访问不同链接时，cookie内容不完全相同
# 第一次访问 -随便哪个页面http://rg.lib.xauat.edu.cn/web/seat3?area=8&segment=1315641&day=2122-3-16&startTime=19:21&endTime=22:11
#           -不需要携带cookie
#           -返回   'Set-Cookie':'PHPSESSID=kv8ab5f268pp5mjld6hmtfuus4; path=/; HttpOnly'
# 获取验证码 -http://rg.lib.xauat.edu.cn/api.php/check
#           -需要携带cookie形式1   'Cookie':'PHPSESSID=kv8ab5f268pp5mjld6hmtfuus4; path=/; HttpOnly'
#           -需要携带cookie形式2   'Cookie':'PHPSESSID=kv8ab5f268pp5mjld6hmtfuus4'
#           -不返回cookie，即cookie维持不变
# 登录      -http://rg.lib.xauat.edu.cn/api.php/login
#           -需要携带cookie形式1   'Cookie':'PHPSESSID=kv8ab5f268pp5mjld6hmtfuus4; path=/; HttpOnly'
#           -需要携带cookie形式2   'Cookie':'PHPSESSID=kv8ab5f268pp5mjld6hmtfuus4'
#           -返回   'Set-Cookie': 'userid=2112211396; path=/, user_name=%E9%99%88%E9%97%AF; path=/, access_token=c8d1e9d1e374fe442bc65b2167cd898e; path=/, expire=2122-13-15+19%3A13%3A11; path=/'
# 延长cookie和预约 -"http://rg.lib.xauat.edu.cn/api.php/spaces/3787/book"
#                 -需要携带cookie：'Cookie': 'PHPSESSID=nivivdo1ga13s6q2mp8j93ja11;redirect_url=%2Fweb%2Fseat2%2Farea%2F4%2Fday%2F2122-3-15; userid=2112211396;user_name=%E9%99%88%E9%97%AF;access_token=aa61ee9f81dec12734ab8649156688c9;expire=2122-13-16+19%3A57%3A55'
#                 -需要携带cookie：'Cookie': 'PHPSESSID=nivivdo1ga13s6q2mp8j93ja11; userid=2112211396;user_name=%E9%99%88%E9%97%AF;access_token=aa61ee9f81dec12734ab8649156688c9;expire=2122-13-16+19%3A57%3A55'
#                 -返回：'Set-Cookie': 'expire=2122-13-16+19%3A57%3A55; path=/'
# 获取座位信息 -http://rg.lib.xauat.edu.cn/api.php/check
#             -需要携带cookie：'Cookie': 'PHPSESSID=tn9dfvckr33aiisv5cddmdaeu4; userid=2112211396;user_name=%E9%99%88%E9%97%AF;access_token=aed11367dd16acc7d1ba84dfd84e4b86;expire=2122-13-16+11%3A19%3A11'
#            -不返回cookie，即cookie维持不变
