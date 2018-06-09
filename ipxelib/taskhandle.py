import logging
import mysql.connector
import mysql.connector.errors
import json

logging.basicConfig(level=logging.DEBUG)

class IpxeError(Exception):
    def __init__(self, msg, code):
        self.code = str(code)
        self.msg = msg
    
    def info(self):
        return {
            'type': 'Error',
            'data':{
                'msg': self.msg,
                'code': self.code,
                'errortype': self.__class__.__name__
            }
        }

class IpxeTypeError(TypeError, IpxeError):
    def __init__(self, msg, code='6'):
        super(IpxeTypeError, self).__init__(msg, code)

class UnknownMissionType(IpxeError):
    def __init__(self, msg, code='5'):
        super(UnknownMissionType, self).__init__(msg, code)

class EmptyMacList(IpxeError):
    def __init__(self, msg, code='4'):
        super(EmptyMacList, self).__init__(msg, code)

class MyDBQueryError(IpxeError):
    def __init__(self, msg, code='3'):
        super(MyDBQueryError, self).__init__(msg, code)

class NoCurrentTask(IpxeError):
    def __init__(self, msg, code='2'):
        super(NoCurrentTask, self).__init__(msg, code)

class UnknownError(IpxeError):
    def __init__(self, msg, code='1'):
        super(UnknownError, self).__init__(msg, code)

