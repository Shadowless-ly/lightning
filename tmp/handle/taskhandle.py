import ipxelib
import logging

logging.basicConfig(level=logging.DEBUG)

class EmptyMacList(Exception):pass
class MyDBQueryError(Exception):pass

#---------------------------------------------------------------------------
# 任务控制
#---------------------------------------------------------------------------
class BasicHandler(object):
    """
    任务控制器的模板类,依据SUT MAC地址列表对比pxe数据库中的current_task表中所有MAC地址,
    找到两者交集,利用该MAC地址查询current_task表获得对应record id，使用record id进行任务管理
    """
    def __init__(self, mac_list, blacklist=None):
        self.mydb = ipxelib.MyDB()
        self.mac_list = mac_list
        # TODO MAC地址过滤,滤除无效MAC,blacklist的MAC地址,转换MAC地址格式
        if self.mac_list:
            self.all_mac_list = [i.get('mac', None) for i in self.mydb.execute('SELECT mac FROM current_task;')]
            mac = list(set(mac_list) & set(self.all_mac_list))
            if len(mac) == 1:
                self.mac = mac[0]    # Get MAC from pxe.current_task
                record_id = self.mydb.execute('SELECT record_id FROM current_task WHERE current_task.mac = "%s";' %self.mac)
                if len(record_id) == 1:
                    self.record_id = [r.get('record_id', None) for r in record_id][0]    # Get Record id From pxe.current_task
                else:
                    logging.info('Get Record id From pxe.current_task: %s' %record_id)
                    raise MyDBQueryError()
            else:
                logging.info('Get MAC from pxe.current_task table: %s ' %mac)
                raise  MyDBQueryError()
        else:
            logging.info('mac_list: %s ' %self.mac_list)
            raise EmptyMacList()

    def close(self):
        """
        关闭数据库连接
        """
        self.mydb.close()
     
    def _mac_blackhole(self, blacklist):
        # TODO 过滤MAC地址
        pass
    
    def prepare(self):
        # TODO 环境准备
        pass
    
    def begin(self):
        # TODO 任务开始
        pass

    def complete(self):
        # TODO 任务完成
        pass


class OSInstallHandler(BasicHandler):
    """
    OS安装任务控制器使用record id从os_install_mission表中查询安装所需参数
    os_name, kernel_name, initrd_name, vmlinuz_args
    并依据Record id修改record表中status值
    """
    def __init__(self, mac_list, blacklist=None):
        super(OSInstallHandler, self).__init__(mac_list, blacklist)
        self.param = self.mydb.execute('SELECT * FROM os_install_mission WHERE id = %s' %self.record_id)    # 从os_install_mission查询OS Install参数

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


class CVHandler(BasicHandler):
    def __init__(self, mac_list, blacklist=None):
        super(CVHandler, self).__init__(mac_list, blacklist)
    


class StressHandler(BasicHandler):
    def __init__(self, mac_list, blacklist=None):
        super(StressHandler, self).__init__(mac_list, blacklist)
        pass


def task(mission_type, mac_list, blacklist=None):
    mission_type_dict = {
        'OS': OSInstallHandler,
        'CV': CVHandler,
        'Stress': StressHandler
    }
    if mission_type in mission_type_dict:
        return mission_type_dict[mission_type](mac_list, blacklist=blacklist)
    else:
        return None

if __name__ == "__main__":
    mac_list = ['D6:97:60:F1:54:4A', 'D6:97:60:F1:54:4E', '00:A0:C9:00:00:03']
    os = task('OS', mac_list)
    print(os.record_id)
    os.begin()
    os.complete()
    os.close()
    print('END')
