#! /usr/bin/env python

# IPMITOOL URL
IPMITOOL_URL = 'http://192.168.1.1/tools/ipmitool-1.8.18.tar.bz2'
import subprocess
import sys
try:
    from exceptions import AssertionError
except:
    pass


class IPMISetError(Exception):
    pass

class IPMINotFoundError(Exception):
    pass

class IPMI(object):
    
    def __init__(self):
        self._action_data = {
            'query': '0x36 0x0b 0xa2 0x63 0x00 0x1a',
            'set': '0x36 0x0b 0xa2 0x63 0x00 0x19' }
        self._option_data = {
            'bootmode': '0x0e',
            'bootdev': '0x14',
            'oprom': '0x0b' }
        self._mode_data = {
            'uefi': '0x01',
            'legacy': '0x00' }
        self._bootdev_data = {
            'HDD': '0x00',
            'ODD': '0x01',
            'USBHDD': '0x02',
            'USBODD': '0x03',
            'USBKEY': '0x04',
            'USBFDD': '0x05',
            'USBLAN': '0x06',
            'NETWORK': '0x07',
            'UEFI_APPLICATION': '0x08',
            'DISABLE': '0x09' }
        self._oprom_data = {
            'auto': '0x00',
            'uefi': '0x01',
            'legacy': '0x02' }
        self._method = 'ipmitool raw'
        self.lanplus_host = 'localhost'
        self.lanplus_name = 'admin'
        self.lanplus_password = 'Password@_'

    
    def reverse_dict(self):
        self.mode_dict = {value.replace('0x', ''): key for (key, value) in list(self._mode_data.items())}
        self.oprom_dict = {value.replace('0x', ''): key for (key, value) in list(self._oprom_data.items())}
        self.bootdev_dict = {value.replace('0x', ''): key for (key, value) in list(self._bootdev_data.items())}
        # self._mode = dict(zip(self._mode_data.values(), self._mode_data.keys()))
        # self._bootdev = dict(zip(self._bootdev_data.values(), self._bootdev_data.keys()))
        # self._oprom = dict(zip(self._oprom_data.values(), self._oprom_data.keys()))


    def set_handle(self, method):
        if method == 'raw':
            self._method = 'ipmitool raw'
        elif method == 'lanplus':
            self._method = 'ipmitool -H %s -I lanplus -U %s -P %s raw' % (self.lanplus_host, self.lanplus_name, self.lanplus_password)

    
    def _cmd(self, cmd):
        p = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
        recv = p.communicate(None)
        return recv

    @property
    def boot_mode(self):
        get_boot_mod = '%s %s %s' % (self._method, self._action_data['query'], self._option_data['bootmode'])
        recv = self._cmd(get_boot_mod)
        return recv


    @boot_mode.setter
    def boot_mode(self, mode):
        if mode in list(self._mode_data.keys()):
            set_boot_mode = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['bootmode'], self._mode_data[mode])
            recv = self._cmd(set_boot_mode)

    @property
    def bootdev(self):
        get_boodev = '%s %s %s' % (self._method, self._action_data['query'], self._option_data['bootdev'])
        recv = self._cmd(get_boodev)
        return recv

    @bootdev.setter
    def bootdev(self, device):
        if device in list(self._bootdev_data.keys()):
            set_bootdev = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['bootdev'], self._bootdev_data[device])
            recv = self._cmd(set_bootdev)

    @property
    def oprom(self):
        get_oprom = '%s %s %s' % (self._method, self._action_data['query'], self._option_data['oprom'])
        recv = self._cmd(get_oprom)
        return recv

    @oprom.setter
    def oprom(self, oprom):
        if oprom in list(self._oprom_data.keys()):
            set_oprom = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['oprom'], self._oprom_data[oprom])
            recv = self._cmd(set_oprom)

def install_ipmitool(url):
    p = subprocess.Popen('wget -N %s -O ipmitool.tar.bz2 -q ; tar -jxvf ipmitool.tar.bz2 ; cd ipmitool-1.8.18/; /bin/sh configure ;make && make install' %IPMITOOL_URL,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) 
    recv = p.communicate(input=None)
    return recv

