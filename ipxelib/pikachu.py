#!/usr/bin/env python
# -*-coding:utf-8-*-

from ipxelib.taskhandle import MyDB
import json
import datetime


class JsonExtendEncoder(json.JSONEncoder):
    """This class provide an extension to json serialization for datetime/date.
    """
    def default(self, o):
        """provid a interface for datatime/date
        """
        if isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, 0)


class PikachuServer(object):
    def __init__(self):
        self.db = MyDB()
    
    def query(self, para):
        """para格式

        para = {
            'type': 'record',
            'data':{'mac_address': [],
                    'method': 'all'}
        }
        """
        # 查询record信息
        if para['type'] == 'record':
            mac_list = para['data']['mac_address']
            method = para['data']['method']
            type_dict = {
                'current': 'pikachu_current_task',
                'all': 'pikachu_user_view',
                'history': '',
                'next': ''
                }
            # 有指定mac地址,查询指定mac
            if '' not in mac_list:
                mac_specify = ' or '.join(["mac='"+mac.upper()+"'" for mac in mac_list])
                instruction = "SELECT * FROM %s WHERE %s ORDER BY `ID`, `SET_ID`;" %(type_dict.get(method), mac_specify)
                print(instruction)
            # 未指定mac地址,查询所有mac
            else:
                instruction = "SELECT * FROM %s ORDER BY `SET_ID`, `ID`;" % type_dict.get(method)
                print(instruction)
            return json.dumps(self.db.execute(instruction), cls=JsonExtendEncoder)

        # 查询其他table
        elif para['type'] == 'other':
            table_name_dict= {
                'OS': 'pikachu_os',
                'Stress': 'Stress',
                'CV': 'CV',
                'MAC': 'mac_addr',
                'SET': 'record_set'
            }
            instruction = 'SELECT * FROM %s;' % table_name_dict[para['data']['table_name']]
            print(instruction)
            return json.dumps(self.db.execute(instruction))

    def add(self, para):
        """添加任务
        """
        # 插入mac地址到mac_addr表
        if para['type'] == 'add_mac':
            instruction = "INSERT INTO mac_addr(mac) VALUES('{mac}');".format(mac=para['data']['mac'].upper())
            return json.dumps(self.db.execute(instruction))

        # 插入record到record表       
        elif para['type'] == 'add_record':
            instruction = "INSERT INTO record(set_id, mission_id, status, result, type) VALUES({set_id}, {mission_id}, {status}, {result}, {type_id});".format(set_id=para['data']['set_id'], mission_id=para['data']['mission_id'], status=para['data']['status'], result=para['data']['result'], type_id=para['data']['type_id'])
            return json.dumps(self.db.execute(instruction))
    
        # 插入record set到record_set表
        elif para['type'] == 'add_record_set':
            instruction = "INSERT INTO record_set(mac_id, set_status) VALUES({mac_id}, {status});".format(mac_id=para['data']['mac_id'], status=para['data']['status'])
            print(instruction)
            return json.dumps(self.db.execute(instruction))

        
    def delete(self, para):
        pass
        
    def modify(self, para):
        # 修改record的status,需要data中含有status与record_id参数
        if para['type'] == 'modify_record':
            status =  para['data'].get('status')
            record_id = para['data'].get('id')
            type_id = para['data'].get('type_id')
            mission_id = para['data'].get('mission_id')
            if mission_id == None:
                instruction = "UPDATE `record` SET `status`={status} WHERE `record`.`id`={record_id};".format(status=status, record_id=record_id)
            else:   
                instruction = "UPDATE `record` SET `mission_id`={mission_id}, `type`={type_id} WHERE `record`.`id`={record_id};".format(mission_id=mission_id, type_id=type_id, record_id=record_id)
            return json.dumps(self.db.execute(instruction))

        # 修改record_set的status,需要data中含有status与set_id参数
        elif para['type'] == 'modify_record_set':
            instruction = "UPDATE `record_set` SET `set_status`={status} WHERE `record_set`.`id`={set_id};".format(status=para['data']['status'], set_id=para['data']['id'])
            return json.dumps(self.db.execute(instruction))
    
    def support(self, method):
        if method == 'query':
            return ['record', 'other']
        elif method == 'add':
            return ['add_mac', 'add_record', 'add_record_set']
        elif method == 'delete':
            return []
        elif method == 'modify':
            return ['modify_record', 'modify_record_set']

    def close(self):
        self.db.close()
