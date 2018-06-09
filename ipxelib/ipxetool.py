#!/usr/bin/env python
#-*-coding=utf-8-*-

import logging
import copy

logging.basicConfig(level=logging.DEBUG)

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
        if item in self.query_result:
            return self.query_result[item]
        else:
            return None


    def __setattr__(self, name, value):
        # if self.MyDBObject:
        #     self.MyDBObject.execute('')
        # TODO
        return super(Record, self).__setattr__(name, value)


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
        efi + '  initrd -n initrd --timeout 10000 ${initrd} || goto retry'
        efi + '  kernel -n vmlinuz --timeout 10000 ${kernel} || goto retry'
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
        efi_grub + '  kernel -n vmlinuz --timeout 10000 ${kernel} || goto retry'
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
        config + 'echo "export PATH="/root/anaconda3/bin:$PATH" > /root/.bashrc'
        config + '# declare -x PATH="/root/anaconda3/bin:$PATH"'
        config + 'source /root/.bashrc'
        config + '}'
        config + 'download || echo "Download Failed"'
        config + 'set_mode || echo "Change Mode Failed"'
        config + 'do_install || echo "Install Failed"'
        return config.getstr()

    @classmethod
    def read_from_file(self, filename):
        with open(filename, 'r') as f:
            data = f.read()
            return data

    @classmethod
    def boot_from_hd(self):
        hd = IpxeString()
        hd + 'echo OS Install Status is code 1, Boot From Local Disk... '
        hd + 'sanboot --no-describe --drive 0xff'
        return hd.getstr()

    @classmethod
    def task_explain(self):
        task_exp = """
        <h1>Lightning Server与Tasktracker通信格式定义</h1>
        tasktracker优先使用curl发送http请求,在缺失curl环境使用urlib<br/>
        <b>curl</b>参数为 <b>curl -sSL -H "Content-type:application/json"</b><br/>
        为兼容curl发送Json,格式采用单引号包含的Json,其内容为字典格式转换而来<br/>
        字典内部字符串格式为双引号<br/>
        <i>type</i>值为任务:<i>"GetTask","OS","CV","Stress"</i><br/>
        data值为字典dict类型,字典中必须包含<i>"mac_list"</i>键<br/>
        <i>"mac_list"</i>值为列表,元素为双引号包裹的MAC地址字符串<br/>
        '{<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;"type"："OS",<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;"data": {<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"mac_list": ["11:22:33:44:55:66:77"],<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"status": 0<br/>
        &nbsp;&nbsp;&nbsp;&nbsp;}<br/>
        }'<br/>
        """
        return task_exp
        

if __name__ == "__main__":
    s = Script.read_from_file('/pxe/repertory/tools/env.sh')
    print(s)
