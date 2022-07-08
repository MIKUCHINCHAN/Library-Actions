# Library-Actions

- 图书馆自助预约程序：[MIKUCHINCHAN/Library-Actions](https://github.com/MIKUCHINCHAN/Library-Actions) 的 Github Action 版


- 该脚本适合于**西安建筑科技大学(XAUAT)**、**中南大学(CSU)等**，除西建外的其余高校可将脚本中域名改为自己学校进行使用。
- 利用 Github Action 的 [Secrets](https://docs.github.com/cn/actions/reference/encrypted-Secrets) 加密储存所有配置信息，任何人都无法从项目仓库中直接读取这些敏感信息。
- 支持的通知方式：**Bark**、**钉钉机器人**；暂不支持的通知方式：Serverchan-Turbo、pushplus、喵推送、QQ机器人（go-cqhttp）

- 目前**签到**无法使用，可能是因为在预约网站上暴露出来的签到接口被设置为不能进行签到，而真正的签到接口并没有暴露出来，也可能是因为需要在图书馆局域网操作（@founder-yu的猜想，但我认为并不是），但仍保留了相关代码，如有人有解决方法，请与我联系。

- 如脚本运行有任何问题，请先参考文末[常见问题](#常见问题)；如实在无法解决，请在本仓库直接发issue描述你的问题。**不留联系方式，不接受私下交流。**



### Step1 Fork本仓库

- 点击右上角的**Fork**，将本项目复制到自己的仓库
- 稍等片刻，将自动跳转至新建的仓库。

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/1.png)

### Step2 配置个人信息参数

- 在新建的仓库页面，依次点开`Setting`，进入项目仓库设置页面

- 在左方侧边栏点击选项 `Environments`，点击右上角按钮 `New environment` 创建用于存放用户配置的 Environment，命名为 `Library_CONFIG`。

- 进入新建的 Environment ，在 “Environment Secrets” 一栏中点击 `Add Secret` 按钮，根据需要新建下列的 Secret，并填写对应 Value 值：

  <details>
  <summary><b>基本参数</b></summary>

  - `USERNAME`：学号，e.g.`1902222334`

  - `PASSWORD`：图书馆账号密码，e.g.`WFAWCWAdcaw1!`

  - `AREA_ID`：想要预约的房间编号，写在方括号中，若想添加其他的或者不知道自己学校的房间编号，可以先随便写如[8,10]运行脚本，之后会显示出其他房间的编号，再自行添加或者更改，同时优先考虑高楼层，且房间中优先考虑大座位号，e.g.`[10,8]`

  - `BANNED_SEAT`（无需求可跳过）：绝对不要的座位号，对于AREA_ID中的房间，不要求必须给绝对不要的座位号，可以一个房间给一个不给，同时对于不在AREA_ID中的房间，在这里也可以给绝对不要的座位号，格式为{房间1号ID:[座位号1,座位号2,座位号3,.....]，房间2号ID:...,...}，e.g.`{8:[1,2,3,4,5,6],10:[1,2,3,4]}`

  - 

  - `SELECT_WAY`（无需求可跳过）：筛选座位的方式，可选的为1和2，e.g.`1`

    - 方式1，优先级在于房间：优先`AREA_ID`中第一个房间的所有位置，其次为`AREA_ID`中第二个房间的所有位置，且同一房间中的大号优先
    - 方式2，优先级在于座位号：一级优先的是某几个房间的某些位置，二级优先为某几个房间的另外某些位置……

  - `OK_SEAT`（无需求可跳过，若SELECT_WAY=2则该项必填）： 除了BANNED_SEAT以外座位号的倾向，即一个房间中哪些位置比较喜欢 

    - 当SELECT_WAY为1时，无需填写

    - 当SELECT_WAY为2时，需填写房间和座位号的排序，房间ID对应的列表内，越靠前的列表越是倾向（倾向分级），如{8:[[43,44,],[57],[31]],10:[[1,2],[4]]} ，这里的优先级是 8号房间的43号和44号>10号房间的1号和2号>8号房间的57号>10号房间的4号>8号房间的31号>8号房间的剩余号码>10号房间的剩余号码，e.g.`{8:[[43,44,45,46,47,48,49,50,51,52,53,54,59,60,61,64,],[57,58],[31,32,33,34,35,36,37,38,39,40,41,42]],10:[[1,2,3],[1,2,3]]} `

      > - 若AREA_ID中的房间顺序与此处相矛盾，那么以此处为准
      >
      > - 从python3.6开始，dict的插入变为有序，即字典整体变的有序；而之前的版本，比如python2.7，对于字典的插入是乱序的，即插入a,b,c，返回结果顺序可能是a,c,b。

  - `OTHERS_ACCOUNT_USERNAME_1`（无需求可跳过）： 其他人的账号，该项可以重复，即还可以有`OTHERS_ACCOUNT_USERNAME_2`、`OTHERS_ACCOUNT_USERNAME_3`等，若填写则代表开启**场外救援模式**，即按常规预约了30分钟内必须通过闸机进行签到，但可以通过在预约后第25分钟时，若自己账号今日还没取消过预约，那么可以取消一次，同时登陆其他账号预约同一个座位，当到第25分钟时，重复上述步骤….当自己在距离第一次预约25分钟后到馆时，可以直接去馆内预约机器上手动预约`ALWAYS_SPARE_AREA`房间的任意一个位置，该座位只用来检测人是否在馆内，之后人可以去之前预约到座位，其他不用管，脚本会自动将其他账号预约到的那个位置转到自己的账号上，e.g.`1114141515 `

  - `OTHERS_ACCOUNT_PASSWORD_1`（无需求可跳过）： 其他人账号的密码，与`OTHERS_ACCOUNT_USERNAME_1`搭配，该项可以重复，即还可以有`OTHERS_ACCOUNT_PASSWORD_2`、`OTHERS_ACCOUNT_PASSWORD_3`等，e.g.`fesfsec2aw! `

  - `ALWAYS_SPARE_AREA`（无需求可跳过，若开启了救援模式则此项必填）： 填写一个总是坐不满的房间ID，e.g.`7`

  </details>

  <details>
  <summary><b>推送服务（可选）</b></summary>


  目前支持的推送方式：

  - Bark
  - 钉钉机器人

  需要使用哪一种方式推送，创建该方式对应的 Secret 即可。

  可以同时推送多个渠道，只需额外创建这些推送方式对应的 Secret 即可。

  如不创建这些推送方式对应的 Secret，则不会推送打卡结果通知。

  <details>
  <summary><b>Bark</b></summary>
  - `BARK_TOKEN` （可选）：填写自己 Bark 的推送 URL，e.g.`https://api.day.app/thisisatoken`

    > 形如 `https://api.day.app/thisisatoken`，用于 Bark 推送打卡结果的通知；**请注意不要以斜杠结尾。**
    >
    > 为避免输入错误，建议从 Bark 客户端直接复制。

  </details>

  <details>
  <summary><b>钉钉机器人</b></summary>
  - `DD_BOT_ACCESS_TOKEN`（可选）：钉钉机器人推送 Token，填写机器人的 Webhook 地址中的 token。只需 `https://oapi.dingtalk.com/robot/send?access_token=XXX` 等于=符号后面的XXX即可，e.g.`WFAWCWAdcaw1!`

  - `DD_BOT_SECRET`（可选）：钉钉机器人推送SECRET，[官方文档](https://developers.dingtalk.com/document/app/custom-robot-access)，e.g.`WFAWCWAdcaw1!`

    > 如需配置钉钉机器人，上述的 `DD_BOT_ACCESS_TOKEN` 和 `DD_BOT_SECRET` 两条 Secrect 都需创建。

  </details>

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/2.png)

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/3.png)

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/4.png)

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/5.png)

