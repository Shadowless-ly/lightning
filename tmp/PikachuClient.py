import json
from sys import exit
from copy import copy
from urllib import request
from urllib import error
from urllib import parse
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit import prompt, HTML, ANSI
# from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter


####################
#base url dict
#url构成参数
#修改query字段添加GET参数
#修改path字段控制url地址
####################
base_url_dict = {
 'scheme': 'http',
 'netloc': '172.16.73.10',
 'path': '/auto',
 'params': '',
 'query': '',
 'fragment': ''
}


class PikachuConnector(object):
    """Lightning Clinet端

	用于查询，修改，添加Lightning任务以及测试结果获取
	"""
    def __init__(self, base_url_dict):
        # 组装record查询url path
        self.base_url_dict = copy(base_url_dict)
        self.base_url_dict['path']  += '/user'
        self.record_url = parse.urlunparse(self.base_url_dict.values())

        # 新建opener并添加httphandler
        # proxyhandler = request.ProxyHandler({})
        # opener = request.build_opener(proxyhandler)

    def _send(self, req, retry=2):
        try:
            noproxy_handler = request.ProxyHandler({})
            opener = request.build_opener(noproxy_handler)
            response = opener.open(req)
        except error.URLError as e:
            response = None
            print(str(e.code) + ':' + e.msg)
            if retry > 0:
                if hasattr(e, 'code') and 500 <= e.code < 600:
                    return self._send(req, retry-1)
        return response

    def query(self, qtype='record', mac_address=[], method='all', table=''):
        """pikachu查询操作,查询record数据与其他table数据
		
		:param qtype: 查询目标类型,可接受值为'record' or 'other',record表示record的查询,other表示对其他table
		:param mac_address: mac地址列表,当qtype为'record'时有效
		:param method: 选择所有任务'all'或当前任务'current',当qtype为'record'时有效
		:param table: 当qtype为other类型,会使用table参数构造GET请求,table表示目的table名
		:returns: str,http response
		"""
        if qtype == 'record':
            """record查询

			所有mac地址当前任务: mac_address=['ALL'], method=current
			指定mac地址当前任务：mac_address=['1a:2b:3c:4d:5e:6f'], method=current
			指定mac地址所有任务：mac_address=['a1:b2:c3:d4:e5:f6', '1a:2b:3c:4d:5e:6f'], method=all
			"""
            # 查询mac_address list中的mac地址对应record
            # mac_address为空列表则查询所有record
            query_record_url = copy(self.base_url_dict)
            query_record_url['path'] += '/record'
            query_record_url['query'] = 'mac_address=' + str(','.join(mac_address).upper()) + '&method=%s' % method
            # http://172.16.73.10/auto/user/record?mac_address=1111111,2222222,ABCABCABC&method=all
            qurl = parse.urlunparse(query_record_url.values())
            # print(qurl)
            qrequest = request.Request(qurl)
        elif qtype == 'other':
            """其他table查询
			"""
            query_other_url = copy(self.base_url_dict)
            query_other_url['path'] += '/table'
            query_other_url['query'] = 'table=' + table
            # http://172.16.73.10/auto/user/table?table=OS
            qurl = parse.urlunparse(query_other_url.values())
            # print(qurl)
            qrequest = request.Request(qurl)
        # 发送request
        resonse = self._send(qrequest)
        if resonse:
            return resonse.read().decode('utf-8')    # msg decode by utf-8
        else:
            return resonse    # None

    def add(self, atype='add_mac', mac='', mac_id=None, set_id=None, mission_id=None, status=0, result=0, type_id=0):
        """添加record与record set

		:param atype: 支持字符串参数''add_mac','add_record', 'add_record_set'
		:param mac: mac地址字符串,用于添加记录
		:param set_id: record set id用于为指定record set添加record
		:param mission_id: 为添加record具体任务
		:param status: 新增状态,默认为0未开始
		:param result: record结果,默认为0无
		:param type_id: record类型,支持0 'OS', 1 'CV', 2 'Stress'
		:param mac_id: int,mac表中的id值
		:returns int, 0 Done or 1 Failed
		"""
        headers = {'Content-Type': 'application/json'}
        data = {
         'type': atype,
         'data': {
          'mac': mac,
          'set_id': set_id,
          'mission_id': mission_id,
          'status': status,
          'result': result,
          'type_id': type_id,
          'mac_id': mac_id
         }
        }
        add_record_url = copy(self.base_url_dict)
        add_record_url['path'] += '/record'
        aurl = parse.urlunparse(add_record_url.values())
        print(aurl)
        arequest = request.Request(url=aurl, headers=headers, data=json.dumps(data).encode('utf-8'))
        response = self._send(arequest)
        if response:
            return response.read().decode('utf-8')
        else:
            return response

    def modify(self, mtype="modify_record", record_id=None, set_id=None, mac_id=None, record_status=0, set_status=0, mission_id=None, type_id=None):
        # mtype为modify_record表示对record进行修改
        # 实现了record的status,mission_id修改；record_set的status修改
        headers = {"Content-Type": "application/json"}
        if mtype == "modify_record":
            mdata = {
             'status':record_status,
             'id': record_id,
             'type_id': type_id,
             'mission_id': mission_id
            }
        # mtype为modify_record_set表示对record_set进行修改
        # 支持status修改
        elif mtype == "modify_record_set":
            if set_status:
                mdata = {
                 'status': set_status,
                 'id': set_id,
                }
            else:
                return "You should specify the record set status！"
        modify_record_url = copy(self.base_url_dict)
        modify_record_url['path'] += '/record'
        murl = parse.urlunparse(modify_record_url.values())
        print(murl)
        data = {
         'type': mtype,
         'data': mdata
        }
        # print(json.dumps(data))
        mrequest = request.Request(url=murl, headers=headers, data=json.dumps(data).encode('utf-8'))
        response = self._send(mrequest)
        if response:
            return response.read().decode('utf-8')
        else:
            return response