#---------------------------------------------------------------------------
# 数据库连接与查询
#---------------------------------------------------------------------------
class MyDB(object):
    """
    连接mysql数据库并提供iPXE所需SQL语句
    """
    def __init__(self, cursorclass=mysql.connector.cursor.MySQLCursorDict):
        """
        建立数据库连接
        """
        config = {
            'host': '192.168.1.1',
            'port': 3306,
            'user': 'root',
            'password': '',
            'database': 'pxe'
        }

        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor(cursor_class=cursorclass)

    def execute(self, s: str) -> dict:
        """
        直接执行SQL语句
        """
        self.cursor.execute(s)
        try:
            values = self.cursor.fetchall()
        except mysql.connector.errors.InterfaceError:
            values = {'rowcount': self.cursor.rowcount}
        if values:
            self.conn.commit()
        logging.debug('execute:%s' %values)
        return values

    def post_query(self, mac: str) -> dict:
        """
        iPXE Client完成系统安装后，iPXE Server收到来自client的POST请求，执行该方法
        """
        logging.debug(mac)
        self.cursor.execute('select record.id as re_id,status from record inner join mac_addr on (record.mac_id=mac_addr.id) where mac = "'+ mac + '" and status <> 2 order by record.id')
        values = self.cursor.fetchall()
        logging.debug(values)
        return values

    def get_query(self, mac: str) -> dict:
        """
        iPXE Client执行preboot or efipreboot向iPXE Server发出GET请求，运行此方法返回查询结果Record字典
        """
        logging.debug(mac)
        # self.cursor.execute('select * from record inner join mac_addr on (record.mac_id=mac_addr.id) inner join os_mission on (os_mission.id=record.mission_id) inner join os on (os.id=os_mission.os_id) where mac = "' + mac + '" and status <> 2 order by record.id')
        # columns = self.cursor.column_names
        self.cursor.execute('select * from os_install_mission where mac = "%s"' %mac)
        values = self.cursor.fetchall()
        logging.debug(values)
        return values

    def close(self):
        """
        关闭数据库连接
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()  

#---------------------------------------------------------------------------
# 任务控制
#---------------------------------------------------------------------------
class BasicHandler(object):
    """
    任务控制器的模板类,依据SUT MAC地址列表对比pxe数据库中的current_task表中所有MAC地址,
    找到两者交集,利用该MAC地址查询current_task表获得对应record id，使用record id进行任务管理
    """
    def __init__(self, mac_list: list, blacklist=None):
        self.mydb = MyDB()
        logging.debug('%s.mac_list:  %s' %(self.__class__, mac_list))
        if isinstance(mac_list, list):    # mac_list类型检查,mac_list为list类型
            self.mac_list = [i.upper() for i in mac_list]      # 全部转换为大写
            logging.debug('%s.mac_list:  %s' %(self.__class__, self.mac_list))
        else:    # 若mac_list非list类型则抛出TypeError异常
            raise TypeError('mac_list should be a list!')

        # TODO MAC地址过滤,滤除无效MAC,blacklist的MAC地址
    
        if self.mac_list:   # 检查mac_list为非空,从current_task中查询所有mac地址并取其与mac_list的交集(list)
            self.all_mac_list = [i.get('mac', None) for i in self.mydb.execute('SELECT mac FROM current_task;')]
            mac = list(set(self.mac_list) & set(self.all_mac_list))
            if len(mac) == 1:    #交集列表元素有且仅有1
                self.mac = mac[0]
                record_id = self.mydb.execute('SELECT record_id FROM current_task WHERE current_task.mac = "%s";' %self.mac)    #使用交集唯一mac查询pxe数据库current_task表,获取record_id
                if len(record_id) == 1:    # 一个mac在current_task中仅可查到唯一
                    self.record_id = [r.get('record_id', None) for r in record_id][0]    # Get Record id From pxe.current_task
                else:   # 若mac在current_task查询非唯一或出现查询错误,抛出MyDBQuerryError异常
                    raise MyDBQueryError('query mac failed! taskhandle->maclist:%s ;all_mac_list:%s' % (mac_list,self.all_mac_list))
            elif len(mac) == 0:    #交集为空,抛出NoCurrentTask异常
                raise  NoCurrentTask('Get MAC from pxe.current_task table: %s ' %mac)
            else:    #交集非空且不唯一,或出现查询错误,抛出MyDBQuerryError异常
                raise  MyDBQueryError('Get MAC from pxe.current_task table: %s ' %mac)
        else:    # 若mac_list为空抛出emptyMacList异常
            raise EmptyMacList('mac_list: %s ' %self.mac_list)

    def close(self):
        """
        关闭数据库连接
        """
        self.mydb.close()
     
    def _mac_blackhole(self, blacklist):
        # 过滤MAC地址
        pass
    
    def prepare(self):
        # 环境准备
        pass
    
    def begin(self):
        # 任务开始
        pass

    def complete(self):
        # 任务完成
        pass


class TaskHandler(BasicHandler):
    def __init__(self, data, blacklist=None):
        mac_list = data['mac_list']
        super(TaskHandler, self).__init__(mac_list, blacklist)
    
    def _query_task(self):
        return self.mydb.execute('SELECT type, record_id AS id, set_id, mac, record_status as status FROM current_task WHERE current_task.mac = "%s"' % self.mac)

    def _convert2json(self, query_dict):
        task_dict = {
        'type': query_dict[0].get('type', 'None'), 
        'data': {
            'id': query_dict[0].get('id', 'None'),
            'mac': query_dict[0].get('mac', 'None'),
            'set_id': query_dict[0].get('set_id', 'None'),
            'status': query_dict[0].get('status', 'None')
        }
        }
        return json.dumps(task_dict)

    def start(self):
        return self._convert2json(self._query_task())


class OSInstallHandler(BasicHandler):
    """处理OS安装任务
    
    OS安装任务控制器使用record id从os_install_mission表中查询安装所需参数
    os_name, kernel_name, initrd_name, vmlinuz_args
    并依据Record id修改record表中status值
    """
    def __init__(self, data, blacklist=None):
        self.data = data
        mac_list = self.data['mac_list']
        super(OSInstallHandler, self).__init__(mac_list, blacklist)
        

    def begin(self):
        '''
        开始安装,使用record id修改record表中对应项的status值为1
        '''
        ret = self.mydb.execute('UPDATE record SET status = 1 WHERE id = %s' %self.record_id)
        logging.debug(ret)

    def complete(self):
        """
        安装完成,使用record id修改record表中对应项的status值为2
        """
        ret = self.mydb.execute('UPDATE record SET status = 2 WHERE id = %s' %self.record_id)
        logging.debug(ret)

    def _os_param(self):
        # 从os_install_mission查询OS Install参数
        param = self.mydb.execute('SELECT * FROM os_install_mission WHERE id = %s' %self.record_id)
        logging.debug(param)
        return param

    def _convert2json(self, query_dict):
        task_dict = {
        'type': 'OS', 
        'data': {
            'id': query_dict[0].get('id', 'None'),
            'os_id': query_dict[0].get('os_id', 'None'),
            'os_name': query_dict[0].get('os_name', 'None'),
            'status': query_dict[0].get('record_status', 'None'),
            'mode': query_dict[0].get('mode', 'None')
        }
        }
        return json.dumps(task_dict)

    def start(self):
        if self.data['status'] == 2:
            # 安装完成
            self.complete()
            return None
        if self.data['status'] == 1:
            # TODO 系统安装过程中,判断message是否为空,空则为Ipxe安装请求,非空则OS环境部署错误
            if self.data['message'] == None:
                self.begin()
            else:
                pass
            return None
        if self.data['status'] == 0:
            # 返回Next OS 安装信息
            return self._convert2json(self._os_param())


class CVHandler(BasicHandler):
    def __init__(self, mac_list, blacklist=None):
        super(CVHandler, self).__init__(mac_list, blacklist)



class StressHandler(BasicHandler):
    def __init__(self, mac_list, blacklist=None):
        super(StressHandler, self).__init__(mac_list, blacklist)
        pass


def task(mission_dict, blacklist=None):
    print(mission_dict)
    if not isinstance(mission_dict, dict):
        raise TypeError('mission_dict show be dict type, but get %s' %type(mission_dict))

    mission_type_dict = {
        'OS': OSInstallHandler,
        'CV': CVHandler,
        'Stress': StressHandler,
        'GetTask': TaskHandler
    }
    if mission_dict['type'] in mission_type_dict:
        return mission_type_dict[mission_dict['type']](mission_dict['data'], blacklist=blacklist)
    else:
        raise  UnknownMissionType('There is No  Misson for %s' %mission_dict['type'])

if __name__ == "__main__":
    print(TaskHandler(['00:A0:C9:00:00:03']).__class__)
    # mac_list = ['D6:97:60:F1:54:4A', 'D6:97:60:F1:54:4E', '00:A0:C9:00:00:03']
    # ts = task('Task', mac_list)
    # print(ts.get_task())
    # os = task('OS', mac_list)
    # print(os.record_id)
    # os.begin()
    # os.complete()
    # os.close()
    # print('END')
