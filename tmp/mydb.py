#!/usr/bin/python36

import mysql.connector
import logging

logging.basicConfig(level=logging.INFO)

class MyDB(object):

    def __init__(self):
        self.conn = mysql.connector.connect(host='192.168.1.1', port=3306, user='root', password='', database='pxe')
        self.cursor = self.conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)

    def post_query(self, mac):
        logging.debug(mac)
        self.cursor.execute('select record.id as re_id,status from record inner join mac_addr on (record.mac_id=mac_addr.id) where mac = "'+ mac + '" and status <> 2 order by record.id')
        values = self.cursor.fetchall()
        return values[0]

    def get_query(self, mac):
        logging.debug(mac)
        self.cursor.execute('select * from record inner join mac_addr on (record.mac_id=mac_addr.id) inner join os_mission on (os_mission.id=record.mission_id) inner join os on (os.id=os_mission.id) where mac = "' + mac + '" and status <> 2 order by record.id')
        columns = self.cursor.column_names
        values = self.cursor.fetchall()
        logging.debug(values)
        return values[0]

    def close(self):
        self.cursor.close()
        self.conn.close()


class Record(object):

    def __init__(self, query_result):
        self.status = query_result['status']
        self.mode_id = query_result['mode_id']
        self.mac_id = query_result['mac_id']
        self.name = query_result['name']
        self.start_time = query_result['start_time']
        self.args = query_result['args']
        self.initrd_name = query_result['initrd_name']
        self.mission_id = query_result['mission_id']
        self.mac = query_result['mac']
        self.os_id = query_result['os_id']
        self.kernel_name = query_result['kernel_name']
        self.end_time = query_result['end_time']
        self.id = query_result['id']
        self.result = query_result['result']

    def __getitem__(self, key):
        return self.__getattribute__(key)


if __name__ == '__main__':
    db = MyDB()
    values = db.get_query('00:0C:29:F5:20:5C')
    r = Record(values)
    for key in dir(r):
        print(r[key])
    db.close()

