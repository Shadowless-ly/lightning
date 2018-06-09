# from multiprocessing import Process
# from urllib import request

# def open(url):
#     with request.urlopen(url) as f:
#         data = f.read()
#         print('Status', f.status, f.reason)
#         for k, v in f.getheaders():
#             print('%s: %s' %(k, v))
#         print('Data:', data.decode('utf-8'))

# def main():
#     n = 1
#     while n < 100:
#         p1 = Process(target=open, args=('http://localhost/auto/uefi?mac=a1:2b:3c:4d:5e:6f',))
#         p2 = Process(target=open, args=('http://localhost/auto/legacy?mac=a1:2b:3c:4d:5e:6f',))
#         p3 = Process(target=open, args=('http://localhost/ipxe/boot.php',))
#         p4 = Process(target=open, args=('http://localhost/auto/uefi?mac=00:0C:29:F5:20:5C',))
#         p5 = Process(target=open, args=('http://localhost/auto/legacy?mac=00:0C:29:F5:20:5C',))
#         p1.start()
#         p2.start()
#         p3.start()
#         p4.start()
#         p5.start()
#         p1.join()
#         p2.join()
#         p3.join()
#         p4.join()
#         p5.join()
#         n += 1
#         print('n: %s' %n)

# def test():
#     from ipxelib import IpxeString
#     config = IpxeString('#!/bin/sh')
#     config + 'set -e'
#     config + 'download() {wget -N $CONDA_PATH -O $(basename ${CONDA_PATH})}'
#     config + 'set_mode() {chmod 755 $(basename ${CONDA_PATH})}'
#     config + 'do_install() {sh $(basename ${CONDA_PATH}) -bf; source /root/.bashrc}'
#     config + 'download || echo "Download Failed"'
#     config + 'set_mode || echo "Change Mode Failed"'
#     config + 'do_install || echo "Install Failed"'
#     config_string = config.getstr()
#     print(config_string)

# import queue
# q = queue.Queue(maxsize=1)
# q.put(item='a', block=False, timeout=None)
# print(q.get())
# q.put(item='b', block=False, timeout=None)
# print(q.get(block=False))


# class MylistMetaclass(type):
#     def __new__(cls, name, bases, attrs):
#         attrs['add'] = lambda self, value: self.append(value)
#         return type.__new__(cls, name, bases, attrs)

# class Mylist(list, metaclass=MylistMetaclass):
#     pass

# L = Mylist()
# L.add('1')
# L.add('2')
# print(L.__class__)

# class ObjectCreator(object):
#     pass

# my_object = ObjectCreator()
# print(my_object.__class__.__name__.title())
# print(ObjectCreator)
# print(ObjectCreator.__name__.title())

# def echo(self):
#     print('Hello World!')

# a = type('Myclass', (), {"hello": echo})
# print(a.__name__.title())
# say = a()
# say.hello()

class UpperAttrMetaclass(type):
    def __new__(cls, name, bases, attr):
        attr_list = [(key, value) for key, value in attr.items() if not key.startswith('__')]
        for n, v in attr_list:
            attr.pop(n)
        new_attr = dict((key.upper(), value) for key, value in attr_list)

        new_attr.update(attr)
        return type.__new__(cls, name, bases, new_attr)

    def __init__(cls, name, bases, attr):
        cls.type = 'test'
        super().__init__(cls)



class Foo(object, metaclass=UpperAttrMetaclass):

    def __init__(self, a):
        self.n = a

    def echo(self):
        print('Hello World!')


a = Foo('a')
# print(dir(a))
print(a.n)
a.ECHO()
print(a.type)
print(dir(Foo))
import os
print(os.path.realpath(__file__))
