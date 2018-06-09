#!/usr/bin/python2
# -*-coding=utf-8-*-

import subprocess
import sys
import time

# ipmitool源码包位置
IPMITOOL_URL = 'http://192.168.1.1/tools/ipmitool-1.8.18.tar.bz2'

class IPMI_SETTER(object):

    def __init__(self):
        self.method = "local"
        self.basic_ipmicommand = 'ipmitool raw'
        self._action_dict = {}
        self._option_dict = {}
        self._mode_dict = {}
        self._bootdev_dict = {}
        self._oprom_dict = {}
        self.dict_map = {
            'bootmode': self._mode_dict,
            'bootdev': self._bootdev_dict,
            'oprom': self._oprom_dict
        }
        self.reverse_dict()

    def _run_cmd(self, cmd):
        """执行shell命令
        """
        time.sleep(0.1)
        # print(cmd)
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        recv = p.communicate(input=None)
        return recv

    def install_ipmitool(self, url):
        """解压，编译，安装ipmitool源码包
        """
        recv = self._run_cmd('wget -N %s -O ipmitool.tar.bz2 -q ; tar -jxvf ipmitool.tar.bz2 ; cd ipmitool-1.8.18/; sh configure || /usr/bin/sh configure; make && make install' %url)
        return recv

    def reverse_dict(self):
        """翻转字典键值用于结果查询
        """
        self._re_action_dict = {self._action_dict[key].replace('0x', ''): key for key in self._action_dict.keys()}
        self._re_option_dict = {self._option_dict[key].replace('0x', ''): key for key in self._option_dict.keys()}
        self._re_mode_dict = {self._mode_dict[key].replace('0x', ''): key for key in self._mode_dict.keys()}
        self._re_bootdev_dict = {self._bootdev_dict[key].replace('0x', ''): key for key in self._bootdev_dict.keys()}
        self._re_oprom_dict = {self._oprom_dict[key].replace('0x', ''): key for key in self._oprom_dict.keys()}

    def confirm_ipmitool(self, install=0):
        """确认ipmitool存在，如不存在则执行一次安装
        """
        recv = self._run_cmd('type ipmitool')
        if not recv[1]:
            pass
        elif recv[1] and install:
            raise EnvironmentError(recv[1])
        else:
            result = self.install_ipmitool(IPMITOOL_URL)
            print(result[0] + result[1])
            self.confirm_ipmitool(install=1)

    def modprobe(self):
        """加载驱动
        """
        recv = self._run_cmd('modprobe ipmi_msghandler; modprobe ipmi_devintf; modprobe ipmi_si; modprobe ipmi_poweroff; modprobe ipmi_watchdog')
        return recv

    def set_handle(self, method, host, username="admin", password="Password@_"):
        """设置发送本地命令或lanplus
        """
        self.method = "lanplus"
        self.basic_ipmicommand = "ipmitool -H {host} -I {method} -U {username} -P {password} raw".format(
            host=host,
            method=self.method,
            username=username,
            password=password
            )

    def query_machine_type(self):
        """识别机型
        """
        return 'V5R1'

    def set_command(self, option, mode):
        """执行设置命令
        """
        set_mode = '{basic_ipmicommand} {target_action} {target_option} {target_mode}'.format(
            basic_ipmicommand = self.basic_ipmicommand,
            target_action = self._action_dict.get('set', ''),
            target_option = self._option_dict.get(option, ''),
            target_mode = self.dict_map.get(option).get(mode, '')
                )
        return self._run_cmd(set_mode)
    
    def query_command(self, option):
        """执行查询命令
        """
        get_mode = '{basic_ipmicommand} {target_action} {target_option}'.format(
            basic_ipmicommand=self.basic_ipmicommand,
            target_action=self._action_dict.get('query', ''),
            target_option=self._option_dict.get(option, '')
            )
        print('query_command:', get_mode)
        return self._run_cmd(get_mode)

    @property
    def mode(self):
        return self.query_command('bootmode')

    @mode.setter
    def mode(self, mode_type):
        return self.set_command('bootmode', mode_type)

    @property
    def device(self):
        return self.query_command('bootdev')

    @device.setter
    def device(self, device_type):
        return self.set_command('bootdev', device_type)

    @property
    def option_rom(self):
        return self.query_command('oprom')

    @option_rom.setter
    def option_rom(self, option_rom_type):
        return self.set_command('oprom', option_rom_type)

    def send_ipmi_command(self, bios_mode=None, option_rom_mode=None, boot_device=None):
        print(bios_mode, option_rom_mode, boot_device)
        if bios_mode:
            self.mode = bios_mode
        if option_rom_mode:
            self.option_rom = option_rom_mode
        if boot_device:
            self.device = boot_device
        # try:
        #     print('BIOS:', self._re_mode_dict[self.mode[0].strip()[-2:]])
        #     print('OPION_ROM:', self._re_oprom_dict[self.option_rom[0].strip()[-2:]])
        #     print('BOOTDEV:', self._re_bootdev_dict[self.device[0].strip()[-2:]])
        # except Exception as e:
        #     print('IPMI Query Error!')
        #     raise e
        self.mode
        self.option_rom
        self.device