### Step3 配置脚本运行时间(可选，如果没有定时预约座位需求的可以跳过这一步)

脚本的触发运行时间由项目仓库内`.github/workflows`的两个 Workflow 文件配置：

- `Library.yml`
  - 对应脚本`main.py`

  - 默认没有开启定时预约功能，若开启的话，默认是每天北京时间08:01，因为是githun的云执行，所以时间不准，需要自己考虑可能延时一个小时或者半个小时

如果需要修改脚本的运行时间：

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/6.png)

- 点击页面上方选项 `Code`，回到项目仓库主页。

- 点击文件夹`.github/workflows`，修改所需要的 Workflow 文件。

  - 点击`Library.yml`，进入文件预览。

  - 点击预览界面右上方笔的图标，进入编辑界面。

  - 将红框中最前面的`#`去掉，只去掉`#`，不要多去掉空格，同时根据自己的打卡时间需要，修改代码中的 cron 表达式。

    ![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/7.png)

    > **定时注意事项：**
    >
    > - Github Actions 用的是世界标准时间（UTC），北京时间（UTC+8）转换为世界标准时需要减去8小时。
    > - Github Action 执行计划任务需要排队，脚本并不会准时运行，大概会延迟1h左右，请注意规划时间。
  
- 修改完成后，点击页面右侧绿色按钮 `Start commit`，然后点击绿色按钮 `Commit changes`。

  ![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/8.png)