class PikachuView(object):
    """Pikachu Client prompt视图
	"""
    def __init__(self):
        self.current_view = 'Pikachu'
        self.help_message = ''
        self.view_complete_list = {'show'}
        self.pkcon = PikachuConnector(base_url_dict)
        self.status_dict = {
            '-1' : 'CLOSED',
            '0' : 'NOT RUNNING',
            '1': 'RUNNING',
            '2': 'DONE'
        }
        self.type_id_dict = {
            'OS': '0',
            'CV': '1',
            'Stress': '2'
        }

    def _response(self, response):
        if response != None:
            raw = json.loads(response).get('rowcount', None)
            if raw:
                print(HTML('<skyblue>%s raw(s) changed!</skyblue>' %raw))
            else:
                print(HTML('<yellow>Warning: No row modified!</yellow>'))
        else:
            print(HTML('<violet>Error: No response!</violet>'))

    def phelp(self):
        print(HTML(self.help_message))

    def pexit(self):
        if self.view_name == 'Pikachu-mac':
            del self.mac_id
            del self.mac
            self.pikachu_view()
        elif self.view_name == 'Pikachu-mac-set':
            del self.record_set_id
            del self.view_name
            self.record_set_view([self.mac_id, self.mac])
        else:
            exit()

    def _pquery(self):
        if self.view_name == 'Pikachu':
            mac_table = self.pkcon.query(qtype='other', table='MAC')
            if mac_table:
                return json.loads(mac_table)
        if self.view_name == 'Pikachu-mac':
            set_table = self.pkcon.query(qtype='other', table='SET')
            if set_table:
                set_table = json.loads(set_table)
            current_set_list = [i for i in set_table if str(i.get('mac_id'))==self.mac_id]
            return current_set_list
        if self.view_name == 'Pikachu-mac-set':
            record_table = self.pkcon.query(qtype='record', mac_address=[self.mac], method='all')
            if record_table:
                set_table = json.loads(record_table)
                record = [
                    i for i in set_table
                    if str(i.get('SET_ID')) == self.record_set_id
                ]
                return record

    def pshow(self):
        if self.view_name == 'Pikachu':
            print(HTML('<skyblue>show MAC ADDRESS list</skyblue>'))
            mac_table=self._pquery()
            print('-'*38)
            mac_table_title = '<skyblue>' + ' ' + 'MAC ID'.ljust(6) + ' '*12 + 'MAC ADDRESS'.rjust(18) + ' '+ '</skyblue>'
            print(HTML(mac_table_title))
            print('-'*38)
            if mac_table == None:
                print('-' * 38)
                return
            for item in mac_table:
                print('|' +
                    str(item.get('id', 'NULL')).ljust(6) + '|**********|' +
                    str(item.get('mac')).rjust(18) + '|')
                print('-'*38)

        if self.view_name == 'Pikachu-mac':
            print(HTML('<skyblue>show RECORD SET list</skyblue>'))
            print('-' * 50)
            set_title = '<skyblue>' + ' ' + 'SET ID'.ljust(
                6) + ' ' * 12 + 'MAC ID'.center(6) + ' '*12 + 'SET STATUS'.rjust(10) + '</skyblue>'
            print(HTML(set_title))
            print('-' * 50)
            current_set_list = self._pquery()
            # print(current_set_list)
            for item in current_set_list:
                print('|' +
                    str(item.get('id')).ljust(6) + '|**********|' +
                    str(item.get('mac_id')).center(6) + '|**********|' +
                    self.status_dict[str(item.get('set_status'))].rjust(12) +
                    '|'
                )

        if self.view_name == 'Pikachu-mac-set':
            n = 3
            print(HTML('<skyblue>show RECORD list</skyblue>'))
            print('-' * 175)
            record_title = '<skyblue>' + ' '*n + 'RECORD ID'.center(10) + ' '*n + 'RECORD STATUS'.center(14) + ' '*n + ' SET ID'.center(6)\
            + ' '*n + 'SET STATUS'.center(10) + '  '*n + 'MISSION ID'.center(12) + ' '*n + 'OS NAME'.center(10) + ' '*n + 'MODE'.center(4) + ' '*n + 'OS ID'.center(5)\
            + ' '*n + 'MAC'.center(18) + ' ' + 'TYPE'.center(4) + ' '*n + 'START TIME'.center(20) + ' '*n + 'END TIME'.center(20) + '</skyblue>'
            print(HTML(record_title))
            print('-' * 175)
            record_list = self._pquery()
            for i in record_list:
                print('|' +
                str(i.get('ID')).center(12) + '|' + str(i.get('RECORD_STAT')).center(17) + '|' + str(i.get('SET_ID')).center(9)
                + '|' + str(i.get('SET_STAT')).center(14) + '|' + str(i.get('MISSION_ID')).center(14) + '|' + str(i.get('NAME')).center(12) + '|' + str(i.get('MODE')).center(8) + '|' + str(i.get('OS')).center(7)
                + '|' + str(i.get('MAC')).center(18) + '|' + str(i.get('TYPE')).center(6) + '|' + str(i.get('START_TIME')).center(22) + '|' + str(i.get('END_TIME')).center(22) +
                '|'
                )

    def padd(self, data):
        response = None
        if self.view_name == 'Pikachu':
            data = data[0]
            right_mac = True
            if len(data.split(':')) == 6:
                for i in data.split(':'):
                    if len(i) != 2:
                        right_mac = False
            else:
                right_mac = False
            if right_mac:
                # TODO 过滤重复数据添加
                response = self.pkcon.add(atype='add_mac', mac=data)
            else:
                print(
                    HTML('<violet>%s is illegal mac address!</violet>' % data))

        if self.view_name == 'Pikachu-mac':
            data = data[0]
            if str(data) not in ['-1', '1', '2', '3', '0']:
                print(HTML('<violet>%s is illegal Record status %s!</violet>' % data))
                return
            response = self.pkcon.add(
                atype='add_record_set', mac_id=self.mac_id, status=data)

        if self.view_name == 'Pikachu-mac-set':
            # 参数长度验证
            if len(data) < 2 or len(data) > 3:
                print(HTML('<violet>error:`add` need 2 or 3 parameters, but %s given!</violet>' %len(data)))
                return
            self.record_set_id

            status = '0'
            result = '0'
            if len(data) == 2:
                mission_id = data[0]
                type_id = self.type_id_dict.get(data[1])
            elif len(data) == 3:
                mission_id = data[0]
                status = data[1]
                type_id = self.type_id_dict.get(data[2])
            if status not in ['-1', '0', '1', '2']:
                print(HTML('<violet>error:Wrong status parameter,please check your input!</violet>'))
                return
            if not type_id:
                print(HTML('<violet>error:Unknow mission type,please check your input!</violet>'))
                return
            response = self.pkcon.add(atype='add_record', set_id=self.record_set_id,
            mission_id=mission_id, status=status, result=result, type_id=type_id)

        self._response(response)

    def pmodify(self, para):
        response = None
        if self.view_name == 'Pikachu-mac':
            if len(para) != 2:
                print(
                    HTML('<violet>%s is not a correct parameter</violet>' % para))
                return
            set_id = para[0]
            set_status = para[1]
            if set_status not in ['-1', '0', '1', '2', '3']:
                print(
                    HTML('<violet>%s is illegal Record status!</violet>' % set_status))
                return
            set_id_table = json.loads(self.pkcon.query(qtype='other', table='SET'))
            mac_id_table = [str(i.get('id')) for i in set_id_table if str(i.get('mac_id')) == self.mac_id]
            if str(set_id) in mac_id_table:
                response = self.pkcon.modify(mtype='modify_record_set', set_id=set_id, set_status=set_status)
                print('response', response)
            else:
                print(HTML('<violet>%s is not a correct set id!</violet>' % set_id))
                return
        if self.view_name == 'Pikachu-mac-set':
            # 参数合法性检查
            if len(para) < 3:
                print(
                    HTML(
                        '<violet>modify need at least 3 parameters, but %s get!</violet>'
                        % len(para)))
                return
            record_id = para[0]
            option = para[1]
            if para[0] not in [str(i.get('ID')) for i in self._pquery()]:
                print(
                    HTML('<violet>%s is not a correct record id!</violet>' %
                         record_id))
               	return
            if para[1] not in ['mission', 'status']:
                print(HTML('<violet>%s is not a correct option, Only support modify `mission` or `status`!</violet>'))
                return
            # 执行修改
            if option == 'mission':
                if len(para) < 4:
                    print(
                        HTML(
                            '<violet>modified mission need at least 4 parameters, but %s get!</violet>'
                            % len(para)))
                    return
                mission_id = para[2]
                type_id = self.type_id_dict.get(para[3])
                if not type_id:
                    print(
                        HTML(
                            '<violet>Wrong type %s specify!You could specify one from ["OS", "CV", "Stress"]</violet>' % para[3]
                        ))
                    return
                response = self.pkcon.modify(
                    mtype="modify_record",
                    record_id=record_id,
                    mission_id=mission_id,
                    type_id=type_id)

            elif option == 'status':
                if str(para[2]) not in ['-1', '0', '1', '2']:
                    print(
                        HTML('<violet>%s is illegal Record status!</violet>' %
                             str(para[2])))
                    return
                else:
                    status = para[2]
                response = self.pkcon.modify(mtype="modify_record", record_id=record_id, record_status=status)
        self._response(response)

    def pos(self):
        print(HTML('<skyblue>show MAC ADDRESS list</skyblue>'))
        os_table = json.loads(self.pkcon.query(qtype='other', table='OS'))
        print('-' * 56)
        set_title = '<skyblue>' + ' ' + 'MISSION ID'.ljust(6) +\
         ' ' * 15 + 'NAME'.center(6) + ' '*15 + 'MODE'.rjust(10) + '</skyblue>'
        print(HTML(set_title))
        print('-' * 56)
        for item in os_table:
            print('|' + str(item.get('ID')).ljust(6) + '|******|' +
                  str(item.get('OS')).center(22) + '|******|' +
                  str(item.get('MODE')).rjust(8) + '|')
            # print('-'*50)

    def _parse(self, command):
        if len(command.split()) >= 2:
            action = command.split()[0]
            if action not in self.current_view_option:
                return lambda: print(HTML('<violet>Unknow command!</violet>'))
            if action == 'add':
                para = command.split()[1:] # :type para: list
                return lambda :self.padd(para)
            if action == 'mac':
                para = command.split()[1]
                mac_table = self._pquery()
                mac_id_table = [str(i.get('id')) for i in mac_table]
                mac = ''
                if para in mac_id_table:
                    for i in mac_table:
                        if str(i.get('id')) == para:
                            mac = i.get('mac')
                    para = (para, mac)
                    return lambda :self.record_set_view(para)
                else:
                    return lambda :print(HTML('<violet>%s is not a correct mac id!</violet>' % para))
            if action == 'modify':
                para = command.split()[1:]
                return lambda :self.pmodify(para) # :type para: list
            if action == 'set':
                para = command.split()[1]
                record_set = self._pquery()
                set_id_table = [str(i.get('id')) for i in record_set]
                if para in set_id_table:
                    return lambda : self.record_view(para)
                else:
                    return lambda : print(HTML('<violet>%s is not a correct set id!</violet>' %para))

        elif command not in self.current_view_option:
            return lambda: print(HTML('<violet>Unknow command!</violet>'))
        elif command == 'os':
            return self.pos
        elif command.find('exit') != -1:
            return self.pexit
        elif command.find('show') != -1:
            return self.pshow
        elif command.find('help') != -1:
            return self.phelp
        else:
            return lambda: print(HTML('<violet>Unknow command!</violet>'))

    def pikachu_view(self):
        self.view_name = 'Pikachu'
        self.current_view = 'Pikachu'
        self.current_view_option = ['exit', 'show', 'add', 'mac', 'help']
        self.help_message = '''<dodgerblue>PikachuClient 是一个用于配置 Lightning OS 自动化测试系统的命令行工具.</dodgerblue>\n
        选项:\n
    show    列出MAC地址列表,可以从该表查阅目标mac地址所对应的id.
    add     添加一个mac地址,当有新机台需要加入测试时,\n           使用该选项将其mac地址加入列表,格式为:add aa:bb:cc:dd:ee:ff.
    mac     选择mac id进入其record set视图,在record set视图,可以管理测试集,\n           格式为:mac mac_id
    exit    退出命令行.
    help    显示帮助信息.
        '''

    def record_set_view(self, mac_id):
        self.mac_id = mac_id[0]
        self.mac = mac_id[1]
        self.view_name = 'Pikachu-mac'
        self.current_view = 'Pikachu-mac%s %s' % (self.mac_id, self.mac)
        self.current_view_option = ['show', 'exit', 'help', 'add', 'modify', 'set']
        self.help_message = '''<dodgerblue>Record Set视图用于管理测试集,可以为一台机器(mac)创建多个测试集,但同一时间请保证只有一个处于running状态.</dodgerblue>\n
    选项:\n
    show    列出列出测试集信息,包括Record set ID, MAC ID,Record set status
    add     新建一个测试集(record set),并且可以定义其状态,\n           格式为:add [-1, 0, 1, 2] -1:手动关闭 0:未开始 1:正在执行 2:完成
    set      选择测试集ID(set id)进入其测试项(record)视图,在record视图,可以\n           对该测试集中的测试项进行管理,命令格式为:set set_id
    modify   修改测试集(record set)的状态,modify set_id  status[-1, 0, 1, 2],\n           状态同add项帮助信息
    exit     退出当前视图.
    help     显示帮助信息.
        '''

    def record_view(self, record_set_id):
        self.record_set_id = record_set_id
        self.view_name = 'Pikachu-mac-set'
        self.current_view = 'Pikachu-mac%s %s-set%s' % (self.mac_id, self.mac, self.record_set_id)
        self.current_view_option = ['exit', 'help', 'show', 'add', 'os', 'modify']
        self.help_message = '''<dodgerblue>Record视图用于管理测试项,一个测试集中会存在多个测试项,测试顺序依据record id升序排列.</dodgerblue>\n
        选项:\n
    show    列出列出测试集信息,包括Record set ID, MAC ID,Record set status.
    os      列出OS列表,可以查看OS id, Misson id, mode信息.
    add     新建一个测试项(record),并且可以定义其状态,任务(mission id),任务类型(type),\n           格式为:add mission_id status[-1, 0, 1, 2] type['OS', 'CV', 'Stress']\n           -1:手动关闭 0:未开始 1:正在执行 2:完成 可直接add mission_id type\n           添加status 0的Record\n
    modify  修改测试项(record)的状态(record status)任务(mission id),\n           modify record_id status|mission status_id|(mission_id, mission_type),\n           状态同add项帮助信息
    exit    退出当前视图.
    help    显示帮助信息.
        '''

    def mainloop(self):
        self.view_stack = []
        self.pikachu_view()
        while True:
            PCompleter = WordCompleter(self.current_view_option, ignore_case=True)
            command = prompt(ANSI('\033[36m<%s> \033[0m' % self.current_view),
                            history=FileHistory('history.txt'),
                            auto_suggest=AutoSuggestFromHistory(),
                            completer=PCompleter,
                            )
            if command:
                self._parse(command)()


if __name__ == "__main__":
    pi = PikachuView()
    try:
        pi.mainloop()
    except KeyboardInterrupt:
        print('Exit')
        exit()