def confirm_ipmitool():
    install = 0
    p = subprocess.Popen('type ipmitool', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    recv = p.communicate(input=None)
    if not recv[1]:
        pass
    elif recv[1] and install:
        raise EnvironmentError(recv[1])
    else:
        install = 1
        result = install_ipmitool(IPMITOOL_URL)
        print(result[0] + result[1])

def ipmi_cmd(method, bios_mode=None, oprom_mode=None, boot_device=None, host='localhost', username='admin', password='Password@_'):
    confirm_ipmitool()
    ipmi = IPMI()
    ipmi.lanplus_host=host
    ipmi.lanplus_name=username
    ipmi.lanplus_password=password
    ipmi.set_handle(method)
    if bios_mode:
        ipmi.boot_mode = bios_mode
    if oprom_mode:
        ipmi.oprom = oprom_mode
    if boot_device:
        ipmi.bootdev = boot_device
    try:
        ipmi.reverse_dict()
        # print(ipmi.boot_mode[0].strip()[-2:], "------------->", ipmi.mode_dict)
        print('BIOS:', ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]])
        print('OPROM:', ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]])
        print('BOOTDEV:', ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]])
        # assert ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]] == bios_mode, 'Set Boot Mode Failed!'
        # assert ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]] == oprom_mode, 'Set Option ROM mode Failed'
        # assert ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]] == boot_device, 'Set Boot Device Failed'
    except AssertionError as e:
        raise e()

def set_uefi_pxe():
    ipmi_cmd('raw', bios_mode='uefi', oprom_mode='uefi', boot_device='NETWORK')

def set_legacy_pxe():
    ipmi_cmd('raw', bios_mode='legacy', oprom_mode='legacy', boot_device='NETWORK')

def set_uefi_disk():
    ipmi_cmd('raw', bios_mode='uefi', oprom_mode='uefi', boot_device='HDD')

def set_legacy_disk():
    ipmi_cmd('raw', bios_mode='legacy', oprom_mode='legacy', boot_device='HDD')

def set_pxe():
    ipmi_cmd('raw', boot_device='NETWORK')

def set_disk():
    ipmi_cmd('raw', boot_device='HDD')

def menu():
    ipmi = IPMI()
    host = input('Please Input your BMC IP address:')
    ipmi.lanplus_host = host
    username = input('Please Input your BMC username:(default admin)')
    username = username or 'admin'
    ipmi.lanplus_name = username or 'admin'
    password = input('Please Input your BMC password:(default Password@_)')
    password = password or 'Password@_'
    ipmi.lanplus_password = password
    ipmi.set_handle('lanplus')
    method = input('Please select method query(q) or set(s):')
    if method in ['query', 'q']:
        ipmi.reverse_dict()
        print('BIOS:', ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]])
        print('OPROM:', ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]])
        print('BOOTDEV:', ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]])
    elif method in ['set', 's']:
            mode = input('you can chose boot mode:\n1:uefi pxe\n2:legacy pxe\n3:uefi disk\n4:legacy disk\ninput your select:')
            if mode == '1':
                ipmi_cmd('lanplus', 'uefi', 'uefi', 'NETWORK', host=host, username=username, password=password)
            elif mode == '2':
                ipmi_cmd('lanplus', 'legacy', 'legacy', 'NETWORK', host=host, username=username, password=password)
            elif mode == '3':
                ipmi_cmd('lanplus', 'uefi', 'uefi', 'HDD', host=host, username=username, password=password)
            elif mode == '4':
                ipmi_cmd('lanplus', 'legacy', 'legacy', 'HDD', host=host, username=username, password=password)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('please input arguments ["uefi_pxe", "legacy_pxe", "uefi_disk", "legacy_disk", "pxe", "disk"]')
    elif sys.argv[1] == 'uefi_pxe':
        set_uefi_pxe()
    elif sys.argv[1] == 'legacy_pxe':
        set_legacy_pxe()
    elif sys.argv[1] == 'uefi_disk':
        set_uefi_disk()
    elif sys.argv[1] == 'legacy_disk':
        set_legacy_disk()
    elif sys.argv[1] == 'pxe':
        set_pxe()
    elif sys.argv[1] == 'disk':
        set_disk()
