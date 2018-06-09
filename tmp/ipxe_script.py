from ipxelib import IpxeString
class Script(object):

    def __init__(self):
        pass

    def ipxe_script(self, os_name, kernel_name, initrd_name, vmlinuz_args):
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

    def grub_script(self, os_name):
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

if __name__ == '__main__':
    print(grub_script('rhel7.3'))