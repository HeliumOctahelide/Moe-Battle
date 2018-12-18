#-*-coding:utf-8-*-
# NGAID：_江天万里霜_
# 创建时间：2018/11/27
# 本程序依赖下列的包：
import requests
import configparser
import time
import re, json
import os
from bs4 import BeautifulSoup
import langconv
# 感谢csdz提供的繁简转换和Canon__提供的获取泥潭cookies方法。


# 全局定义
my_cookies = ''
too_young_users = []
VALID_INPUT = ['1','2','3','4','q','w','e','r','a','s','d','f','z','x','c','v']

conf = configparser.ConfigParser()
conf.read('config.ini', encoding='utf-8-sig')

def tradition2simple(line):
    # 将繁体转换成简体
    line = langconv.Converter('zh-hans').convert(line)
    return line

def set_cookies():
    # NGA的cookies经过了setcookie，requests得到的cookies和浏览器中的cookies不一致，直接访问的话会403。因此先要做一个cookies供requests使用。
    req = requests.get('https://bbs.nga.cn/read.php?tid=11451419')
    j = req.cookies.get_dict()
    k = int(j['lastvisit'])-1
    cookies_ = {'guestJs': str(k)}
    requests.utils.add_dict_to_cookiejar(req.cookies, cookies_)
    return req.cookies

