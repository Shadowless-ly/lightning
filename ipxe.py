#!/usr/bin/env python
#-*-coding=utf-8-*-

import flask

from ipxelib import ipxetool
from ipxelib import taskhandle
from ipxelib import pikachu
import mysql.connector.errors
import logging
import json

logging.basicConfig(level=logging.DEBUG)
app = flask.Flask(__name__)


#---------------------------------------------
# 获取数据库链接,保存于全局对象flask.g
# 使用get_db()可以直接取得MyDB对象
#---------------------------------------------
def get_db():
    logging.debug('==========Get db ==========')
    db = getattr(flask.g, '_database', None)
    if db is None:
        db = taskhandle.MyDB()
        flask.g._database = db
    return db

def query_record(mac):
    """处理IPXE GET请求参数,查询OS安装所需参数
    """
    mac = flask.request.args.get('mac') # 获取获取request参数
    logging.debug(mac)
    if mac is None: # 检查mac地址是否为空
        return 'echo please send request with your mac address\n'
    else:
        mac = str(mac).upper()  # 全部转换为大写
        db = get_db()   # 获取数据库链接
        try:
            res = db.get_query(mac) # 依据mac查询os_miimon
        except mysql.connector.ProgrammingError as e:
            res = e.msg
            return 'echo %s' %e.msg
        if len(res) == 0:   # 查询无结果则提示no task
            return "echo \033[1;33mThere is no task for your mac:%s !\033[0m\necho \033[1;36mYou could access http://192.168.1.1/auto/config/PikachuClient.exe to download manager cli tool!\033[0m\necho \033[1;36mUse http://172.16.73.10/auto/config/PikachuClient.exe in lan of SIT.\033[0m" %mac
        else:
            record = ipxetool.Record(res[0]) # 将查询结果的第一条转换为record对象
            return record

def back_to_menu(record: str, url: str) -> ipxetool.IpxeString:
    """ipxe script,返回菜单
    """
    s = ipxetool.IpxeString()
    s.append_substr(record)
    s.append_substr('set menu %s' %url)
    s.append_substr('set msg "chain ${menu}"')
    s.append_substr('prompt --timeout=10000 Booting back to the menu. Press any key to shell! && echo you can use ${msg} back to the menu! && shell ||')
    s.append_substr('chain --timeout 10000 ${menu}')
    return s

@app.route('/')
def index():
    return '<h1>Hello, Welcome to Auto iPXE!</h1>'

@app.route('/uefi')
def efi():
    """IPXE UEFI模式接口
    """
    mac = flask.request.args.get('mac') # 获取获取request参数
    record = query_record(mac)
    logging.info(mac)
    if not isinstance(record, ipxetool.Record): #return if record is String
        s = back_to_menu(record, 'http://os.com/ipxe.d/efimenu.ipxe')
        return s.getstr()
    logging.debug(dir(record))

    if record.mode == 2:
        s = back_to_menu('echo the current mission mode is Legacy ,the arguments Only support Legacy mode!', 'http://os.com/ipxe.d/efimenu.ipxe')
        return s.getstr()

    elif record.record_status == 1:
        return ipxetool.Script.boot_from_hd()

    elif record.vmlinuz_args == 'NA': # 如vmlinz_args参数置为NA,表示采用grub启动,否则采用标准uefi启动
        script = ipxetool.Script.grub_script(record.os_name) # 生成grub启动脚本
    else:
        script = ipxetool.Script.ipxe_script(record.os_name, record.kernel_name, record.initrd_name, record.vmlinuz_args) # 生成iPXE UEFI标准启动脚本
    # 将mac地址字符串置于mac_list列表
    mission_dict = {
        'type': 'OS',
        'data': {
            'mac_list':mac.split(),
            # status值为1，表示开始安装
            'message': None,
            'status': 1
        }
    }
    os = taskhandle.task(mission_dict)    
    os.start()
    os.close()
    return script

@app.route('/legacy', methods=['GET'])
def legacy():
    """IPXE Legacy模式接口
    """
    mac = flask.request.args.get('mac')
    record = query_record(mac)
    if not isinstance(record, ipxetool.Record):
        s = back_to_menu(record, 'http://os.com/ipxe.d/legacy.ipxe')
        return s.getstr()

    if record.mode == 1:
        s = back_to_menu('echo the current mission mode is UEFI ,the arguments Only support UEFI mode!', 'http://os.com/ipxe.d/legacy.ipxe')
        return s.getstr()

    scirpt = ipxetool.Script.ipxe_script(record.os_name, record.kernel_name, record.initrd_name, record.vmlinuz_args)
    mission_dict = {
        'type': 'OS',
        'data': {
            'mac_list':mac.split(),
            'message': None,
            'status': 1
        }
    }
    os = taskhandle.task(mission_dict)
    os.start()
    os.close()
    return scirpt

