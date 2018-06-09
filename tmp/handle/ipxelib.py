#!/usr/bin/env python
#-*-coding=utf-8-*-

try:
    import mysql.connector
    import mysql.connector.errors
except Exception:
    pass
import logging
import copy

logging.basicConfig(level=logging.INFO)


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
        logging.debug(values)
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
        self.cursor.execute('SELECT * FROM os_install_mission WHERE id = (SELECT record_id FROM current_task WHERE current_task.mac_id = \'%s\')' %mac)
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
# 查询结果处理
#---------------------------------------------------------------------------

class Record(object):

    """
    将record字典转换为Record类，对应字典的键值转换为Record实例的属性
    """
    def __init__(self, query_result: dict, MyDBObject=None):
        self.MyDBObject = MyDBObject
        self.query_result = dict(query_result)

    def __getitem__(self, key: str) -> str:
        """
        支持[]运算符，可以使用record['status']获取到record的属性值
        """
        # return self.__getattribute__(key)
        return self.query_result[key]

    def __getattr__(self, item: str) -> str:
        """
        支持属性获取，可以使用record.status获取到record的属性值
        """
        return self.query_result[item]

    def __setattr__(self, name, value):
        # if self.MyDBObject:
        #     self.MyDBObject.execute('')
        # TODO
        pass

    def get_key(self) -> list:
        """
        返回record的全部键
        """
        return list(self.query_result.keys())

#---------------------------------------------------------------------------
# 生成ipxe脚本
#---------------------------------------------------------------------------

class IpxeString(str):
    """
    生成标准格式iPXE Script
    """
    
    def __init__(self, mystr: str = '#!ipxe'):
        """
        定义IpxeString第一行_mystr属性
        _sub_string_list属性为IpxeString Script的列表形式，按照列表元素逐行排列
        默认值#!ipxe
        """
        super(IpxeString, self).__init__()
        self._mystr = mystr
        self._sub_string_list = []

    def append_substr(self, sub_string: str) -> None:
        """
        添加一行IpxeString Script，参数sub_string为str类型，保存在_sub_string_list的尾部
        """
        self._sub_string_list.append(sub_string)
    
    def insert_substr(self, index: int, sub_string: str) -> None:
        """
        插入一行IpxeString Script，参数index指明插入位置，参数sub_string为待插入字符串
        """
        self._sub_string_list.insert(index, sub_string)
    
    def getstr(self, s: str = '\n') -> str:
        """
        生成ipxe script字符串，参数s指定合成_sub_string_list列表的分隔符，默认使用"\n"
        """
        ipxe_string = ''
        _sub_string_list = ''
        _sub_string_list = copy.deepcopy(self._sub_string_list)
        _sub_string_list.insert(0, self._mystr)
        ipxe_string = s.join(_sub_string_list)
        return ipxe_string

    def get_str_list(self) -> list:
        """
        返回IpxeString的_sub_string_list属性，该属性为IpxeString Script的列表形式
        """
        return self._sub_string_list
    
    def __str__(self):
        return self.getstr()
    
    def __add__(self, other) -> object:
        """
        使用 "+" 运算符添加IpxeString语句
        示例：
        ipxe_string = IpxeString()
        ipxe_string + 'echo hello iPXE'
        效果等同于ipxe_string.append_substr('echo hello iPXE')
        """
        self._sub_string_list.append(other)
        return self

    def __sub__(self, other) -> object:
        """
        使用 "-" 运算符删除IpxeString语句
        示例：
        ipxe_string = IpxeString()
        ipxe_string + 'echo hello iPXE'
        ipxe_string - "echo hello iPXE"
        或
        ipxe_string - 0
        """
        if type(other) == str:
            self._sub_string_list.remove(other)
        if type(other) == int:
            del self._sub_string_list[other]
        return self


class Script(object):
    """
    生成iPXE启动脚本
    """
    def __init__(self):
        pass

    @classmethod
    def ipxe_script(self, os_name: str, kernel_name: str, initrd_name: str, vmlinuz_args: str) -> str:
        """
        生成iPXE标准模式启动脚本
        """
        efi = IpxeString()
        efi + 'set os %s' %os_name
        efi + 'set retry:int32 0'
        efi + 'set path http://192.168.1.1/image/${os}' 
        efi + 'set image tftp://192.168.1.1/Image/${os}'
        efi + 'set kernel ${image}/%s' %kernel_name
        efi + 'set initrd ${image}/%s' %initrd_name
        efi + 'set args vmlinuz initrd=initrd %s' %vmlinuz_args
        efi + 'goto install'
        efi + ':fail'
        efi + '  shell'
        efi + ':retry'
        efi + '  inc retry'
        efi + '  iseq ${retry} 4 || echo Retrying download ${retry} times... ||'
        efi + '  iseq ${retry} 4 && echo Download Failed && shell ||'
        efi + '  sleep 3'
        efi + '  iseq ${retry} 4 || goto install || goto fail ||'
        efi + ':install'
        efi + '  echo Starting Installer'
        efi + '  echo ${kernel}'
        efi + '  echo ${initrd}'
        efi + '  initrd -n initrd --timeout 200 ${initrd} || goto retry'
        efi + '  kernel -n vmlinuz --timeout 200 ${kernel} || goto retry'
        efi + '  imgargs vmlinuz initrd=initrd %s' %vmlinuz_args
        efi + '  boot || goto fail'
        return efi.getstr()
    
    @classmethod
    def grub_script(self, os_name: str) -> str:
        """
        生成iPXE UEFI模式grub兼容方案启动脚本
        """
        efi_grub = IpxeString()
        efi_grub + 'set os %s' %os_name
        efi_grub + 'set retry:int32 0'
        efi_grub + 'set path http://192.168.1.1/grub/${os}' 
        efi_grub + 'set kernel ${path}/${os}.efi'
        efi_grub + 'goto install'
        efi_grub + ':fail'
        efi_grub + '  shell'
        efi_grub + ':retry'
        efi_grub + '  inc retry'
        efi_grub + '  iseq ${retry} 4 || echo Retrying download ${retry} times... ||'
        efi_grub + '  iseq ${retry} 4 && echo Download Failed && shell ||'
        efi_grub + '  sleep 3'
        efi_grub + '  iseq ${retry} 4 || goto install || goto fail ||'
        efi_grub + ':install'
        efi_grub + '  echo Starting Installer'
        efi_grub + '  echo ${kernel}'
        efi_grub + '  kernel -n vmlinuz --timeout 200 ${kernel} || goto retry'
        efi_grub + '  boot || goto fail'
        return efi_grub.getstr()

    @classmethod
    def install_miniconda(self):
        """
        生成Miniconda安装脚本
        """        
        config = IpxeString('#!/bin/sh')
        config + '#set -e'
        config + 'CONDA_PATH="http://192.168.1.1/tools/Miniconda3.sh"'
        config + 'download() {'
        config + '  wget -N $CONDA_PATH -O $(basename ${CONDA_PATH})'
        config + '}'
        config + 'set_mode() {'
        config + '  chmod 755 $(basename ${CONDA_PATH})'
        config + '}'
        config + 'do_install() {'
        config + 'sh $(basename ${CONDA_PATH}) -bf'
        config + '# export PATH="/root/anaconda3/bin:$PATH"'
        config + '# declare -x PATH="/root/anaconda3/bin:$PATH"'
        config + 'source /root/.bashrc'
        config + '}'
        config + 'download || echo "Download Failed"'
        config + 'set_mode || echo "Change Mode Failed"'
        config + 'do_install || echo "Install Failed"'
        return config.getstr()