def get_pages():   # 读取指定的投票专楼中特定的页码，并保存为vote.json
    print("请输入你要计票的帖子ID。例：11451419")
    try:
        postid = input()
        int(postid)
        basic_url = 'https://bbs.nga.cn/read.php?tid={}'.format(postid)
    except:
        print(">>错误<<：请正确地输入一个帖子ID。")
        input()
        exit()

    print("请输入你要计票的页数。例如输入>>12,16<<表示你计票的页数是12,13,14,15,16")
    try:
        left,right = list(map(int,input().split(',')))
    except:
        print(">>错误<<：请正确地输入两个页码。")
        input()
        exit()

    all_comments = []
    for page in range(left, right+1):
        url = basic_url + '&page={}'.format(page)
        print("正在读取第{}页".format(page))
        for i in range(5):
            try:
                this_page_comment = get_single_page(url)
            except:
                print("出现了一个错误。正在重试({}/5)".format(i+1))
                time.sleep(1)
                continue
            break
        else:
            print(">>错误<<：看来你遇到了一个企鹅。你可以后退访问其他页面或报告管理员。")
            input()
            exit()
        # 如果本页的内容与上页完全相同，就代表已经到了末页，丢弃本页并结束循环
        if all_comments[-len(this_page_comment):] == this_page_comment:
            break
        all_comments += this_page_comment

    #conf.set('moe','done','1')
    #conf.write(open('config.ini','w'))
    with open('vote.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(all_comments))
    print("已经读取完毕所有楼层的数据并保存为vote.json。按Enter键继续...")
    input()
    return 1


def get_single_page(url):
    global too_young_users
    # 获取页面信息
    r = requests.get(url, cookies=my_cookies)
    r.raise_for_status()
    r.encoding = 'gbk'
    soup = BeautifulSoup(r.text.replace('<br/>', '\n'), "lxml")

    # 获取本页用户的注册时间，如果注册时间晚于要求（8012年11月11日）则将此UID标记为无效票
    userinfo = re.findall(r'"uid":([0-9]+).*?"regdate":([0-9]+)',soup.text)
    for thisuser in userinfo:
        if int(thisuser[1]) > 1541952000:
            too_young_users.append(thisuser[0])
            print ("已经将UID:{}标记为无效票：注册时间晚于要求（8012年11月11日）".format(thisuser[0]))

    # 获取本页的所有回复
    floors = soup.find_all('a', attrs={'name':re.compile('^l')})
    comments = soup.find_all('span', class_='postcontent ubbcode')
    uids = [re.search(r'uid=([0-9]+)',str(i)).group(1) for i in soup.find_all('a', class_='author b')]
    if len(uids) != len(comments):
        uids.pop(0) # 第一页的楼层包含了楼主而comments中没有包含，这一情况下剔除uids[0]和floors[0]
        floors.pop(0)
    comments_list = []
    for i in range(len(comments)):
        if uids[i] in too_young_users:  # 过滤新账号
            comments_list.append({'floor':floors[i].attrs['name'][1:], 'uid':uids[i], 'content':"这个账号的注册时间晚于要求，已经被过滤！"})
        else:
            comments_list.append({'floor':floors[i].attrs['name'][1:], 'uid':uids[i], 'content':comments[i].text})
    
    return comments_list
        
def read_votes():                       # 读取已有的投票专楼数据
    with open('vote.json', 'r') as f:
        return json.loads(f.read())

def clear_save():
    conf.set('moe','saveaddr','')       # 清空之前保存的计票到的位置和票数
    conf.set('moe','votes','')
    conf.set('moe','marked','')
    conf.write(open('config.ini','w', encoding='utf-8-sig'))

def print_candidates(vote_data):        # 输出格式化的每位舰娘对应的票数。
    i = 0
    output = ''
    thecandidates = conf.get('moe','ships').split(',')
    while(len(thecandidates) < 16):
        thecandidates.append("[[无]]")
    for t in thecandidates:
        if len(print_a_condidate(t)) <= 4: # 比较取巧地处理对齐问题。卜知道会不会出问题
            output += "{}：{}".format(VALID_INPUT[i], print_a_condidate(t)+'　　　')
        else:
            output += "{}：{}".format(VALID_INPUT[i], print_a_condidate(t))
        i += 1
        if i % 4 != 0:
            output += '\t'
        else:
            output += '\n当前票数：{}\t当前票数：{}\t当前票数：{}\t当前票数：{}\n'.format(vote_data[i-4],vote_data[i-3],vote_data[i-2],vote_data[i-1])
    return output[:-1]

def formatted_vote_data(votedata, candidates):  # 格式化特定的某层楼投票结果。
    output = ''
    for i in range(len(candidates)):
        if votedata[i] != 0:
            output += print_a_condidate(candidates[i])
            output += ' '
    return output

def output_all_data(votedata, candidates):
    output = ''
    newvotedata = add_data(votedata)
    for i in range(len(candidates)):
        output += "{}：{} ".format(candidates[i], newvotedata[i])
    return output

def automatic(commit, candidates):
    auto_vote = [0 for j in range(17)]
    for ican in range(len(candidates)):
        for candidate in split_condidate(candidates[ican]):
            if tradition2simple(candidate.upper()) in tradition2simple(commit.upper()):
                auto_vote[ican] = 1
    if sum(auto_vote) > 5:
        print("本楼层无效：投票数超过了5票。")
        return [0 for j in range(17)]
    else:
        return auto_vote

def add_data(new_data):
    output_data = [0 for j in range(17)]
    for thisdata in new_data:
        for i in range(len(output_data)):
            output_data[i] += thisdata[i]
    return output_data

def minus_data(save_data, new_data):
    for i in range(len(save_data)):
        save_data[i] -= new_data[i]
    return save_data

def print_a_condidate(condidate):
    return condidate.split('/')[0]

def split_condidate(condidate):
    return condidate.split('/')

if __name__ == '__main__':
    my_cookies = set_cookies()
    i = 0
    marked = []
    vote_data = [] 
    print ("欢迎使用NGA舰萌计票辅助系统v1。如果在使用中发现问题请联系NGAID：_江天万里霜_")

    # 读取候选人
    if conf.get('moe','ships') != '':
        print("发现已经存在的候选人名单：{}\n按Enter键以使用该名单，键入任何其他值以重新钦定一份候选人名单：".format(conf.get('moe','ships')))
        if input():
            print("请钦定候选人名单。\n同一候选人可以添加多个名称，用\"/\"分隔，多个候选人之间用半角逗号\",\"分隔。\n候选人的名称大小写或简繁均不拘，但请避免在每个候选人的第一个名称中使用西里尔字母（会产生排版问题）。\n例：>>朝潮,大淀,加賀,飛鷹,biSMarCk/俾斯麦,ywwuyi/爽哥,西南風/LIBECCIO<<\n注：如果有候选人的名字被其他人的名字包含，自动识别时会产生问题（例如潮），如果潮和其他名字中包含潮的舰娘分到一组，请不要为她添加潮这个名称。")
            conf.set('moe','ships',input())
            conf.write(open('config.ini','w', encoding='utf-8-sig'))
    else:
        print("请钦定候选人名单。\n同一候选人可以添加多个名称，用\"/\"分隔，多个候选人之间用半角逗号\",\"分隔。\n候选人的名称大小写或简繁均不拘，但请避免在每个候选人的第一个名称中使用西里尔字母（会产生排版问题）。\n例：>>朝潮,大淀,加賀,飛鷹,biSMarCk/俾斯麦,ywwuyi/爽哥,西南風/LIBECCIO<<\n注：如果有候选人的名字被其他人的名字包含，自动识别时会产生问题（例如潮），如果潮和其他名字中包含潮的舰娘分到一组，请不要为她添加潮这个名称。")
        conf.set('moe','ships',input())
        conf.write(open('config.ini','w', encoding='utf-8-sig'))

    # 读取投票数据
    if 'vote.json' in os.listdir('.'):
        print ("发现已经存在的票楼数据。按Enter键以从该数据开始或继续，键入任何其他值以清空之前保存的数据并重新读取：")
        if input():
            print("----------------------------")
            print("清空之前保存的数据并读取新数据：")
            get_pages()
            clear_save()
        else:
            print("----------------------------")
            print("从已有的数据开始或继续：")
    else:
        print("----------------------------")
        print("没有找到票楼数据文件。开始读取新的投票数据：")
        get_pages()
        clear_save()

    vote_list = read_votes()

    # 读取存档
    if conf.get('moe','saveaddr') != '' and conf.get('moe','votes') != '':
        print("发现已经存在的计票存档：进度{}/{}。\n按Enter键以继续该存档，键入任何其他值以抛弃此存档并从头开始：".format(int(conf.get('moe','saveaddr')),len(vote_list)))
        if input():
            print("----------------------------")
            print("清空已有存档并从头开始：")
            clear_save()
        else:
            print("----------------------------")
            print("从已有进度开始：")
            try:
                i = int(conf.get('moe','saveaddr'))
                vote_data = json.loads(conf.get('moe','votes'))
                if conf.get('moe','marked') != '':
                    marked = json.loads(conf.get('moe','marked'))
            except:
                print(">>错误<<：计票存档存在问题。从头开始计票：")
                clear_save()
    else:
        print("----------------------------")
        print("没有发现计票存档。从头开始计票：")
        clear_save()

    # 读取候选人
    candidates = conf.get('moe','ships').split(',')
    while(len(candidates) < 16):
        candidates.append("[[无]]")
    if len(candidates) <= 1:
        print(">>错误<<：请检查你是否输入了错误的候选人名单？")
        input()
        exit()

    # 主计票循环
    print("请关闭输入法与大写锁定。键入任意值以继续...")
    input()
    while(i <= len(vote_list)-1):
        os.system('cls')
        this_vote = [0 for j in range(17)]
        # 用户UI
        print("进度：{}/{} 已标记的楼层：{}".format(i,len(vote_list),','.join(list(map(str,marked)))))
        if vote_data:
            print("============上一个楼层：============")
            print("#{} 发帖人：{}\n-----发帖内容-----\n{}\n-----已被计为-----\n{}".format(vote_list[i-1]['floor'], vote_list[i-1]['uid'], vote_list[i-1]['content'], formatted_vote_data(vote_data[-1], candidates)))
        print("============本楼层：============")
        print("#{} 发帖人：{}\n-----发帖内容-----\n{}".format(vote_list[i]['floor'], vote_list[i]['uid'], vote_list[i]['content']))
        automatic_vote = automatic(vote_list[i]['content'],candidates)
        print("-----自动识别-----\n{}".format(formatted_vote_data(automatic_vote, candidates)))
        print("============输入舰娘前面的序号来计票============")
        tempdata = add_data(vote_data)
        print(print_candidates(tempdata))
        print("t：在输入中加入自动识别的内容")
        print("例：输入>>12ws<<代表为序号为1、2、w、s的舰娘各计一票；\n输入>>1tg<<代表为自动识别出的舰娘和序号为1的舰娘各计一票，并标记本楼所在的楼层")
        print("或者输入一个操作：\n空格：跳过本楼；h：保存当前进度；g：标记此楼层；b：后退一步")
        while(True):
            input_invalid_char = False
            input_back = False
            action = input()
            if not action:    
                print("你没有输入任何值。请输入一个值！")  
                continue
            elif action == ' ': # 跳过
                print("你跳过了本楼。")
            elif action == 't': # 自动输入内容
                this_vote = automatic_vote
            elif action == 'b': # 后退一步
                if i >= 1:
                    input_back = True
                else:
                    print("已经是第一步了！")
                    input_invalid_char = True
            elif action == 'g': # 标记楼层
                print("已标记楼层：{}".format(vote_list[i]['floor']))
                marked.append(vote_list[i]['floor'])
            elif action == 'h': # 保存
                conf.set('moe','saveaddr',str(i))
                conf.set('moe','votes',json.dumps(vote_data))
                conf.set('moe','marked',json.dumps(marked))
                conf.write(open('config.ini','w', encoding='utf-8-sig'))
                print("在位置{}/{}保存了。当前的票数为：\n{}".format(i,len(vote_list),output_all_data(vote_data,candidates)))
                input()
                exit()
            else:               # 手动计票
                for char in action:
                    if (char not in VALID_INPUT[:len(candidates)]) and (char != 't') and (char != 'g'):
                        input_invalid_char = True
                        break
                else:
                    if 't' in action:
                        this_vote = automatic_vote
                    if 'g' in action:
                        print("已标记楼层：{}".format(vote_list[i]['floor']))
                        marked.append(vote_list[i]['floor'])
                    for ichar in range(len(candidates)):
                        if VALID_INPUT[ichar] in action:
                            this_vote[ichar] = 1
            if input_invalid_char:
                print("你输入了一个非法的值。请重新输入！")
                continue
            break   # 如果是合法的输入则循环会直接break，否则循环继续
        if input_back:
            vote_data.pop(-1)
            if str(vote_list[i-1]['floor']) in marked:
                marked.pop(marked.index(str(vote_list[i-1]['floor'])))
            i -= 1
        else:
            this_vote[16] = int(vote_list[i]['floor'])
            vote_data.append(this_vote)
            i += 1
    
    conf.set('moe','saveaddr',str(i))
    conf.set('moe','votes',json.dumps(vote_data))
    conf.set('moe','marked',json.dumps(marked))
    conf.write(open('config.ini','w', encoding='utf-8-sig'))
    print("计票已完成，输出计票结果至result.csv。")
    end_data = '舰娘,'
    for j in candidates:
        end_data += "{},".format(print_a_condidate(j))
    end_data += '\n票数,'
    all_data = add_data(vote_data)
    for i in range(len(candidates)):
        end_data += '{},'.format(all_data[i])
    end_data += '\n以下楼层被标记,\n'
    end_data += ','.join(list(map(str,marked)))
    end_data += '\n'
    # 分页输出
    i=1
    end_data += "分页结果输出如下：\n页码,"
    for j in candidates:
        end_data += "{},".format(print_a_condidate(j))
    end_data += '\n'
    tempdata = [vote_data[0]]
    while(i<len(vote_data)):
        while(True):
            
            if i == len(vote_data) - 1:
                tempdata.append(vote_data[i])
                break
            elif (vote_data[i][16] % 20 < vote_data[i-1][16] % 20):
                break
            else:
                tempdata.append(vote_data[i])
                i += 1
                
        tempdata = add_data(tempdata)
        end_data += "第{}页,".format(vote_data[i-1][16] // 20+1)
        for j in tempdata[:-1]:
            end_data += "{},".format(j)
        end_data += '\n'
        tempdata = []
        tempdata.append(vote_data[i])
        i += 1

    with open('result.csv', 'w', encoding='gbk') as f:
        f.write(end_data)
    os.system('pause')