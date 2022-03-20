from cacheout import Cache
from aiocqhttp import CQHttp
import re
import time
import datetime
import random
from aiocqhttp.message import MessageSegment, Message

bot = CQHttp(enable_http_post=False)

cache = Cache()
calllimit = Cache()
shield = Cache()

"""
PP 2019/08/05 21:41:45
/callme
MalPicBot 2019/08/05 21:43:27
缺少参数，格式/callme 数字[s,m,h]
PP 2019/08/05 21:43:41
/callme 30min
MalPicBot 2019/08/05 21:44:37
已经加入等候列表，现在有：
马雷丕(还能等待30min) 
正在等待联机
MalayP 2019/08/05 21:45:12
/call
MalPicBot 2019/08/05 21:45:53
@PP ！@MalayP 正在找人联机！
PP 2019/08/05 21:46:18
/leave
MalayP 2019/08/05 21:46:36
/call
MalPicBot 2019/08/05 21:47:07
现在没人联机了，自己创建队伍吧
"""

sign = {
    "s": 1,
    "sec": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 3600*24,
    "day": 3600*24,
    "days": 3600*24
}

def defaultvalue(value, default):
    return value or default

def stringlimit(text, length=9):
    return text if len(text) <= length else f'{text[:length]}......'

def test(i):
    return datetime.datetime.fromtimestamp(i['now'] + i['sec'])

def smarttime(timestamp):
    unit = {"天": 3600 * 24, "小时": 3600, "分钟": 60, "秒": 1}
    num = timestamp
    num1 = 0
    result = {}
    for i in unit:
        num1 = num
        num = num % unit[i]
        result[i] = (num1 - num) / unit[i]
    return result

async def callme(context):
    splited = context["message"].split(" ")
    if len(splited) < 2:
        return "缺少参数，格式/callme 数字[s,m,h]"
    matched = re.findall(r"([0-9]{1,2})([a-zA-Z]{1,6})", splited[1])
    if not matched:
        return "正则匹配失败, 你可能使用了错误的时间格式."
    signedMap = {sign: number for number, sign in matched}
    try:
        sec = sum(sign[i] * int(signedMap[i]) for i in signedMap)
    except KeyError:
        return "拼写错误的时间单位."

    if context.get("group_id"):
        if not cache.get(context.get("group_id")):
            cache.set(context.get("group_id"), type(
                str(context.get("group_id")), (Cache,), {})())

        cache.get(context.get("group_id")).set(
            context['user_id'],
            {
                "user_id": context['user_id'],
                "card": context['sender']['card']
                or context['sender']['nickname']
                or context['sender']['id'],
                "sec": sec,
                "now": time.time(),
            },
            ttl=sec,
        )

        return """已加入等候列表, 现有:
{0}
正在等待联机.""".format("\n".join(["{card}(还能等待{time})".format(
            card=stringlimit(i['card']),
            time="".join(["{v}{k}".format(v=round(v), k=k) for k, v in filter(lambda x: bool(x[1]), smarttime(
                (datetime.datetime.fromtimestamp(i['now'] + i['sec']) - datetime.datetime.now()).total_seconds()).items())])
        ) for i in cache.get(context.get("group_id")).values()]))
    else:
        return "本指令不支持私人聊天."

async def call(context):
    if not context.get("group_id"):
        return "本指令不支持私人聊天."
    if not cache.get(context.get("group_id")):
        cache.set(context.get("group_id"), type(
            str(context.get("group_id")), (Cache,), {})())

    if not list(cache.get(context.get("group_id")).values()):
        return "现在没人联机了, 自己发起吧."

    shouldBe = True
    tick = 0
    while shouldBe and tick < 8:
        result = random.choice(
            list(cache.get(context.get("group_id")).values()))
        if result['user_id'] != context['user_id']:
            shouldBe = False
        tick += 1
    if tick >= 8 and shouldBe:
        return "错误: 等待列表中可能只有你一个人吧= ="
    return "".join([
        str(MessageSegment.at(result['user_id'])),
        ", ",
        str(MessageSegment.at(context['user_id'])),
        " 找你联机!"
    ])

async def play_list(context):
    if not context.get("group_id"):
        return "本指令不支持私人聊天."
    if not cache.get(context.get("group_id")):
        cache.set(context.get("group_id"), type(
            str(context.get("group_id")), (Cache,), {})())

    if not list(cache.get(context.get("group_id")).values()):
        return "现在没人联机了, 自己发起吧."

    return "\n".join([
        "现有:",
        "\n".join([
            "{card}(还能等待{time})".format(
                card=stringlimit(i['card']),
                time="".join(["{v}{k}".format(v=round(v), k=k) for k, v in filter(lambda x: bool(x[1]), smarttime(
                    (datetime.datetime.fromtimestamp(i['now'] + i['sec']) - datetime.datetime.now()).total_seconds()).items())])
            ) for i in cache.get(context.get("group_id")).values()
        ]),

        "正在等待联机..."
    ])

