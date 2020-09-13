# -*- coding: UTF-8 -*-
import re
import requests
from contextlib import closing
import time

usn = int(input('本科生学号：'))
psd = input('密码：')
ids = 0
seId = 0

headers = {
    'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
ss = requests.Session()
loginData = {
    'username': usn,
    'password': psd,
    'encodedPassword': '',
    'session_locale': 'zh_CN'
}
loginPost = ss.post('http://us.nwpu.edu.cn/eams/login.action',
                    data=loginData, headers=headers)
loginRes = loginPost.text

if '密码错误' in loginRes:
    input('密码错误，退出')
    exit()
elif '账户不存在' in loginRes:
    input('账户不存在')
    exit()
elif '验证码不正确' in loginRes:
    input('请更换网络环境并稍等几分钟')
    exit()
elif '尊敬的' not in loginRes:
    input('未知的登录错误')
    exit()
print('登录成功！用户:', re.search(r'尊敬的(.+?)用户', loginRes, flags=re.S).group(1))

idsGet = ss.get('http://us.nwpu.edu.cn/eams/courseTableForStd.action',
                headers=headers)
idsRe = re.search(r'addInput\(form,\"ids\",\"(\d+)\"\)',
                  idsGet.text, flags=re.S)
if idsRe == None:
    input('ids 获取错误')
    exit()
ids = int(idsRe.group(1))
print('ids 获取成功为:', ids)

sIdData = {
    'tagId': 'semesterBar15920393881Semester',
    'dataType': 'semesterCalendar',
    'empty': 'true'
}

sIdPost = ss.post('http://us.nwpu.edu.cn/eams/dataQuery.action',
                  data=sIdData, headers=headers)

sIdTotal = []
total = re.findall(
    r'id:(\d+),schoolYear:\"(\d+-\d+)\",name:\"(.+)\"', sIdPost.text)
for i in range(len(total)):
    sIdTotal.append([total[i][0], total[i][1], total[i][2]])
if len(sIdTotal) == 0:
    input('学期id获取失败！')
    exit()
print('------学期信息------')
for item in sIdTotal:
    print('%s %s学期: %s' % (item[1], item[2], item[0]))
inp = input('你需要查询的具体学期的id是?(本学期可能是 %s,假如是的话就直接回车):' %
            sIdTotal[len(sIdTotal)-2][0])
if inp == '':
    seId = int(sIdTotal[len(sIdTotal)-2][0])
else:
    seId = int(inp)

detailList = []
baseList = []
# =========
lteacher = ""  # 以下为"last"的意思
lclass = ""
lroom = ""
l01week = ""
lstartendweek = []

tstartweek = -1
ttday = -1
ttstartNode = -1
ttstep = 0
firstornot = True
skipornot = False  # 当activity中有 -1 值的时候，可能说明这个课情况特殊（比如说是停课状态），就直接skip

finalData = {
    'ignoreHead': '1',
    'setting.kind': 'std',
    'startWeek': '1',
    'project.id': '1',
    'semester.id': seId,
    'ids': ids
}
finalPost = ss.post('http://us.nwpu.edu.cn/eams/courseTableForStd!courseTable.action',
                    data=finalData, headers=headers)
response = finalPost.text
if('var activity=null;' not in response):
    input('课表标识没有找到')
    exit()
res = str(re.findall('var activity=null;[\\w\\W]*(?=table0.marshalTable)', response,
                     flags=re.S)).replace('\\r\\n\\t\\t\\t', '\n').lstrip('[\'').rstrip('\\r\\n\\t\']')
foundResults = re.findall(r'.+?;', res)
for text in foundResults:
    if text[0:3] == 'var' or text[0:6] == 'table0':
        continue
    elif text[0:8] == 'activity':  # 先添加“上”课
        if len(lstartendweek) != 0:
            for i in range(1, len(lstartendweek)+1, 2):
                perfectlroom = re.sub('\\[教学[东西]楼[A-Za-z]座\\]', '', lroom)
                perfectlroom = re.sub(
                    '\\[体育场地\\][A-Za-z]\\d+?', '', perfectlroom)
                perfectlroom = re.sub('\\[实验大楼\\]', '', perfectlroom)
                detailList.append([len(baseList)-1, ttday, perfectlroom, lteacher,
                                   lstartendweek[i-1], lstartendweek[i], ttstartNode, ttstep])

        if ',\"-1\",' in text:  # 状态可能有问题
            skipornot = True
            continue
        else:
            skipornot == False

        firstornot = True  # 确保下一行的index是本activity的first
        matchRs = re.search('TaskActivity\\(.+?,\"(.*?)\",.+?,\"(.+?)\",.+?,\"(.+?)\",\"(.+)\"', text)
        if lclass != matchRs.group(2):  # 课程不同
            lstartendweek.clear()
            lteacher = matchRs.group(1)
            lclass = matchRs.group(2)
            lroom = matchRs.group(3)
            l01week = matchRs.group(4)

            for i in range(len(l01week)):  # 从01状态码转为连续week情景（一前一后为start、endweek）
                if (l01week[i] == '0' and tstartweek == -1):
                    continue
                elif (l01week[i] == '1' and tstartweek == -1):
                    tstartweek = i
                    lstartendweek.append(i)
                elif (l01week[i] == '1' and tstartweek != -1):
                    continue
                elif (l01week[i] == '0' and tstartweek != -1):
                    tstartweek = -1
                    lstartendweek.append(i - 1)

            baseList.append([len(baseList), lclass])
        else:  # 课程同，但其他的出现了不同，就要写detail课程同，但其他的出现了不同，就要写detail
            lstartendweek.clear()
            lteacher = matchRs.group(1)
            lclass = matchRs.group(2)
            lroom = matchRs.group(3)
            l01week = matchRs.group(4)

            for i in range(len(l01week)):  # 从01状态码转为连续week情景（一前一后为start、endweek）
                if (l01week[i] == '0' and tstartweek == -1):
                    continue
                elif (l01week[i] == '1' and tstartweek == -1):
                    tstartweek = i
                    lstartendweek.append(i)
                elif (l01week[i] == '1' and tstartweek != -1):
                    continue
                elif (l01week[i] == '0' and tstartweek != -1):
                    tstartweek = -1
                    lstartendweek.append(i - 1)
    elif text[0:5] == 'index':
        if skipornot:
            continue

        if firstornot:
            matchRs = re.search('=(\\d+)\\*unitCount\\+(\\d+);', text)
            ttday = int(matchRs.group(1))+1
            ttstartNode = int(matchRs.group(2))+1
            ttstep = 1
            firstornot = False
        else:
            ttstep += 1

if len(lstartendweek) != 0:
    for i in range(1, len(lstartendweek)+1, 2):
        perfectlroom = re.sub('\\[教学[东西]楼[A-Za-z]座\\]', '', lroom)
        perfectlroom = re.sub('\\[体育场地\\][A-Za-z]\\d+?', '', perfectlroom)
        perfectlroom = re.sub('\\[实验大楼\\]', '', perfectlroom)
        detailList.append([len(baseList)-1, ttday, perfectlroom, lteacher,
                           lstartendweek[i-1], lstartendweek[i], ttstartNode, ttstep])

print('\n总共有 %d 课程:\n--------' % len(baseList))
dayString = '空一二三四五六日'
i4detail = 0
fileout = '[%s] %d seId:%d\n--------' % (
    time.asctime(time.localtime(time.time())), usn, seId)
for base in baseList:
    deindex = 1
    print('\n%02d: %s' % (int(base[0])+1, base[1]))
    fileout += '\n\n%02d: %s' % (int(base[0])+1, base[1])
    while i4detail < len(detailList) and detailList[i4detail][0] == base[0]:
        cur = detailList[i4detail]
        print('»%d. 第%s-%s周 周%s %s-%d 节 @%s by %s' % (deindex,
                                                      cur[4], cur[5], dayString[cur[1]], cur[6], int(cur[6])+1, cur[2], cur[3]))
        fileout += '\n»%d. 第%s-%s周 周%s %s-%d 节 @%s by %s' % (
            deindex, cur[4], cur[5], dayString[cur[1]], cur[6], int(cur[6])+1, cur[2], cur[3])
        deindex += 1
        i4detail += 1

with open(('schedule.txt'), 'w', encoding='utf-8') as f:
    f.write(fileout)
input('课表信息已经写入 schedule.txt')