class IPMI_V5R1_SETTER(IPMI_SETTER):
    def __init__(self):
        super(IPMI_V5R1_SETTER, self).__init__()
        self._action_dict = {
            'query': '0x36 0x0b 0xa2 0x63 0x00 0x1a',
            'set': '0x36 0x0b 0xa2 0x63 0x00 0x19' 
            }
        self._option_dict = {
            'bootmode': '0x0e',
            'bootdev': '0x14',
            'oprom': '0x0b' 
            }
        self._mode_dict = {
            'uefi': '0x01',
            'legacy': '0x00' 
            }
        self._bootdev_dict = {
            'HDD': '0x00',
            'ODD': '0x01',
            'USBHDD': '0x02',
            'USBODD': '0x03',
            'USBKEY': '0x04',
            'USBFDD': '0x05',
            'USBLAN': '0x06',
            'NETWORK': '0x07',
            'UEFI_APPLICATION': '0x08',
            'DISABLE': '0x09' 
            }
        self._oprom_dict = {
            'auto': '0x00',
            'uefi': '0x01',
            'legacy': '0x02' 
            }
        self.dict_map = {
            'bootmode': self._mode_dict,
            'bootdev': self._bootdev_dict,
            'oprom': self._oprom_dict
        }
        self.reverse_dict()


class IPMI_V2R2_SETTER(IPMI_SETTER):
    pass

class IPMI_V5R2_SETTER(IPMI_SETTER):
    pass


def ipmi_select():
    ipmitool = IPMI_SETTER()
    ipmitool.confirm_ipmitool()
    ipmitool.modprobe()
    machine_type = ipmitool.query_machine_type()
    if machine_type == 'V5R1':
        return IPMI_V5R1_SETTER()
    elif machine_type == 'V2R2':
        return IPMI_V2R2_SETTER()
    elif machine_type == 'V5R2':
        return IPMI_V5R2_SETTER()
    else:
        return None

def set_uefi_pxe(ipmitool):
    ipmitool.send_ipmi_command(bios_mode='uefi', option_rom_mode='uefi', boot_device='NETWORK')

def set_legacy_pxe(ipmitool):
    ipmitool.send_ipmi_command(bios_mode='legacy', option_rom_mode='legacy', boot_device='NETWORK')

def set_uefi_disk(ipmitool):
    ipmitool.send_ipmi_command(bios_mode='uefi', option_rom_mode='uefi', boot_device='HDD')

def set_legacy_disk(ipmitool):
    ipmitool.send_ipmi_command(bios_mode='legacy', option_rom_mode='legacy', boot_device='HDD')

def set_pxe(ipmitool):
    ipmitool.send_ipmi_command(boot_device='NETWORK')

def set_disk(ipmitool):
    ipmitool.send_ipmi_command(boot_device='HDD')

def main():
    args_dict = {
        "uefi_pxe": set_uefi_pxe,
        "legacy_pxe": set_legacy_pxe,
        "uefi_disk": set_uefi_disk,
        "legacy_disk": set_legacy_disk,
        "pxe": set_pxe,
        "disk": set_disk
    }
    if len(sys.argv) < 2 or sys.argv[1] not in args_dict.keys():
        print('please input arguments ["uefi_pxe", "legacy_pxe", "uefi_disk", "legacy_disk", "pxe", "disk"]')
    else:
        ipmitool = ipmi_select()
        if not ipmitool:
            print('Unknow machine type!')
            raise EnvironmentError("Unknow machine type!")
        args_dict[sys.argv[1]](ipmitool)	


if __name__ == '__main__':
	main()