async def leave(context):
    if not context.get("group_id"):
        return "本指令不支持私人聊天."
    if not cache.get(context.get("group_id")):
        cache.set(context.get("group_id"), type(
            str(context.get("group_id")), (Cache,), {})())

    if not cache.get(context.get("group_id")).get(context['user_id']):
        return "没有查找到你的联机请求..."

    cache.get(context.get("group_id")).delete(context['user_id'])
    return "你已撤销你之前的联机请求."

async def callall(context):
    if not context.get("group_id"):
        return "本指令不支持私人聊天."
    wait_secs = 180
    if not calllimit.get(context.get("group_id")):
        calllimit.set(context.get("group_id"), {
            "time": time.time()
        }, ttl=wait_secs)
    else:
        return "本群暂时无法使用callall指令, 预计该指令将在{time}后可用.".format(
            time="".join(["{v}{k}".format(v=round(v), k=k) for k, v in filter(lambda x: bool(x[1]), smarttime(
                (datetime.datetime.fromtimestamp(calllimit.get(context.get("group_id"))['time'] + wait_secs) - datetime.datetime.now()).total_seconds()).items())])
        )

    if not cache.get(context.get("group_id")):
        return "该群内无任何请求被发出过."
    for i in cache.get(context.get("group_id")).keys():
        if shield.get("{group}_{user}".format(group=context.get("group_id"), user=i)):
            continue
        await bot.send_private_msg(
            user_id=i,
            message="在群 {group} 中, {sender_name}({sender_qq}) 向你发送了联机申请.".format(
                group=(
                    await bot._get_group_info(group_id=context.get("group_id"))
                )['group_name'],
                sender_name=context['sender']['card']
                or context['sender']['nickname']
                or context['sender']['id'],
                sender_qq=str(context['user_id']),
            ),
        )

    return "已完成."

def sec_summon(text):
    matched = re.findall(r"([0-9]{1,2})([a-zA-Z]{1,6})", text)
    if not matched:
        return False
    signedMap = {sign: number for number, sign in matched}
    try:
        sec = sum(sign[i] * int(signedMap[i]) for i in signedMap)
    except KeyError:
        return False
    return sec

async def shielder(context):
    group = context.get("group_id")
    wait = "2m"
    if not group or len(context['message'].split(" ")) >= 2:
        splited = context['message'].split(" ")
        needupdate = {
            "group": group,
            "wait": wait
        }
        needupdate.update({i.split("=")[0]: i.split("=")[1] for i in splited[1:]})
        group = needupdate['group']
        wait = needupdate['wait']
    try:
        shield.set("{group}_{user}".format(group=group, user=context['user_id']), {
            "time": time.time()
        }, ttl=sec_summon(wait))
    except ValueError:
        return "你给出了一个错误的时间值."
    return "屏蔽操作已对群 {group} 生效,在 {time} 之内你将不会被该群群员使用callall时被我吵醒.".format(
        group=group,
        time="".join(["{v}{k}".format(v=round(v), k=k) for k, v in filter(lambda x: bool(x[1]), smarttime(sec_summon(wait)).items())])
    )

async def unshield(context):
    group = context.get("group_id")
    if not group:
        splited = context['message'].split(" ")
        needupdate = {
            "group": group
        }
        needupdate.update({i.split("=")[0]: i.split("=")[1] for i in splited[1:]})
        if not needupdate['group']:
            return "无法确定你所指示的需要进行屏蔽操作的群."
        group = needupdate['group']
    result = shield.get("{group}_{user}".format(group=group, user=context['user_id']))
    if not result:
        return "没有查询到你关于该群的屏蔽记录"
    shield.delete("{group}_{user}".format(group=group, user=context['user_id']))
    return "已撤销你关于该群的callall屏蔽."
    
commands = {
    "callme": callme,
    "call": call,
    "play_list": play_list,
    "leave": leave,
    "callall": callall,
    "shield": shielder,
    "unshield": unshield
}


@bot.on_message()
async def handle_msg(context):
    if (
        context["message"].split(" ")[0][0] == "/"
        and context["message"].split(" ")[0][1:] in commands
    ):
        return {"reply": await commands[context["message"].split(" ")[0][1:]](context), 'at_sender': False}

bot.run("localhost", 8695)
