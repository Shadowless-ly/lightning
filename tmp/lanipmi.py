#!/usr/bin/python2

import subprocess
import exceptions

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
        self.mode_dict = {value.replace('0x', ''): key for (key, value) in self._mode_data.items()}
        self.oprom_dict = {value.replace('0x', ''): key for (key, value) in self._oprom_data.items()}
        self.bootdev_dict = {value.replace('0x', ''): key for (key, value) in self._bootdev_data.items()}
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
        if mode in self._mode_data.keys():
            set_boot_mode = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['bootmode'], self._mode_data[mode])
            recv = self._cmd(set_boot_mode)

    @property
    def bootdev(self):
        get_boodev = '%s %s %s' % (self._method, self._action_data['query'], self._option_data['bootdev'])
        recv = self._cmd(get_boodev)
        return recv

    @bootdev.setter
    def bootdev(self, device):
        if device in self._bootdev_data.keys():
            set_bootdev = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['bootdev'], self._bootdev_data[device])
            recv = self._cmd(set_bootdev)

    @property
    def oprom(self):
        get_oprom = '%s %s %s' % (self._method, self._action_data['query'], self._option_data['oprom'])
        recv = self._cmd(get_oprom)
        return recv

    @oprom.setter
    def oprom(self, oprom):
        if oprom in self._oprom_data.keys():
            set_oprom = '%s %s %s %s' % (self._method, self._action_data['set'], self._option_data['oprom'], self._oprom_data[oprom])
            recv = self._cmd(set_oprom)


def confirm_ipmitool():
    p = subprocess.Popen('type ipmitool', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    recv = p.communicate(input=None)
    if recv[1]:
        print(recv)
        raise EnvironmentError


def ipmi_cmd(method, bios_mode, oprom_mode, boot_device, host='localhost', username='admin', password='Password@_'):
    confirm_ipmitool()
    ipmi = IPMI()
    ipmi.lanplus_host=host
    ipmi.lanplus_name=username
    ipmi.lanplus_password=password
    ipmi.set_handle(method)
    ipmi.boot_mode = bios_mode
    ipmi.oprom = oprom_mode
    ipmi.bootdev = boot_device
    try:
        ipmi.reverse_dict()
        # print(ipmi.boot_mode[0].strip()[-2:], "------------->", ipmi.mode_dict)
        print 'BIOS:', ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]]
        print 'OPROM:', ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]]
        print 'BOOTDEV:', ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]]
        assert ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]] == bios_mode, 'Set Boot Mode Failed!'
        assert ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]] == oprom_mode, 'Set Option ROM mode Failed'
        assert ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]] == boot_device, 'Set Boot Device Failed'
    except exceptions.AssertionError as e:
        raise e

def set_uefi_pxe():
    ipmi_cmd('raw', 'uefi', 'uefi', 'NETWORK')

def set_legacy_pxe():
    ipmi_cmd('raw', 'legacy', 'legacy', 'NETWORK')

def set_uefi_disk():
    ipmi_cmd('raw', 'uefi', 'uefi', 'HDD')

def set_legacy_disk():
    ipmi_cmd('raw', 'legacy', 'legacy', 'HDD')

def menu():
    ipmi = IPMI()
    host = raw_input('Please Input your BMC IP address:')
    ipmi.lanplus_host = host
    username = raw_input('Please Input your BMC username:(default admin)')
    username = username or 'admin'
    ipmi.lanplus_name = username or 'admin'
    password = raw_input('Please Input your BMC password:(default Password@_)')
    password = password or 'Password@_'
    ipmi.lanplus_password = password
    ipmi.set_handle('lanplus')
    method = raw_input('Please select method query(q) or set(s):')
    if method in ['query', 'q']:
	ipmi.reverse_dict()
        print 'BIOS:', ipmi.mode_dict[ipmi.boot_mode[0].strip()[-2:]]
        print 'OPROM:', ipmi.oprom_dict[ipmi.oprom[0].strip()[-2:]]
        print 'BOOTDEV:', ipmi.bootdev_dict[ipmi.bootdev[0].strip()[-2:]]
    elif method in ['set', 's']:
            mode = raw_input('you can chose boot mode:\n1:uefi pxe\n2:legacy pxe\n3:uefi disk\n4:legacy disk\ninput your select:')
            if mode == '1':
                ipmi_cmd('lanplus', 'uefi', 'uefi', 'NETWORK', host=host, username=username, password=password)
            elif mode == '2':
                ipmi_cmd('lanplus', 'legacy', 'legacy', 'NETWORK', host=host, username=username, password=password)
            elif mode == '3':
                ipmi_cmd('lanplus', 'uefi', 'uefi', 'HDD', host=host, username=username, password=password)
            elif mode == '4':
                ipmi_cmd('lanplus', 'legacy', 'legacy', 'HDD', host=host, username=username, password=password)


if __name__ == '__main__':
    menu()
