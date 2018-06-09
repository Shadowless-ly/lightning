#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
Lightning Server与Tasktracker通信格式定义

为兼容curl发送Json
curl参数为 `curl -sSL -H "Content-type:application/json"`
格式采用单引号包含的字符串,其内容为字典格式转换而来
字典内部字符串格式为双引号
type值为任务:"GetTask","OS","CV","Stress"
data值为字典dict类型,字典中必须包含"mac_list"键
"mac_list"值为列表,元素为双引号包裹的MAC地址字符串
'{
    "type"："OS",
    "data": {
        "mac_list": ["11:22:33:44:55:66:77"],
        "status": 0
    }
}'
"""


import os
import platform
import subprocess
import re
import sys
import shutil
import atexit
import signal
import time
import json
import threading
from threading import Thread
try:
    from queue import Queue
except:
    from Queue import Queue

# 用于测试的临时列表,正常使用时必须为空
TEMP = ['00:A0:C9:00:00:03']
# MAC地址过滤名单，16进制忽略大小写
BLACKHOLE = ['00:0C:29:CB:12:DB']
# 检查sysconfig设备管理目录是否存在
IF_SYSNET = os.path.exists('/sys/class/net/')
# 需要滤除的接口名，填写具体接口名或正则表达式，使用单引号'加入列表
EXCLUDE = ["'lo'", "'bond.*?'", "'vir.*?'"]
# 系统平台
PLATFORM = platform.system()
# url用于获取Task
TASKURL = 'http://192.168.1.1/auto/task'
# TASKURL = 'http://localhost/auto/task'
# 访问TASKURL的时间间隔s
INTERVAL = 5
#CONDA URL
CONDAURL = 'http://192.168.1.1/auto/config/conda'
# CONDAURL = 'http://localhost/auto/config/conda'
# OS Install状态报告
OS_INSTALL_REPORT = 'http://192.168.1.1/auto/os_install_report'
# OS 安装开始环境配置脚本
OS_INSTALL_BEGIN = 'http://192.168.1.1/auto/config/os_install'

class Reporter(object):
    """该类实现了和lightning Web Server交互的Reporter.
    
    该类可以创建一个reporter,使用`curl_post()`以及`urllib_post()`向lightning web server发送POST请求
    `get_task()`方法从服务器端获取当前任务信息,`report()`方法用于向服务端报告任务状态与日志信息
    
    """
    def __init__(self, temp=None, blackhole=BLACKHOLE, if_sysnet=IF_SYSNET, exclude=EXCLUDE, platform=PLATFORM, taskurl=TASKURL):
        """可以通过赋值以下参数来自定义Reporter配置.

        temp:list类型,用于测试的临时列表
        if_sysnet:布尔类型,True表示使用sysnet来获取网卡名
        exclude:list类型,需要过滤掉的接口名,使用正则表达式或具体接口名,使用格式"'example'"加入列表
        platform:str类型,系统平台
        taskurl:str类型,用于获取Task的url地址

        """
        self._TEMP = temp
        self._BLACKHOLE = blackhole
        self._IF_SYSNET = if_sysnet
        self._EXCLUDE = exclude
        self._PLATFORM = platform
        self._TASKURL = taskurl
        self.nic_list = []
        self.maclist = []
        self.IF_CURL = not bool(self.shell_run('type curl')[1])

        if self._PLATFORM in ['Linux']: # 判断平台类型 
            if self._IF_SYSNET: # 判断是否使用sysnet获取网卡名
                self._sys_net()
                self._get_mac_list()
            else:
                # TODO Use another way to get Nic list
                raise EnvironmentError('Not Found /sys/class/net!')
        else:
            # TODO Get Windows NiC MAC Address
            raise OSError('Not support %s yet!' %PLATFORM)

    @classmethod
    def shell_run(self, cmd):
        """运行shell命令.

        执行linux shell命令,返回结果与错误信息
        传入str类型的cmd命令,返回执行结果元组(result, error message)
        """
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        p.wait()
        recived = p.communicate(input=None)
        return recived

    def _sys_net(self):
        # 获取/sys/class/net目录下的所有网络设备接口名
        # 比对需要排除的._EXCLUDE列表,获取有效网卡名称并存放于.nic_list列表
        ex_iflist = re.compile('|'.join(self._EXCLUDE))
        iflist = os.listdir('/sys/class/net')
        exclude_list = [interface.strip("'") for interface in ex_iflist.findall(str(iflist))]
        self.nic_list = [i for i in iflist if i not in exclude_list]

    def _get_mac_list(self):
        # 获取有效网口的MAC地址,存放于.maclist
        for interface in self.nic_list:
            try:
                with open('/sys/class/net/%s/address' %interface, 'r') as f:
                    self.maclist.append(f.read().strip().upper())
            except IOError:
                raise IOError('/sys/class/net/%s/address Not Exists' %interface)
        if self._BLACKHOLE:
            BLACKHOLE = [item.upper() for item in self._BLACKHOLE] 
            self.maclist = [addr for addr in self.maclist if addr not in BLACKHOLE]
            if self._TEMP:
                self.maclist.extend(self._TEMP)

    def curl_post(self, json_data, url):
        """利用curl工具发送HTTP POST请求,封装`curl -sSL -H "Content-type:application/json" -X POST -d JSON_DATA URL`.

        json_data: str类型,需要携带的数据
        url: str类型,请求的目标url
        """
        # data = '"mac_list=' + str(data) + '"'
        cmd = 'curl -sSL -H \"Content-type:application/json\" -X POST -d \'%s\' %s' %(json_data, url)
        result = self.shell_run(cmd)
        if result[1]:
            ret = result[1].decode('utf-8') + '======' + cmd 
            # raise OSError(result+'====='+cmd)
            raise OSError(ret)
        else:
            return result[0].decode('utf-8')

    def curl_get(self, url, data=None):
        """发送GET请求到指定url. 参数为-s静默模式,-S显示错误信息,-L跟踪跳转链接
        """
        if data:
            if len(data) != 1:
                data = '?' + '&'.join(data)
            else:
                data = '?' + data[0]
            cmd = 'curl -sSL \"%s%s\"' %(url, data)
        else:
            cmd = 'curl -sSL \"%s\"' %(url)

        result = self.shell_run(cmd)
        if result[1]:
            ret = result[1].decode('utf-8') + '======' + cmd 
            raise OSError(ret)
        else:
            return result[0].decode('utf-8')


    def urllib_post(self, data, url):
        """使用标准库urllib发送HTTP POST请求.

        data: str类型,需要携带的数据
        url: str类型,请求的目标url
        """
        # TODO If not have Curl tool,Try urllib
        pass

    def report(self, data):
        """报告任务状态,提交测试结果数据.
        """
        # TODO Report task status
        pass

    def post_with_maclist(self, url, mission_type=None, data={}):
        """发送POST请求至目标url.
        
        mission_type: str类型, {OS, CV Stress, Other, Error}
        data: dict类型, {mac_list: [''], msg: ''}
        """
        if self.IF_CURL:
            data.update({"mac_list": self.maclist})

            json_data = {
                "type": mission_type,
                "data": data
            }
            response = self.curl_post(json.dumps(json_data), url)
        else:
            # response = self.urllib_post(json.dumps(json_data), url)
            pass
        return response

    def get_task(self):
        """用于获取任务，构造Json POST到lightning服务端,返回值为Json格式的任务.
        """
        if self.IF_CURL:
            json_data = {
                "type": "GetTask",
                "data": {"mac_list": self.maclist}
            }
            response = self.curl_post(json.dumps(json_data), self._TASKURL)
        else:
            # response = self.urllib_post(self.maclist, 'http://localhost/auto/task')
            pass
        return response


class Daemon(object):
    """实现了守护进程的创建,关闭和重启.

    该类用于创建一个linux系统下的守护进程
    定义任务执行可以通过重写子类的`_run()`方法
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',stderr='/dev/null'):
        """初始化用来记录进程pid的文件位置和标准输入,输出,错误流

        :type strpidfile: 用来记录守护进程pid的文件
        stdin,stdout,stderr: 文件描述符重定向,使用/dev/stdin,/dev/stdout,/dev/stderr可以输出到终端
        """
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def _daemonize(self):
        """守护进程创建.
        """
        try:
            # 第一次fork,生成子进程
            pid = os.fork()
            if pid > 0:
                # 退出主进程,使子进程脱离父进程,将子进程放入后台运行
                sys.exit(0) 
        except OSError as e:
            sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)
        # 改变当前工作目录
        os.chdir('/') 
        # 建立新会话,由于子进程继承了父进程的进程组,控制终端,会话组.
        # 使用setsid()建立新会话,子进程成为新会话组组长,与原来会话和进程组脱离,与控制终端脱离
        os.setsid() 
        os.umask(0) # 重设文件创建掩码

        try:
            # 第二次fork,由于当前进程已经为无终端的会话组组长,可以申请打开控制终端
            # 故再次fork出第二子进程,退出第一子进程,可以禁止打开控制终端
            pid = os.fork() 
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        # 重定向文件描述符
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'w')
        se = open(self.stderr, 'w')

        # 注册退出回调函数,使pidfile和进程存在性保持一致
        atexit.register(self.delpid)
        signal.signal(signal.SIGTERM, lambda signalnum, stack_frame : exit(0))
        pid = str(os.getpid())
        open(self.pidfile, 'w+').write('%s\n' % pid)

    def delpid(self):
        """删除pidfile.
        """
        os.remove(self.pidfile)

    def start(self):
        """启动守护进程.

        根据pidfile判断进程是否存在,不存在则创建,若存在则报出pid并退出
        """
        print('Starting lightning TaskTracker...')
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        
        if pid:
            message = 'pidfile %s already exist. Daemon already running!\n'
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        self._daemonize()
        self._run()

    def stop(self):
        """关闭守护进程.
        """
        print('Stoping lightning TaskTracker...')
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        
        if not pid:
            message = 'pidfile %s does not exist. Daemon not running!\n'
            sys.stderr.write(message %self.pidfile)
            return
        while True:
            try:
                # print('os.kill %s' %pid)
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            # except OSError as e:
            except Exception as e:
                print('No such process')
                # err = str(e)
                # if err.find('No') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                    return 0
                else:
                    print(e)
                    return 1
                    # print(err)
                    # sys.exit(1)
        print('OK')

    def restart(self):
        """重启守护进程.
        """
        self.stop()
        self.start()
        
    def _run(self):
        """守护进程所执行的任务.
        """
        while True:
            time.sleep(INTERVAL)
            # TODO Task

