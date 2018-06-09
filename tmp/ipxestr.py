#!/usr/bin/env python
# encoding: utf-8
import copy

class IpxeString(str):
    
    def __init__(self, _mystr = '#!ipxe'):
        super(IpxeString, self).__init__()
        self._mystr = _mystr
        self._sub_string_list = []

    def append_substr(self, sub_string):
        self._sub_string_list.append(sub_string)
    
    def insert_substr(self, index, sub_string):
        self._sub_string_list.insert(index, sub_string)
    
    def getstr(self, s = '\n'):
        ipxe_string = ''
        _sub_string_list = ''
        _sub_string_list = copy.deepcopy(self._sub_string_list)
        _sub_string_list.insert(0, self._mystr)
        ipxe_string = s.join(_sub_string_list)
        return ipxe_string

    def get_str_list(self):
        return self._sub_string_list
    
    def __str__(self):
        return self.getstr()
    
    def __add__(self, other):
        self._sub_string_list.append(other)
        return self

    def __sub__(self, other):
        if type(other) == str:
            self._sub_string_list.remove(other)
        if type(other) == int:
            del self._sub_string_list[other]
        return self
