#!/usr/bin/env python
#-*-coding=utf-8-*-
import ipxelib

db = ipxelib.MyDB()
res = db.get_query('00:0C:29:9D:36:56')
print(res)
db.close()