class Lightningd(Daemon):
    """lightning tasktracker守护进程.

    `running_log()`方法用于记录日志,`task_parser()用于解析服务器Response的Json`
    """
    def __init__(self, logfile='/lightning.log', **kw):
        self.logfile = logfile
        pidfile = '/etc/lightningd.pid'
        super(Lightningd, self).__init__(pidfile, **kw)

    def _run(self):
        self.running_log('START'.center(50, '='))
        atexit.register(lambda : self.running_log('STOP'.center(50, '=')))
        while True:
            try:
                reporter = Reporter()
                task_json = reporter.get_task()
                self.running_log(task_json)
                t = Thread(target=self.task_parser(task_json), args=())
                t.start()
                t.join()
            except Exception as e:
                self.running_log('%s' % e)
            finally:
                time.sleep(INTERVAL)

    def running_log(self, message):
        """记录日志,使用追加模式记录带有时间戳的日志.

        默认日志位置为/lightning.log
        message: str类型,写入日志文件的字符串
        """
        try:
            with open(self.logfile, 'a+') as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                f.write(timestamp + ' ' + message + '\n')
        except IOError as e:
            message = 'Config Running log Fail: %s' %str(e)
            sys.stderr.write(message)

    def task_parser(self, task_json):
        """解析服务器Response的Json.

        task_json: str类型,由服务端返回的Json类型
        :returns: <function run_task> 返回的run_task方法用于处理指定类型的任务,任务类型由参数task_json的'type'字段作为键从task_dict中取值
        """
        def run_task(*args, **kw):
            task_dict = {
                'OS': self._os,
                'CV': self._cv,
                'Stress': self._stress,
                'Other': self._other,
                'Error': self._error
            }

            task_string = json.loads(task_json)
            if task_string['type'] in task_dict:
                # print(task_dict[task_string['type']])
                return task_dict[task_string['type']](task_string['data'])
            else:
                self.running_log(task_string['type'] + ' not in task_dict!')
        return run_task

    def _os(self, data):
        """OS任务处理方法.

        :param data：服务端Response Json中的data字段,data值为dict类型,依据data中status键值判断OS任务进度
                    data['status'] == 0 执行全新操作系统安装任务
                    data['status'] == 1 执行完成安装环境配置任务
        """
        reportor = Reporter()
        # print('data========>\n %s' % data)
        # 当前任务为一个未开始安装的操作系统
        if data['status'] == 0:
            # TODO python环境检查
            # 获取OS Install开始安装shell配置脚本
            commands = reportor.curl_get(OS_INSTALL_BEGIN)
            # 运行shell脚本,执行工具下载和安装
            result_env = reportor.shell_run(commands)
            # 记录shell脚本运行日志
            list(map(self.running_log, [i.decode('utf-8') for i in result_env if i != b'']))
            # 设置第一启动项为pxe
            self.running_log('Get Next OS Mode from Lightning Server...')
            # 获取Next OS信息
            param = eval(reportor.post_with_maclist(reportor._TASKURL, mission_type="OS", data={"status": 0}))
            self.running_log('param: %s' %param)
            # 解析Next OS的模式Legacy和UEFI
            mode = param['data'].get('mode', None)
            if mode == 2:
                result_ipmi = reportor.shell_run('/usr/bin/python pyipmi.py legacy_pxe || python pyipmi.py legacy_pxe')
            elif mode == 1:
                result_ipmi = reportor.shell_run('/usr/bin/python pyipmi.py uefi_pxe || python pyipmi.py uefi_pxe')
            else:
                result_ipmi = ('Not get ipmi result!')
            list(map(self.running_log, ['IPMI====>'] + [i.decode('utf-8') for i in result_ipmi if i != b'']))
            self.running_log('Waiting for OS Install Beginning...')
            time.sleep(120)
            reboot_log = reportor.shell_run('reboot')
            self.running_log(reboot_log)

        # 当前任务为正在安装的操作系统
        elif data['status'] == 1:
            # 从condaurl获取shell脚本并执行
            commands = reportor.curl_get(CONDAURL)
            # 运行shell脚本
            result_env = reportor.shell_run(commands)
            # 记录shell脚本运行日志
            self.running_log('start config environment...')
            list(map(self.running_log, [i.decode('utf-8') for i in result_env if i != b'']))
            # 使用ipmi修改HDD为第一启动项
            result_ipmi = reportor.shell_run('/usr/bin/python pyipmi.py disk || python pyipmi.py disk')
            list(map(self.running_log, ['IPMI====>'] + [i.decode('utf-8') for i in result_ipmi if i != b'']))
            # POST 请求OS URL,修改当前Record状态为2
            reportor.post_with_maclist(OS_INSTALL_REPORT, mission_type='OS', data={'status': 2})
            time.sleep(120)
            commands =reportor.shell_run('reboot')
            self.running_log(commands)

    def _cv(self, data):
        pass

    def _stress(self, data):
        pass

    def _other(self, data):
        pass

    def _error(self, data):
        if data['errortype'] == 'NoCurrentTask':
            self.running_log('No Current Task!')
            time.sleep(10)

