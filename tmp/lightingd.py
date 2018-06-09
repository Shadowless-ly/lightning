#!/usr/bin/env python
#coding:utf-8
import sys
import os
import platform
import re
import subprocess
import time
import signal
import threading

# MAC list for test
TEMP = ['00:A0:C9:00:00:03']
# MAC地址过滤名单，16进制忽略大小写
BLACKHOLE = ['00:0C:29:CB:12:DB']
# 检查sysconfig设备管理目录
IF_SYSNET = os.path.exists('/sys/class/net/')
# 需要滤除的接口名，填写具体接口名或正则表达式，使用单引号'加入列表
EXCLUDE = ["'lo'", "'bond.*?'", "'vir.*?'"]
# 系统平台
PLATFORM = platform.system()

#-----------------------------------------------------------
# 执行linux shell命令，返回结果与错误信息
# 传入cmd shell命令字符串，
# 返回执行结果元组(result, error message)
#-----------------------------------------------------------
def shell_run(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    recv = p.communicate(input=None)
    p.wait()
    return recv

def signal_handle(signum, frame):
    # print('\nGET Control + C Signal, Process Exit！')
    os.remove('/root/Desktop/task.log')
    exit(0)

def subtask(url):
    p_ret = []
    result = shell_run('curl -sSL http://os.com/auto/config/conda | sh')
    p_ret = result
    return 0

def daemonize(pid_file=None):
    pid = os.fork()
    if pid:
        sys.exit(0)
    os.chdir('/')
    os.umask(0)
    os.setsid()

    _pid = os.fork()
    if _pid:
        sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null') as read_null, open('/dev/null', 'w') as write_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())

    signal.signal(signal.SIGINT, signal_handle)

    with open('/root/Desktop/task.log', 'a') as f:
        f.write(str(os.getpid())+'\n')

    while True:
        p_ret = []
        res = run()
        if res[0].decode('utf-8') == 'True':
            with open('/root/Desktop/task.log', 'a') as f:
                mark = time.strftime('%Y-%m-%d %H:%M:%S %a', time.localtime())
                # mark = '['+ mark +']'+ res[0].decode('utf-8') + '\n'
                f.write(mark)
                p = threading.Thread(target=subtask, args=())
                p.start()
                p.join()
                f.write(str(p_ret))
        time.sleep(5)


#-----------------------------------------------------------
# 编译正则表达式，过滤出/sys/class/net下网卡接口名
# 返回nic_list: 网卡接口名列表
#-----------------------------------------------------------

def sys_net():
    ex_iflist = re.compile('|'.join(EXCLUDE))
    iflist = os.listdir('/sys/class/net')
    exclude_list = [interface.strip("'") for interface in ex_iflist.findall(str(iflist))]
    nic_list = [i for i in iflist if i not in exclude_list]
    return nic_list

#-----------------------------------------------------------
# 从/sys/class/net/<eth>/address获取mac地址信息
# 传入BLACKHOLE 需要滤除的接口名,默认为全局变量BLACKHOLE
# 返回maclist: MAC地址列表 list
#-----------------------------------------------------------

def mac_list(BLACKHOLE=BLACKHOLE, TEMP=TEMP):
    maclist=[]
    for interface in sys_net():
        try:
            with open('/sys/class/net/%s/address' %interface, 'r') as f:
                maclist.append(f.read().strip().upper())
        except IOError:
            raise IOError('/sys/class/net/%s/address Not Exists' %interface)
    if BLACKHOLE:
        BLACKHOLE = [item.upper() for item in BLACKHOLE] 
        maclist = [addr for addr in maclist if addr not in BLACKHOLE]
        maclist.extend(TEMP)
    return maclist

#-----------------------------------------------------------
# 使用curl工具构造POST请求，并发送至指定url，收取response
# 传入data: POST的数据部分 str ，url: 目标地址 str，
# 返回recv：请求结果(Reponse，err)
#-----------------------------------------------------------

def curl_post(data, url):
    if_shell = shell_run('type curl')[1]
    if if_shell:
        raise IOError(if_shell)
    else:
        data = '"mac_list=' + str(data) + '"'
        cmd = 'curl -sSL -X POST -d %s %s' %(data, url)
        return shell_run(cmd)

def run():
    if PLATFORM == 'Linux':
        if IF_SYSNET:
            response = curl_post(mac_list(), 'http://localhost/auto/task')
            return response
            # logging.info(curl_post(mac_list(), 'http://localhost:5000/os_install_report'))
        else:
            raise EnvironmentError('Not Found /sys/class/net!')
    else:
        raise OSError('Not support %s yet!' %PLATFORM)

if __name__ == '__main__':
    daemonize()