@app.route('/report', methods=['GET', 'POST'])
def get_report():
    if flask.request.method == 'GET':
        mac = flask.request.args.get('mac')
        return mac or 'NA'
    if flask.request.method == 'POST':
        json_data = flask.request.json
        print(json_data)
        return str(json_data)

@app.route('/os_install_report', methods=['POST'])
def os_install_report():
    """处理TaskTracker POST Request,修改OS Install状态
    """
    # mac_list = flask.request.form.get('mac_list')
    json_data = flask.request.json
    # mac_list=eval(mac_list)

    try:
        os = taskhandle.task(json_data)
        os.complete()
        os.close()

    except taskhandle.EmptyMacList as e:
        # return 'Failed EmptyMacList\n %s' %e.msg
        return e.code    # code=4
    except taskhandle.NoCurrentTask as e:
        # return 'No Current Task\n %s' %e.msg
        return e.code    # code=2
    except taskhandle.MyDBQueryError as e:
        # return 'Faied MyDBQueryError\n %s' %e.msg
        return e.code    # code=3
    except Exception as e:
        return taskhandle.UnknownError('unknow error!').code    # code=1
    # TODO 环境部署
    return '0'
    # return 'get mac list: %s' %mac_list

@app.route('/config/PikachuClient.exe', methods=['GET', 'POST'])
def pikachu_client():
    return flask.send_from_directory('/pxe/repertory/tools', 'PikachuClient.exe')

@app.route('/config/conda/', methods=['GET', 'POST'])
def env():
    """preboot conda环境配置脚本
    """
    # conda = ipxetool.Script.install_miniconda()
    conda = ipxetool.Script.read_from_file('/pxe/repertory/tools/env.sh')
    return conda

@app.route('/config/os_install/', methods=['GET', 'POST'])
def os_install():
    """new OS Install 配置脚本
    """
    os_install_script = ipxetool.Script.read_from_file('/pxe/repertory/tools/os_install_begin.sh')
    return os_install_script

@app.route('/task', methods=['GET', 'POST'])
def current_task():
    """TaskTracker请求处理
    """
    if flask.request.method == 'GET':
        return ipxetool.Script.task_explain()
    else:
        json_data = flask.request.json
        print(json_data)
        logging.error(json_data)
        try:
            c_task = taskhandle.task(json_data)
        except TypeError as e:
            # return 'Json data type Error %s, Get json: %s\n type: %s\n' % (e, json_data, type(json_data))
            return json.dumps(e.info())
        except taskhandle.UnknownMissionType as e:
            # return (e.msg,e.code)
            return json.dumps(e.info())
        except Exception as e:
            # return (taskhandle.UnknownError(e).msg, taskhandle.UnknownError(e).code)
            return json.dumps(e.info())

        send_task_json = c_task.start()
        c_task.close()
        return send_task_json
        # mac_list = flask.request.form.get('mac_list')
        # mac_list = eval(mac_list)
        # c_task = taskhandle.task('Task', mac_list)
        # task_json = c_task.get_task()
        # c_task.close()
        # # return "mac_list: %s" %mac_list
        # return task_json


@app.route('/user', methods=['GET', 'POST'])
def user():
    """pikachu管理器接口帮助文档
    """
    pass

@app.route('/user/record', methods=['GET', 'POST'])
def record():
    """pikachu Record用户接口
    """
    # 处理用户对Record的查询GET请求,http://172.16.73.10/auto/user/record?mac_address=ALL&method=all
    if flask.request.method == 'GET':
        qtype = 'record'
        # 获取mac_address参数,用于指定mac地址查询
        mac_address = flask.request.args.get('mac_address').split(',')
        # 获取method参数,用于查询类型
        method = flask.request.args.get('method')
        para = {
            'type': qtype,
            'data':{
            'mac_address': mac_address,
            'method': method}
            }
        # 将para传给pikachu query方法处理获取查询record结果
        pkc = pikachu.PikachuServer()
        result = pkc.query(para)
        pkc.close()
        return(result)

    # 处理用户添加record,record set, mac,修改record,record set状态的POST请求
    elif flask.request.method == 'POST':
        post_data = flask.request.json
        para = post_data
        pkc = pikachu.PikachuServer()
        if para['type'] in pkc.support('add'):
            result = pkc.add(para)
        elif para['type'] in pkc.support('modify'):
            result = pkc.modify(para)
        pkc.close()
        return result

@app.route('/user/table', methods=['GET', 'POST'])
def query():
    """处理其他表格查询请求

    使用PikachuServer的query方法,查询OS,CV,Stress信息
    """
    if flask.request.method == 'GET':
        qtype = 'other'
        table_name = flask.request.args.get('table')
        para = {
            'type': qtype,
            'data': {
                'table_name': table_name
            }
        }
        pkc = pikachu.PikachuServer()
        result = pkc.query(para)
        pkc.close()
        return(result)

@app.teardown_request
def teardown_db(response):
    db = getattr(flask.g, '_database', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0')