def install(name='tasktracker'):
    platform_msg = platform.platform()
    boot_path_dict = {
        'rhel': '/etc/rc.d/rc.local',
        'suse': '/etc/rc.d/boot.local',
        'ubuntu': '/etc/rc.local',
        'other': None
    }
    if re.findall('rhel|centos|neokylin', platform_msg, re.IGNORECASE):
        os_name = 'rhel'
    elif re.findall('suse', platform_msg, re.IGNORECASE):
        os_name = 'suse'
    elif re.findall('ubuntu', platform_msg, re.IGNORECASE):
        os_name = 'ubuntu'
    else:
        os_name = 'other'
    boot_path = boot_path_dict.get(os_name)
    if not boot_path:
        # TODO log
        return
    current_file = os.path.realpath(__file__)

    # 检查根目录是否存在tasktracker,没有则拷贝自身过去
    if not os.path.exists('/tasktracker.py'):
        shutil.copy(current_file, '/')
        os.chmod('/tasktracker.py', 0o777)

    # 修改bootfile添加开机执行
    with open(boot_path, 'a+') as f:
        boot_file = f.read()
        if boot_file.find('tasktracker') == -1:
            f.write('\n/usr/bin/python /tasktracker.py || python /tasktracker.py')
    os.chmod(boot_path, 0o777)

    # 从condaurl获取shell脚本并执行
    report = Reporter()
    commands = report.curl_get(CONDAURL)
    # 运行shell脚本
    report.shell_run(commands)
    # 修改下次启动项为Disk
    report.shell_run('/usr/bin/python pyipmi.py disk || python pyipmi.py disk')
    
    # 添加miniconda path环境变量
    with open(boot_path, 'a+') as f:
        boot_file = f.read()
        if boot_file.find('miniconda') == -1:
            f.write('\nexport PATH="/miniconda3/bin:$PATH"\n')

    with open('/root/.bashrc', 'a+') as f:
        bash_file = f.read()
        if bash_file.find('miniconda') == -1:
            f.write('\nexport PATH="/miniconda3/bin:$PATH"\n')
    os.chmod('/root/.bashrc', 0o777)
    # 重启
    subprocess.call(["reboot"])


def main():
    # lightning = Lightningd(stdout='/dev/stdout', stderr='/dev/stderr', stdin='/dev/stdin')
    lightning = Lightningd()
    argv = len(sys.argv) < 2 and 'restart' or sys.argv[1]
    action = {
        'start': lightning.start,
        'stop': lightning.stop,
        'restart': lightning.restart,
        'install': install,
    }
    print(argv)
    start = action.get(argv, None)
    if start:
        start()
    else:
        print('Please use [start, stop, restart, install] parameter')

if __name__ == "__main__":
    main()