### Step4 手动测试脚本运行

- 点击页面上方选项 `Actions`，进入 Github Actions 配置页面。

- 左侧边栏点击需要测试的脚本：

  - `Library`：对应脚本“`main.py`”。

- 在未自行打卡的打卡时段，点击右侧按钮 `Run workflow`，再次点击绿色按钮 `Run workflow`。

- 等待一定时间后刷新页面（预约座位完成，测试的时候可以选择空位多的房间，这样很快就能看到测试结果了）。

- 2如无意外，座位预约将完成；如果你正确配置了 PUSH_TOKEN，应同时在2分钟内收到消息推送。

- 如果出现以下情况：

  - 脚本运行完成了但2分钟后推送说仍未预约到座位。
  - Github Actions 界面最新的 workflow run `WZXY_HealthCheck` 状态为红色错误。
  - 以及其他错误情况。

  请在Github Actions 配置界面中，打开最新的 Workflow run `mian`，查看错误日志，并检查自己的参数配置是否正确。

![1](https://github.com/MIKUCHINCHAN/Library-Actions/blob/main/pic/9.png)



 

<details>
<summary><b>常见问题</b></summary>

- 打卡不准时？
  - Github Action服务器使用的时间是UTC，设置定时时请注意转换为北京时间（UTC+8）。
  - Github Action执行计划任务需要排队，并不会准时运行脚本，大概会延迟1h左右，请注意规划时间。
- 需要其他推送通知渠道？
  - 请提 issue 或参考代码自行实现。
- 其他问题？
  - 欢迎提 issue。

</details>

<details>
<summary><b>XAUAT图书馆的房间名字和编号对照表</b></summary>

```
id-3	雁塔图书馆-二楼-南自修区
id-6	雁塔图书馆-二楼-学术文库自修
id-7	雁塔图书馆-三楼-南自修区
id-8	雁塔图书馆-三楼-移动设备自修区
id-14	雁塔图书馆-三楼-东自修区
id-9	雁塔图书馆-四楼-南自修区 
id-10	雁塔图书馆-四楼-移动设备自修区
id-15	雁塔图书馆-四楼-东自修区
id-16	雁塔图书馆-四楼-西自修区
id-12	雁塔图书馆-一楼研讨间-会议室2(2-20人)
id-13	雁塔图书馆-一楼研讨间-会议室3(2-20人)
id-32	草堂图书馆-一楼-考研专区
id-21	草堂图书馆-二楼-A区
id-22	草堂图书馆-二楼-D区
id-23	草堂图书馆-三楼-A区
id-24	草堂图书馆-三楼-B区
id-25	草堂图书馆-三楼-C区
id-26	草堂图书馆-三楼-D区
id-27	草堂图书馆-四楼-A区
id-28	草堂图书馆-四楼-B区
id-29	草堂图书馆-四楼-C区
id-30	草堂图书馆-四楼-D区
```

</details>

<details>
<summary><b>更新日志</b></summary>

- 2022.07.06 正式发布

</details>

<details>
<summary><b>Todo</b></summary>

- 解耦推送模块
- 用PYQT做一个EXE的可视化界面

</details>

<details>
<summary><b>参考/致谢</b></summary>

- [jimlee2002/Actions-WoZaiXiaoYuanPuncher](https://github.com/jimlee2002/Actions-WoZaiXiaoYuanPuncher) ，参考了其代码中的多种通知方式以及借鉴了其README.md文件的书写格式。


- [founder-yu/CSU-Library](https://github.com/founder-yu/CSU-Library)，参考了其签到的代码，但结果是没效果、没做出来。

</details>

<details>
<summary><b>声明</b></summary>

- 本项目仅供编程学习/个人使用，请遵守Apache-2.0 License开源项目授权协议.
- 请在国家法律法规和校方相关原则下使用。


- 开发者不对任何下载者和使用者的任何行为负责。

- 程序使用的所有信息均利用 Github 的 [Secrets](https://docs.github.com/cn/actions/reference/encrypted-Secrets) 加密储存。

</details>

