[TOC]





# Lightning iPXE服务



## 1. 结构概述

---
Lightning系统安装控制底层使用iPXE,通过动态生成iPXE脚本,控制系统安装任务。
OS使用KS、AutoYast脚本控制系统自动安装。
系统中自动化任务由tasktracker脚本实现。

### 1.1 服务类

#### 1.1.1 DHCP

DHCP作为iPXE的基本服务，用于在PXE网卡启动时分配`IP地址`，`dns`，`nextserver`，`filename`等必须参数，以及`网关地址`,`NTP server`等可选参数。
其中`nextserver`指定为`pxe client`可以访问到的`tftp server`。`tftp server`需要在根目录放置`filename`文件以用于引导启动。
DHCP需要有判断客户端类型的能力，用于配置与客户端配套的`filename`。
> 可选用`dnsmasq`与`dhcpd`，`dnsmasq`修改`/etc/dnsmasq.conf`文件，`httpd` 修改`Apache2`的`httpd.conf`与`httpd-vhost.conf`配置文件。服务名为`dnsmasq`与`dhcpd`

#### 1.1.2 TFTP

TFTP为IPXE基本服务，用于在`pxe client`启动时**传送**可以加载启动的引导程序。以及在引导程序启动后，**Legacy模式**需要从`TFTP`服务器加载**内核**与**根文件系统**文件。
> * 一般TFTP服务托管于`xinetd`超级守护进程。
> * 为了简化设计,UEFI模式同样采取从`TFTP`服务器获取内核与根文件系统相关文件。
> * 配置文件为`/etc/xinetd/tftp`

#### 1.1.3 DNS

为了便于编写配置，使用DNS服务进行域名解析，服务器使用`os.com`以替代IP地址`172.16.1.10`。
由于Lightning中ipxe，KS/AutoYast，tasktracker，pyipmi脚本中使用了`os.com`的url，所以DNS服务为必须。
> * 服务名为`named`
> * 配置文件为`/etc/named.conf`等

#### 1.1.4 NFS

NFS服务为兼容原SIT小网环境，需要支持Live OS启动而开启。
> * 服务名为`portmap`与`nfs`
> * 配置文件为`/etc/exports`

#### 1.1.5 SAMBA

SAMBA服务为Window PXE启动所需服务，供Win PE启动后挂载远程目录，运行系统安装文件。
> 服务名为`smb`，配置文件为`/etc/samba/smb.conf`

#### 1.1.6 HTTP

HTTP服务用于IPXE启动控制与安装过程中文件传输。
主要有两个功能，分别使用`/`根目录与`/auto`。
根目录为系统镜像解压后的仓库，用于Linux内核与根文件系统加载完成后执行系统安装。
`/auto`用于接收IPXE Client的`request`，为其提供控制脚本。在系统安装后支持`tasktracker`用于任务调度。
> * 配置文件为`Apache2`的`httpd.config`与`httpd-vhosts.conf`(若未使用docker环境)
> * `Lightning web`服务端文件位于`/var/www/auto`目录

#### 1.1.7 MySQL

MySQL服务为lightning服务提供数据存储。存放OS列表，任务列表，MAC地址列表以及供查询的视图。

### 1.2 文件类

文件类配置项为各种OS的自动化安装脚本，IPXE控制脚本，OS下任务调度的tasktracker脚本，切换启动顺序的pyipmi脚本，以及shell 环境配置脚本。

#### 1.2.1 IPXE脚本

IPXE启动可以使用IPXE Script来控制，在整个系统中，除了由http服务提供的/auto动态脚本之外，还有用于配置网口，启动菜单的静态脚本。静态脚本按照IPXE Script格式编写，后缀名统一命名为`.ipxe`。
> 文件位置`/home/ipxe/http/ipxe.d`
> 脚本编写参考[ipxe.org](http://ipxe.org/docs)

#### 1.2.2 KS/AutoYast脚本

KS脚本作为系统自动安装使用，默认会进行全包安装。
> 脚本位置`/home/ipxe/http/image`目录下各个操作系统文件夹中的ks或autoyast相关文件
> 编写参考官方文档

#### 1.2.3 tasktracker脚本

tasktracker脚本为系统下任务控制脚本，负责收集本机MAC地址，提交到服务器，获取当前任务，执行任务。
该脚本由KS脚本调用，在KS脚本POST阶段chroot执行tasktrackr install将该脚本添加到系统开机启动(rc.local)，执行ENV脚本部署必要的环境，执行pyipmi脚本切换启动项。在系统安装完成重启后开机自动作为守护进程运行。

#### 1.2.4 ENV脚本

ENV脚本用于执行系统下环境配置以及其他功能。
在OS install过程中，tasktracker脚本的install方法会调用env脚本来部署python3环境（下载miniconda并安装，添加环境变量）以及ipmitool（下载pyipmi，执行）。
同时在tasktracker从服务器获得OS install任务时执行。（未开始的安装任务以及正在进行的安装任务）

#### 1.2.5 pyipmi脚本

pyipmi脚本用于在OS下切换启动项顺序，该脚本依赖ipmitool来执行ipmi命令。
支持四种模式切换: 

* `（BIOS：UEFI， BOOTDEV：NETWORK，CSM NETWROK：UEFI）`
* `（BIOS：UEFI， BOOTDEV：HDD，CSM NETWROK：UEFI）`
* `（BIOS：Legacy， BOOTDEV：NETWORK，CSM NETWROK：Legacy）`
* `（BIOS：Legacy， BOOTDEV：HDD，CSM NETWROK：Legacy）`

> * 需要操作系统安装ipmitool，并支持ipmi命令管理，在该脚本中提供环境检查以及install_ipmitool方法在缺失ipmitool的环境下尝试1次安装。ipmitool的tar包从http服务器下载目录为`http://os.com/tools/ipmitool-1.8.18.tar.bz2`。
> * 文件位置`/home/ipxe/http/tools/ipmitool-1.8.18.tar.bz2`

## 2. 详细配置

---

### 2.1 服务类

#### 2.1.1 DHCP服务配置

在`/etc/dhcp/dhcp.conf`文件中增加以下内容
用以识别客户端发来的`dhcp Request`中`Option identifier`字段，当该字段为`00:07`标识`X86_64`客户端，标识为`00:09`标识Vmware的虚拟机UEFI客户端，其他默认为X86 BIOS Legacy。
指定Next Server为TFTP服务器`172.16.1.10`。

```bash
match if substring (option vendor-class-identifier,0,9) = "PXEClient";
next-server 172.16.1.10;
if option arch = 00:07
    {
    filename "Pikachu_ipxe.efi";
    }
else if option arch = 00:09
   {
   filename "Pikachu_ipxe.efi";
   }
else
   {
   filename "pxelinux.0";
   }
}

```

#### 2.1.2 DNS服务配置

`/etc/named.rfc1912.zones`中增加以下内容
```sh
zone "os.com" IN{
        type master;
        file "named.os.com";
};
```
DNS服务器配置文件增加`/var/named/named.os.com`，内容如下
```dns
$TTL 1D
@	IN SOA	@ os.com. (
					0	; serial
					1D	; refresh
					1H	; retry
					1W	; expire
					3H )	; minimum
	NS	@
	A	172.16.1.10
	AAAA	fe80::eda:41ff:fe1d:cad1
```

#### 2.1.3 MySQL服务配置

数据库服务使用xampp提供的mysql服务，默认用户root密码为空

#### 2.1.4 HTTP服务配置

HTTP服务使用docker的lightning容器，需要安装docker服务。
安装完成后导入lightning镜像
`docker load < http-lightning.tar`
docker安装文件与镜像位置`/home/ipxe/pxetools/lightning`
该镜像提供了python flask运行环境。挂载volume到指定目录即可使用。
运行命令如下
`docker run -d -p 80:80 -v /home/ipxe/http:/pxe/repertory -v /home/ISO/:/home/ISO/ -v /var/www/auto:/var/www/auto --name lightning-httpd lightning`\
> * 该镜像中http文件服务的目标位置为`/pxe/repertory`
> * Flask web文件位置为`/var/www/auto`
> * 需要将HOST上的目标目录以volume挂载进容器
> * 挂载`/home/ISO`目录是因为在`/home/ipxe/http/`目录中有ISO目录的绝对路径`symbol link`，该目录的存在是为了兼容原PXE，将原PXE路径添加修改为`http://os.com/ISO`，避免对原目录结构过大改动。

### 2.2 文件类配置

#### 2.2.1 TFTP目录配置

* 172.16.1.10 tftp目录结构，tftp在保持原PXE Server目录结构基本不变的情况下进行了文件添加。
* 增加了Image目录,在Image目录下为Lightning iPXE启动所需各个操作系统的内核与根文件系统。
* 在tftp根目录使用**Pikachu_ipxe.efi**作为**UEFI**启动文件，使用**pxelinux.0**作为**legacy**启动文件。
* 修改了**PXElinux.0**位于**pxelinux.cfg**下的菜单，增加了引导IPXE启动文件**Pikachu_ipxe.lkrn**的条目。

目录结构见附录5

#### 2.2.2 HTTP镜像目录配置

* **http文件目录**

用于存放需要通过http传输的文件：测试工具，grub，系统安装文件

> 目录位置`/home/ipxe/http`

```shell
/home/ipxe/http/
├── grub
├── grubfm
├── image
├── ipxe.d
├── ISO -> /home/ISO
├── tools
└── wimboot
```

* **grub**：存放grub镜像，该镜像用于解决CentOS/RHEL 7.2， 6.X版本内核不支持EFI启动问题，采用将kernel，initrd与grub和grub菜单封装成grub镜像的方式启动。该目录下提供了mkefi.py脚本用于制作grub镜像。使用方法见附录。
* **grubfm**：存放grub file manager，一个可启动的管理工具。
* **image**：存放解压后的系统镜像，KS脚本，以及阵列卡驱动安装脚本。一般情况下ks脚本放置在对应的系统镜像解压目录
* **ISO**：软连接到/home/ISO目录，为兼容原PXE系统。
* **tools**：客户端运行时需要的工具和脚本。
* **wimboot**：存放grub的菜单文件，用于制作grub镜像。
* **ipxe.d**： 为IPXE Script，用来控制IPXE的启动流程，在ipxe.d目录下单独介绍。


#### 2.2.3 HTTP Lightning Web App 目录配置

HTTP Lightning为存放Python web文件的目录
文件位置为`/var/www/auto`

```shell
auto
├── flask.wsgi
├── ipxelib
│   ├── __init__.py
│   ├── ipxetool.py
│   ├── pikachu.py
│   └── taskhandle.py
├── ipxe.py
├── pikachu
│   └── PikachuClient.py
├── templates
└── tmp
```

`flask.wsgi`为Flask启动文件，该文件直接配合lightning的docker镜像使用即可

```python
import sys
sys.path.insert(0, "/var/www/auto")    # 添加当前目录到环境变量
from ipxe import app as application    # 启动flask application
```

`ipxe.py`为lightning web app文件为响应HTTP请求。
其路由信息如下：

```python
@app.route('/')
"""根目录提供欢迎信息
"""

@app.route('/uefi')
"""uefi启动IPXE

在UEFI模式IPXE的efimenu.ipxe菜单加载后，自动选择或手动进入IPXE AUTO选项。
该动作会向Server端发送http request，其url为http://os.com/auto/uefi?mac=${mac} 
该函数处理此请求获取到get请求参数mac，使用该mac查询数据库os_install_mission表获取pxe安装系统所需参数，并调用ipxelib.ipxetool.Srcipt生成ipxe启动脚本。
"""

@app.route('/legacy', methods=['GET'])
"""legacy启动ipxe

在Legacy模式Pxelinux.0的default菜单加载后，自动选择或手动进入IPXE AUTO选项。
该动作会引导Pikachu.lkrn启动，默认从http://os.com/ipxe.d/preboot.ipxe （/home/ipxe/http/ipxe.d/preboot.ipxe）获得启动脚本
该脚本会向Server端发送http request，其url为chain http://os.com/auto/legacy?mac=${mac}
该函数处理此请求获取到get请求参数mac，使用该mac查询数据库os_install_mission表获取pxe安装系统所需参数，并调用ipxelib.ipxetool.Srcipt生成ipxe启动脚本。
"""

@app.route('/report', methods=['GET', 'POST', 'PUT'])
"""暂未实现，测试报告上传
"""

@app.route('/os_install_report', methods=['POST'])
"""处理TaskTracker POST Request, 同步当前OS Install状态

该函数接收来自tasktracker的post请求
获取tasktracker构造的Json交于.ipxelib.taskhandle.task解析并执行
根据执行结果返回状态码，OS Install状态定义见附录2
"""

@app.route('/config/PikachuClient.exe', methods=['GET', 'POST'])
"""PikachuClient 客户端命令行管理工具下载链接
"""

@app.route('/config/conda/', methods=['GET', 'POST'])
"""获取Conda环境配置脚本

调用ipxetool.Script.read_from_file方法读取/home/ipxe/http/tools/env.sh
"""

@app.route('/config/os_install/', methods=['GET', 'POST'])
"""New OS Install 配置脚本，在执行一个新的系统安装时，tasckertracker会请求该地址以获得配置脚本

调用ipxetool.Script.read_from_file方法读取/home/ipxe/http/tools/os_install_begin.sh
"""

@app.route('/task', methods=['GET', 'POST'])
"""TaskTracker请求处理

tasktracker周期性的向该url发送POST请求附带json数据，json格式为
{
    "type": "GetTask",
    "data": {
        "mac_list": slef.maclist
    }
}
该函数调用taskhandle.task处理该请求
"""

@app.route('/user', methods=['GET', 'POST'])
"""pikachu管理器帮助文档
"""

@app.route('/user/record', methods=['GET', 'POST'])
"""pikachu Record查询接口

为Pikahcu命令行管理工具提供的接口，接收get请求交于ipxelib.pikachu处理用于查询
接收post请求交于ipxelib.pikachu处理用于添加，修改数据。
"""

@app.route('/user/table', methods=['GET', 'POST'])
"""处理其他table查询请求

为Pikachu命令行管理工具提供的接口，用于其他table的查询操作
"""
```

**ipxelib** 
* `ipxetool.py` 是一个ipxe脚本生成工具包含有Rcord类，IpxeString类以及Script类。
    * `Rcord类` 用于将数据库查询结果映射为Rcord实例，查询结果的键值对转换为实例的属性。
    * `IpxeString类` 用于编写ipxe脚本，实例化IpxeString，使用`+`运算符或`append_substr`逐行添加ipxe脚本语句。使用`getstr`方法获得ipxe脚本字符串。
    * `Script类` 已编写好的脚本，包含`ipxe_script`，`grub_script`，`install_miniconda`，`read_from_file`, `boot_from_hd`, `task_explain`等类方法，可直接调用。
        > * `ipxe_script` uefi与legacy正常启动时为ipxe提供该脚本
        > * `grub_script` uefi模式使用兼容性方案grub image模式时提供该脚本
        > * `install_miniconda` 返回环境配置脚本，安装anaconda环境
        > * `read_from_file` 直接从文件读取内容，返回字符串
        > * `boot_from_hd` 引导从硬盘启动 （目前实体服务器存在BUG无法返回，虚拟机正常）

* `taskhandle.py` lightning的任务控制器，用于连接数据库，解析任务类型查询数据库返回对应的操作，处理CV，OS Install，GetTask, Stress任务。
    * class taskhandle.MyDB(mac_list: list, blacklist=None)表示数据库的连接，连接参数使用MyDB.config。MyDB实例具有以下方法：
        * MyDB.execute(s: str)：执行SQL语句，并commit。参数为要执行的SQL语句字符串。当为查询操作，以Dict类型返回查询结果。当执行修改操作，以Dict类型返回rowcount。
        * MyDB.get_query(mac: str):使用mac参数查询os_install_mission表，获取record信息用于系统安装。返回Dict类型的系统安装信息。
        * MyDB.close():关闭数据库连接。
    * class taskhandle.BasicHandler(mac_list, blacklist=None)表示任务控制器的模板，建立任务控制器需要list类型的mac_list参数。初始化过程将建立数据库连接，并使用mac_list比对数据库中的mac地址查找到目标mac地址与record id，并使用record id来管理任务。该过程为了保证在系统在多网口环境下能够识别出登记到lightning的目标mac。
        * BasicHandler.close():关闭数据库连接。
        * BasicHandler.prepare():测试环境准备。
        * BasicHandler.begin():测试任务开始。
        * BasicHandler.complete():测试任务完成。
    * class TaskHandler(data)表示一个Task任务控制器，用来处理Tasktracker的gettask请求，data参数为tasktracker构造的Dict，
        ```json
        '{
        "type"："GetTask",
        "data": {
            "mac_list": ["11:22:33:44:55:66:77"],
        }'
        ```
        * TaskHandler.start()返回使用mac_list查询current_task表所得任务信息。类型为str/json
            ```json
            task_dict = {
            'type': type,    # 当前无任务该值为None
            'data': {
                'id': id,
                'mac': mac,
                'set_id': set_id,
                'status': status
                }
            }
            ```
    * class OSInstallHandler(data)表示OS安装任务控制器，实现了OS安装开始，完成时设置对应record状态。获取新系统安装任务参数。
        * OSInstallHandler.begin():开始安装，使用reacod id修改record表中对应项的status为1
        * OSInstallHandler.complete():完成安装，使用record id修改record表中对应项的status值为2
        * OSInstallHandler.complete():通过解析tasktracker构造的json完成指定动作。接收data参数格式如下：
            ```json
            {
                'type': 'OS',
                'data': {
                    'mac_list': mac_list,
                    'status': status
                }
            }
            ```
            当status为0，以json类型返回下一个需要安装操作系统所需要的信息
            ```
            {
                'type': 'OS'
                'data': {
                    'id': id,
                    'os_id': os_id,
                    'os_name': os_name,
                    'status': record_status,
                    'mode': mode,
                }
            }
            ```
            * status为1时，执行OSInstallHandler.begin()
            * status为2时，执行OSInstallHandler.complete()

    * class CVHandler(data)表示CV测试控制器。
    * class StressHandler(data)表示Stress测试控制器。

    * task(mission_dict) 函数用以解析来自tasckertracker的原始数据，通过解析其type字段，选择任务控制器类型并使用data字段创建对应的任务控制器对象。

* `pikachu.py` 处理pikachu cli工具的请求。所有pikachu命令行管理工具的请求由该模块处理。


**pikachu** 
* `PikachuClient.py`
用于自动化测试任务管理的命令行工具，可以添加mac地址，添加，修改任务，查询当前任务等。该模块依赖prompt_toolkit 2.0环境，需要从官网下载prompt_toolkit 2.0，并使用pyinstaller将该命令行打包成exe可执行文件，放置在`/home/ipxe/http/tools`目录。

## 3. 服务维护

### 3.1 更新IPXE启动文件

更新IPXE启动文件可以使用本地源码编译与在线编译两种方式
编译时需要制定启动脚本 `netconfig.ipxe`，可以参照下方代码：

```bash
#!ipxe
set i:int32 0
:setnet
ifstat net${i} || goto end
echo Initializing Net${i}
dhcp net${i} && chain http:/os.com/ipxe.d/preboot.ipxe || ifclose net${i}
inc i && goto setnet

:end
echo InitializeFailed
shell
```

该脚本实现了按顺序初始化网口，当网口0存在则开始dhcp，dhcp成功后尝试`chain http://os.com/ipxe.d/preboot.ipxe`如果失败则关闭该网口，继续下一个网口。若没有可以成功启动的网口则进入shell。

在指定链式引导文件的位置时需要区分UEFI和Legacy，如uefi使用`http://os.com/ipxe.d/efipreboot.ipxe`
legacy使用`http://os.com/ipxe.d/preboot.ipxe`
> 当前采用此方案区分启动模式

#### 3.1.1 本地源码编译

下载源码包，源码包地址 `http://git.ipxe.org/ipxe.git`安装所需环境，执行编译`cd ipxe/src ; make`。使用EMBED脚本编译出ipxe启动文件：

* Legacy `make bin/ipxe.lkrn EMBED=netconfig.ipxe`
* UEFI  `make bin-x86_64-efi/ipxe.efi EMBED=netconfig.ipxe`

```shell
依赖环境
gcc (version 3 or later)
binutils (version 2.18 or later)
make
perl
liblzma or xz header files
mtools
mkisofs (needed only for building .iso images)
syslinux (for isolinux, needed only for building .iso images)
```

#### 3.1.2 本地源码编译

在线编译地址`https://rom-o-matic.eu/`

### 3.2 Legacy菜单

Legacy使用pxelinux.0引导启动，在启动项中添加了ipxe启动项用于自动化测试，其他系统配置和原pxe保持一致。

```grub
label iPXE
menu label iPXE
menu default
kernel Pikachu_ipxe.lkrn
```

> 文件位置 /var/lib/tftpboot/pxelinux.cfg/default

### 3.3 UEFI菜单

UEFI模式将使用IPXE标准菜单,可参照[附录5.4](#54-ipxe-uefi)。

> 文件位置 /home/ipxe/http/ipxe.d/efimenu.ipxe

### 3.4 新增CV测试功能

* 数据库配置：CV测试功能可以使用mysql数据库中的cv_mission table，将cv测试所需脚本放于指定位置，位置信息记录于script_path列。
* ipxe.py: CV测试功能使用接口为http://os.com/auto/task。 该路由会调用taskhandle中的task函数解析POST请求，识别该请求类别为CV，并使用CVHandler对象处理。
* taskhandle.py: CV测试的接口为CVHandler(mac_list), 处理模式与OSInstallHandler相同，用于和Client端tasktracker交互的Json数据格式为
  ```json
  {
    'type': 'CV',
    'data': {
        'mac_list': mac_list,
        'status': status
    }
  }
  ```
* tasktracker.py: 完成tasktracker中Lightningd._cv方法，当type为CV时，该方法会被调用处理接收到的Json数据。根据Json数据data字段做出不同动作，如下载脚本，执行测试等。

> CV测试脚本可存放在http服务指定目录，以便客户端直接wget或curl下载获得。
### 3.5 新增Stress测试功能
* 数据库配置：Stress测试功能可以使用mysql数据库中的stress_mission table，将Stress测试所需脚本放于指定位置，位置信息记录于script_path列。
* ipxe.py: Stress测试功能使用接口为http://os.com/auto/task。 该路由会调用taskhandle中的task函数解析POST请求，识别该请求类别为Stress，并使用StressHandler对象处理。
* taskhandle.py: Stress测试的接口为StressHandler(mac_list), 处理模式与OSInstallHandler相同，用于和Client端tasktracker交互的Json数据格式为
  ```json
  {
    'type': 'Stress',
    'data': {
        'mac_list': mac_list,
        'status': status
    }
  }
  ```
* tasktracker.py: 完成tasktracker中Lightningd._stress方法，当type为CV时，该方法会被调用处理接收到的Json数据。根据Json数据data字段做出不同动作，如下载脚本，执行测试等。

> Stress测试脚本可存放在http服务指定目录，以便客户端直接wget或curl下载获得。

> Stress测试存在非阻塞情况，需要定义任务执行状态。一般情况下，任务执行为阻塞式的，在OS Install任务中，Tasktracker会定时请求服务器以获得当前任务，得到任务后，创建子线程解析并执行任务，主线程等待子线程返回后继续任务请求循环。而CV测试中，如Reboot脚本存在非阻塞情况，当Reboot执行后会立即重启，且开机后会自动运行，tasktracker必须有和服务端约定的正在执行任务状态，以便Reboot重启开机后可以正确处理当前任务动作。并且需要监控reboot状态，在reboot退出时向服务端同步状态。可以定制reboot脚本或在tasktracker实现。

## 4. 使用实例

### 4.1 新增普通PXE系统

#### 4.1.1 增加Legacy系统
由于legacy模式采用了兼容传统pxelinux.0的架构，故获取目标系统的内核与初始磁盘映像并直接修改pxelinux.cfg/default即可。
例如：

```pxe
label CentOS 7.3 Auto Install
menu label  Install CentOS 7.3 x64(Auto Install)
kernel Image/centos7.3/vmlinuz
append initrd=Image/centos7.3/initrd.img method=http://192.168.1.1/image/centos7.3/ ks=http://192.168.1.1/image/centos7.3/ks.cfg ip=dhcp 
```

```pxe
label Ubuntu 16.04
menu label  Install Ubuntu 16.04 x64(Legacy)
kernel Image/ubuntu16.04/linux vga=788
append initrd=Image/ubuntu16.04/initrd.gz ks=http://192.168.1.1/image/ubuntu16.04/url.cfg preseed/url=http://192.168.1.1/image/ubuntu16.04/preseed.cfg  --quiet
```

```pxe
label SLES12 SP3
menu label  Install SLES12 SP3 x64(Legacy)
kernel Image/sles12sp3/linux
append initrd=Image/sles12sp3/initrd install=http://192.168.1.1/image/sles12sp3/  ip=dhcp
```

> 菜单位置/var/lib/tftpboot/pxelinux.cfg/default

#### 4.1.2 新增UEFI系统

UEFI模式使用IPXE直接启动，故增加系统需要使用IPXE语法规则，且UEFI模式需要特殊处理兼容性问题。
在菜单开始部分定义各项服务变量名

```ipxe
set menu-timeout 10000
set menu-default ipxe
set image  tftp://os.com/Image
set method http://os.com/image
set tftp tftp://os.com
set http http://os.com
isset ${ip} || dhcp
set retry:int32 0
```

编写显示菜单函数：start

```ipxe
  menu iPXE Boot Menu
  item --gap -- ----------------------------------------REBOOT--------------------------------------------
  item reboot   Reboot
  item --gap -- ----------------------------------------OS INSTALL-----------------------------------------
  item --gap -- ------------------------------------------CentOS-------------------------------------------
  item centos7.4	Install CentOS 7.4
  item centos7.3	Install CentOS 7.3
```
选择菜单，跳转至已选择函数

```ipxe
choose --timeout ${menu-timeout} --default ${menu-default} selected
imgfree
goto ${selected}
```
目标系统函数，经由菜单选择后跳转至该函数，执行文件加载与启动

```
:centos7.4
  set nowboot centos7.4
  echo Starting CentOS 7.4 Installer
  initrd --timeout 30000 ${image}/centos7.4/initrd.img || goto retry
  kernel --timeout 30000 ${image}/centos7.4/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/centos7.4 ip=dhcp
  boot || goto fail

:centos7.3
  set nowboot centos7.3
  echo Starting centos7.3
  kernel --timeout 30000 ${http}/grub/centos7.3/centos7.3.efi || goto retry
  boot || shell
```

**Centos/RHEL 6系列系统内核不支持efi启动，Centos/RHEL 7.3系统内核存在BUG在UEFI下不支持使用ipxe直接启动, 采用以下方案**

该方案使用制作独立的grub镜像，将目标操作系统内核，根文件系统与grub菜单打包成memdisk，使用ipxe直接启动该grub镜像。

1.  安装grub2-mkimage
2.  获取目标系统内核（vmlinuz）与初始根文件系统映像（initrd.img），将其拷贝到当前目录
3.  在当前目录下创建/boot/grub/目录，新建grub_cfg文件，编写grub菜单，为兼容lightning自动化测试，该菜单第一选项为使用KS脚本自动安装。
  
    ```grub2
    set timeout=5    # 默认时间
    set default=0    # 默认菜单
    insmod net
    insmod efinet
    insmod tftp
    insmod gzio
    insmod part_gpt
    insmod efi_gop
    insmod efi_uga
    insmod video_bochs
    insmod video_cirrus
    insmod all_video

    menuentry 'RHEL 7.3 Server AUTO' --class os {
      echo 'Loading vmlinuz ...'
      linux (memdisk)/vmlinuz method=http://os.com/image/rhel7.3 ks=http://os.com/image/rhel7.3/ks.cfg ip=dhcp
      echo 'Loading initial ramdisk ...'
      initrd (memdisk)/initrd.img
    }
    menuentry 'RHEL 7.3 Server' --class os {
      echo 'Loading vmlinuz ...'
      linux (memdisk)/vmlinuz method=http://os.com/image/rhel7.3 ip=dhcp
      echo 'Loading initial ramdisk ...'
      initrd (memdisk)/initrd.img
    }

    ```

4.  制作memdisk tar包：`tar -cvf memdisk.tar boot/ vmlinuz initrd.img`
5.  制作grub with memdisk镜像

    ```shell
    grub2-mkimage \
    -v --memdisk=memdisk.tar \    # 指定memdisk
    -o centos7.3.efi \    # 指定输出文件名
    -O x86_64-efi \    # 指定grub类型
    memdisk tar echo sleep linux linuxefi lsefi reboot multiboot linux16 boot efi_uga gfxterm help video    # 附加module
    ```
6. 使用该centos7.3.efi文件即可启动安装系统。

> 菜单位置/home/pxe/http/ipxe.d/efimenu.ipxe


### 4.2 新增Auto PXE系统

#### 4.2.1 Legacy模式新增系统

1. 在mysql pxe数据库的os table中添加该系统。
2. 在os_mission table中添加该系统，mode字段填写UEFI或Legacy模式，该模式查阅mode表填写
3. 在kernel_name, initrd_name 字段分别填写内核文件名与初始根文件映像名，args为内核启动参数。lightning会自动使用tftp://os.com/image/${os_name}/${kernel_name}, tftp://os.com/image/${os_name}/${initrd_name}并附加参数生成安装脚本。*注意：必须在tftp指定目录创建与os_name字段相同的目录，并放置kernel与initrd。在http的image目录下放置安装镜像解压文件。*
4. 若系统使用grub2打包的兼容性方案，则无需填写args，lightning会将不填写args的项视为grub2启动，文件位置为tftp image目录下以os_name命名的文件夹。

### 4.3 使用Pikachu命令行工具管理任务

Pikachu为简单的命令行管理工具，用于为Lightning添加新的OS测试任务。
使用时请修改窗口属性为合适大小

![pikachu_setting](C:\Users\Administrator\Desktop\lighting\pictures\pikachu_setting.PNG)

该命令行工具有3个视图，分别为mac,set,record视图

* 在mac视图支持以下命令：

  *  show：查看当前待测机台mac地址

  * add：添加一个mac地址，当有待测机台加入时

  * mac：进入选择目标mac进入其record set视图

  * exit：退出命令行

  * help：显示帮助信息

    

* record set视图：

  * show：查看当前mac地址下测试集信息

  * add：新建一个测试集，并且指定其状态

  * set：选择目标测试集，进入其record视图

  * modify：修改测试集状态

  * exit：退出当前视图，返回mac视图

  * help：显示当前视图帮助信息

    

* record 视图：

  * show：查看当前测试集下record信息
  * add：新建一个测试项，指定状态，任务，任务类型
  * os：显示可选os列表
  * modify：修改测试项状态
  * exit：退出当前视图，返回record set视图
  * help：显示当前视图帮助信息
    

## 5. 附录

### 5.1 mkefi.py使用
mkefi.py为方便制作centos/rhel grub镜像的脚本，位于/home/ipxe/http/grub/文件夹
该脚本会从/var/lib/tftpboot/image/目录下拿取kernel与initrd，并使用/home/ipxe/http/wimboot/目录下的grub菜单文件。在当前目录以os名新建文件夹，生成grub.efi文件。

### 5.2 OS install状态定义
OS状态码|说明
-|-|
-1|手动关闭的任务|
0|未执行任务|
1|正在执行的安装任务|
2|已经完成的安装任务|

### 5.3 IPXE UEFI菜单

```ipxe
#!ipxe
  set menu-timeout 10000
  set menu-default ipxe
  set image  tftp://os.com/Image
  set method http://os.com/image
  set tftp tftp://os.com
  set http http://os.com
  isset ${ip} || dhcp
  set retry:int32 0

:start
  menu iPXE Boot Menu
  item --gap -- ----------------------------------------REBOOT--------------------------------------------
  item reboot   Reboot
  item --gap -- ----------------------------------------ADVANCED-------------------------------------------
  item ipxe	Auto Test
  item grubfm GRUB File Mananger
  item --gap -- ----------------------------------------OS INSTALL-----------------------------------------
  item --gap -- ------------------------------------------CentOS-------------------------------------------
  item centos7.4	Install CentOS 7.4
  item centos7.3	Install CentOS 7.3
  item centos7.2	Install CentOS 7.2
  item centos7.1	Install CentOS 7.1
  item centos7.0	Install CentOS 7.0
  item centos6.9	Install CentOS 6.9
  item centos6.8	Install CentOS 6.8
  item centos6.7	Install CentOS 6.7
  item centos6.6	Install CentOS 6.6
  item centos6.5	Install CentOS 6.5
  item centos6.3	Install CentOS 6.3
  item --gap -- -------------------------------------------RHEL--------------------------------------------
  item rhel7.3		Install RHEL 7.3
  item rhel7.2		Install RHEL 7.2
  item rhel7.1		Install RHEL 7.1
  item rhel7.0		Install RHEL 7.0
  item rhel6.9		Install RHEL 6.9
  item rhel6.8		Install RHEL 6.8
  item rhel6.7		Install RHEL 6.7
  item rhel6.6		Install RHEL 6.6
  item rhel6.5		Install RHEL 6.5
  item --gap -- -------------------------------------------SLES--------------------------------------------
  item sles12sp3	Install SLES12SP3
  item sles12sp2	Install SLES12SP2
  item sles12sp1	Install SLES12SP1
  item sles12		Install SLES12
  item sles11sp4	Install SLES11SP4
  item sles11sp3	Install SLES11SP3
  item --gap -- -------------------------------------------Ubuntu------------------------------------------
  item ubuntu12.04.5	Install Ubuntu12.04.5
  item ubuntu14.04.4	Install Ubuntu14.04.4
  item ubuntu14.10	Install Ubuntu14.10
  item ubuntu15.04	Install Ubuntu15.04
  item ubuntu16.04	Install Ubuntu16.04
  item --gap -- -------------------------------------------Kylin-------------------------------------------
  item kylintrusted6.0	Install Kylin Trusted 6.0
  item kylinadvanced7.2	Install Kylin Trusted 7.2
  item --gap -- -------------------------------------------Asianux------------------------------------------
  item asianux7.0	Install Asianux 7.0
  item --gap -- -------------------------------------------VMware Esxi---------------------------------------
  item esxi6.5d	Install VMware Esxi6.5d
  item esxi6.0u3	Install VMware Esxi6.0u3
  item esxi6.0u2	Install VMware Esxi6.0u2
  item esxi6.0u1	Install VMware Esxi6.0u1
#@  item --gap -- -------------------------------------------Windows------------------------------------------
#@  item window2012r2	Install Windows2012R2
#@  item windows2016	Install Windows2016
#@  item --gap -- ------------------------------------------GRUB---------------------------------------------
#@  item grub		GRUB2 with WIMBOOT

  choose --timeout ${menu-timeout} --default ${menu-default} selected
  imgfree
  goto ${selected}


:fail
  shell

:retry
  inc retry
  iseq ${retry} 4 || echo Retrying Downloading ${retry} Times ... ||
  iseq ${retry} 4 && echo Download Failed && shell ||
  sleep 3
  iseq ${retry} 4 || goto ${nowboot} || goto fail

:kylintrusted6.0
  set nowboot kylintrusted6.0
  echo Starting Kylin Trusted 6.0
  kernel --timeout 30000 ${http}/grub/kylin_trusted_6.0_b31/kylin_trusted_6.0_b31.efi || goto retry
  boot || goto fail

:kylinadvanced7.2
  set nowboot kylinadvanced7.2
  echo Starting Kylin Advanced 7.2
  kernel --timeout 30000 ${http}/grub/kylin_advanced_7.2/kylin_advanced_7.2.efi || goto retry
  boot || goto fail

:asianux7.0
  set nowboot asianux7.0
  echo Starting Asianux 7.0
  kernel --timeout 30000 ${http}/grub/asianux7.0/asianux7.0.efi || goto retry
  boot || goto fail

:centos7.4
  set nowboot centos7.4
  echo Starting CentOS 7.4 Installer
  initrd --timeout 30000 ${image}/centos7.4/initrd.img || goto retry
  kernel --timeout 30000 ${image}/centos7.4/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/centos7.4 ip=dhcp
  boot || goto fail

:centos7.3
  set nowboot centos7.3
  echo Starting centos7.3
  kernel --timeout 30000 ${http}/grub/centos7.3/centos7.3.efi || goto retry
  boot || shell

:centos7.2
  set nowboot centos7.2
  echo Starting CentOS 7.2 Installer
  initrd --timeout 30000 ${image}/centos7.2/initrd.img || goto retry
  kernel --timeout 30000 ${image}/centos7.2/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/centos7.2 ip=dhcp
  boot || goto fail

:centos7.1
  set nowboot centos7.1
  echo Starting CentOS 7.1 Installer
  initrd --timeout 30000 ${image}/centos7.1/initrd.img || goto retry
  kernel --timeout 30000 ${image}/centos7.1/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/centos7.1 ip=dhcp
  boot || goto fail

:centos7.0
  set nowboot centos7.0
  echo Starting CentOS 7.0 Installer
  initrd --timeout 30000 ${image}/centos7.0/initrd.img || goto retry
  kernel --timeout 30000 ${image}/centos7.0/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/centos7.0 ip=dhcp
  boot || goto fail

:centos6.9
  set nowboot centos6.9
  echo Starting Centos6.9
  kernel --timeout 30000 ${http}/grub/centos6.9/centos6.9.efi || goto retry
  boot || shell

:centos6.8
  set nowboot centos6.8
  echo Starting Centos6.8
  kernel --timeout 30000 ${http}/grub/centos6.8/centos6.8.efi || goto retry
  boot || shell

:centos6.7
  set nowboot centos6.7
  echo Starting Centos6.7
  kernel --timeout 30000 ${http}/grub/centos6.7/centos6.7.efi || goto retry
  boot || shell

:centos6.6
  set nowboot centos6.6
  echo Starting Centos6.6
  kernel --timeout 30000 ${http}/grub/centos6.6/centos6.6.efi || goto retry
  boot || shell

:centos6.5
  set nowboot centos6.5
  echo Starting Centos6.5
  kernel --timeout 30000 ${http}/grub/centos6.5/centos6.5.efi || goto retry
  boot || shell


:centos6.3
  set nowboot centos6.3
  echo Starting Centos6.3
  kernel --timeout 30000 ${http}/grub/centos6.3/centos6.3.efi || goto retry
  boot || shell

:rhel7.4
  set nowboot rhel7.4
  echo Starting RHEL 7.4 Installer
  initrd --timeout 30000 ${image}/rhel7.4/initrd.img || goto retry
  kernel --timeout 30000 ${image}/rhel7.4/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/rhel7.4 ip=dhcp
  boot || goto fail

:rhel7.3
  set nowboot rhel7.3
  echo Starting RHEL7.3
  kernel --timeout 30000 ${http}/grub/rhel7.3/rhel7.3.efi || goto retry
  boot || shell

:rhel7.2
  set nowboot rhel7.2
  echo Starting RHEL 7.2 Installer
  initrd --timeout 30000 ${image}/rhel7.2/initrd.img || goto retry
  kernel --timeout 30000 ${image}/rhel7.2/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/rhel7.2 ip=dhcp
  boot || goto fail

:rhel7.1
  set nowboot rhel7.1
  echo Starting RHEL 7.1 Installer
  initrd --timeout 30000 ${image}/rhel7.1/initrd.img || goto retry
  kernel --timeout 30000 ${image}/rhel7.1/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/rhel7.1 ip=dhcp
  boot || goto fail

:rhel7.0
  set nowboot rhel7.0
  echo Starting RHEL 7.0 Installer
  initrd --timeout 30000 ${image}/rhel7.0/initrd.img || goto retry
  kernel --timeout 30000 ${image}/rhel7.0/vmlinuz || goto retry
  imgargs vmlinuz initrd=initrd.img method=${method}/rhel7.0 ip=dhcp
  boot || goto fail

:rhel6.9
  set nowboot rhel6.9
  echo Starting RHEL6.9
  kernel --timeout 30000 ${http}/grub/rhel6.9/rhel6.9.efi || goto retry
  boot || shell

:rhel6.8
  set nowboot rhel6.8
  echo Starting RHEL6.8
  kernel --timeout 30000 ${http}/grub/rhel6.8/rhel6.8.efi || goto retry
  boot || shell

:rhel6.7
  set nowboot rhel6.7
  echo Starting RHEL6.7
  kernel --timeout 30000 ${http}/grub/rhel6.7/rhel6.7.efi || goto retry
  boot || shell

:rhel6.6
  set nowboot rhel6.6
  echo Starting RHEL6.6 with WIMBOOT
  kernel --timeout 30000 ${http}/grub/rhel6.6/rhel6.6.efi || goto retry
  boot || shell

:rhel6.5
  set nowboot rhel6.5
  echo Starting RHEL6.5
  kernel --timeout 30000 ${http}/grub/rhel6.5/rhel6.5.efi || goto retry
  boot || shell


:rhel6.3
  set nowboot rhel6.3
  echo Starting RHEL6.3 with WIMBOOT
  kernel --timeout 30000 ${http}/grub/rhel6.3/rhel6.3.efi || goto retry
  boot || shell

:sles11sp3
  set nowboot sles11sp3
  echo Starting SLES11SP3 Installer
  initrd --timeout 30000 ${tftp}/Image/sles11sp3/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles11sp3/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles11sp3/
  boot || shell

:sles11sp4
  set nowboot sles11sp4
  echo Starting SLES11SP4 Installer
  initrd --timeout 30000 ${tftp}/Image/sles11sp4/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles11sp4/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles11sp4/
  boot || shell

:sles12sp1
  set nowboot sles12sp1
  echo Starting SLES12SP1 Installer
  initrd --timeout 30000 ${tftp}/Image/sles12sp1/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles12sp1/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles12sp1/
  boot || shell

:sles12
  set nowboot sles12
  echo Starting SLES12 Installer
  initrd --timeout 30000 ${tftp}/Image/sles12/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles12/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles12/
  boot || shell

:sles12sp2
  set nowboot sles12sp2
  echo Starting SLES12SP2 Installer
  initrd --timeout 30000 ${tftp}/Image/sles12sp2/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles12sp2/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles12sp2/
  boot || shell


:sles12sp3
  set nowboot sles12sp3
  echo Starting SLES12SP3 Installer
  initrd --timeout 30000 ${tftp}/Image/sles12sp3/initrd || goto retry
  kernel --timeout 30000 ${tftp}/Image/sles12sp3/linux || goto retry
  imgargs linux initrd=initrd ip=dhcp install=${method}/sles12sp3/
  boot || shell


:ubuntu12.04.5
  set nowboot ubuntu12.04.5
  echo Starting Ubuntu12.04.5 Installer
  initrd --timeout 30000 ${tftp}/Image/ubuntu12.04.5/initrd.gz || goto retry
  kernel --timeout 30000 ${tftp}/Image/ubuntu12.04.5/linux || goto retry
  imgargs linux initrd=initrd.gz gfxpayload=800x600x16,800x600 --auto=true ks=http://os.com/image/Ubuntu12.04.5/url.cfg url=http://os.com/image/Ubuntu12.04.5/preseed.cfg quiet ksdevice=link
  boot || shell 

:ubuntu14.04.4
  set nowboot ubuntu14.04.4
  echo Starting Ubuntu14.04.4 Installer
  initrd --timeout 30000 ${tftp}/Image/ubuntu14.04.4/initrd.gz || goto retry
  kernel --timeout 30000 ${tftp}/Image/ubuntu14.04.4/linux || goto retry
  imgargs linux initrd=initrd.gz gfxpayload=800x600x16,800x600 --auto=true ks=http://os.com/image/Ubuntu14.04.4/url.cfg url=http://os.com/image/Ubuntu14.04.4/preseed.cfg quiet ksdevice=link
  boot || shell 

:ubuntu14.10
  set nowboot ubuntu14.10
  echo Starting Ubuntu14.10 Installer
  initrd --timeout 30000 ${tftp}/Image/ubuntu14.10/initrd.gz || goto retry
  kernel --timeout 30000 ${tftp}/Image/ubuntu14.10/linux || goto retry
  imgargs linux initrd=initrd.gz gfxpayload=800x600x16,800x600 --auto=true ks=http://os.com/image/Ubuntu14.10/url.cfg url=http://os.com/image/Ubuntu14.10/preseed.cfg quiet ksdevice=link
  boot || shell 

:ubuntu15.04
  set nowboot ubuntu15.04
  echo Starting Ubuntu15.04 Installer
  initrd --timeout 30000 ${tftp}/Image/ubuntu15.04/initrd.gz || goto retry
  kernel --timeout 30000 ${tftp}/Image/ubuntu15.04/linux || goto retry
  imgargs linux initrd=initrd.gz gfxpayload=800x600x16,800x600 --auto=true ks=http://os.com/image/Ubuntu15.04/url.cfg url=http://os.com/image/Ubuntu15.04/preseed.cfg quiet ksdevice=link
  boot || shell 


:ubuntu16.04
  set nowboot ubuntu16.04
  echo Starting Ubuntu16.04 Installer
  initrd --timeout 30000 ${tftp}/Image/ubuntu16.04/initrd.gz || goto retry
  kernel --timeout 30000 ${tftp}/Image/ubuntu16.04/linux || goto retry
  imgargs linux initrd=initrd.gz gfxpayload=800x600x16,800x600 --auto=true ks=http://os.com/image/ubuntu16.04/url.cfg url=http://os.com/image/ubuntu16.04/preseed.cfg quiet ksdevice=link
  boot || shell 


:esxi6.5d
  set nowboot esxi6.5d
  echo Starting esxi6.5d Installer
  initrd --timeout 30000 ${tftp}/Image/esxi6.5d/boot.cfg || goto retry
  kernel --timeout 30000 ${tftp}/Image/esxi6.5d/mboot.efi || goto retry
  imgargs mboot.efi ks=tftp://192.168.1.1/Image/esxi6.5d/ks.cfg
  boot || shell 

:esxi6.0u1
  set nowboot esxi6.0u1
  echo Starting esxi6.0u1 Installer
  initrd --timeout 30000 ${tftp}/Image/esxi6.0u1/boot.cfg || goto retry
  kernel --timeout 30000 ${tftp}/Image/esxi6.0u1/mboot.efi || goto retry
  boot || shell 

:esxi6.0u2
  set nowboot esxi6.0u2
  echo Starting esxi6.0u2 Installer
  initrd --timeout 30000 ${tftp}/Image/esxi6.0u2/boot.cfg || goto retry
  kernel --timeout 30000 ${tftp}/Image/esxi6.0u2/mboot.efi || goto retry
  boot || shell 

:esxi6.0u3
  set nowboot esxi6.0u3
  echo Starting esxi6.0u3 Installer
  initrd --timeout 30000 ${tftp}/Image/esxi6.0u3/boot.cfg || goto retry
  kernel --timeout 30000 ${tftp}/Image/esxi6.0u3/mboot.efi || goto retry
  boot || shell 

:reboot
  echo reboot
  reboot || shell
  menu default

:ipxe
  echo chain boot from ${iPXE}
  chain http://os.com/auto/uefi?mac=${mac} || shell


:grubfm
  echo GRUB File Mananger
  chain http://os.com/grubfm/grubfmx64.efi || shell

#!:windows2016
#! echo sanboot windows2016pe
#! sanboot --no-describe --drive 0xff  ${http}/image/win2016pe.iso

#!:windows2012r2
#! echo sanboot windows2012r2pe
#! sanboot --no-describe --drive 0xff  ${http}/image/win2012r2pe.iso

```

### 5.4 tftp目录文件结构

```shell
tftpboot
├── 50-DA-00-5E-9C-DB
├── baidu
│   ├── initrd-2.6.32_1-14-0-0.img
│   └── vmlinuz-2.6.32_1-14-0-0
├── Baidu
│   ├── initrd-2.6.32_1-19-0-0-rc5.img
│   └── vmlinuz-2.6.32_1-19-0-0-rc5
├── bakeupefidefault
├── boot
│   ├── bcd
│   ├── bootfix.bin
│   ├── boot.sdi
│   ├── bootsect.exe
│   ├── en-us
│   ├── etfsboot.com
│   ├── fonts
│   ├── memtest.exe
│   └── resources
├── bootmgr
├── bootmgr.efi
├── BOOTX64.efi
├── CAS0209
│   ├── boot-screens
│   ├── initrd.gz
│   ├── linux
│   ├── pxelinux.0
│   └── pxelinux.cfg
├── CASE0503
│   ├── initrd.gz
│   └── linux
├── CentOS6.2x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS6.3x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS6.5x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS6.6x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS6.8x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS6.9x64
│   ├── initrd.img
│   ├── TRANS.TBL
│   └── vmlinuz
├── CentOS7.0x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS7.1x64
│   ├── initrd.img
│   ├── TRANS.TBL
│   ├── upgrade.img
│   └── vmlinuz
├── CentOS7.2x64
│   ├── initrd.img
│   └── vmlinuz
├── CentOS7.3x64
│   ├── initrd.img
│   └── vmlinuz
├── clone
│   ├── initrd.img
│   └── vmlinuz
├── efidefault
├── galaxy_640x480.jpg
├── galaxy_800x600.jpg
├── grubfm
│   ├── grubfmia32.efi
│   ├── grubfm.iso
│   └── grubfmx64.efi
├── H3C.jpg
├── iFIST1.00.01x64
│   ├── initrd.img
│   └── vmlinuz
├── IFISTx64
│   ├── initrd.img
│   └── vmlinuz
├── Image
│   ├── asianux7.0
│   ├── CASE0306
│   ├── centos6.3
│   ├── centos6.5
│   ├── centos6.6
│   ├── centos6.7
│   ├── centos6.8
│   ├── centos6.9
│   ├── centos7
│   ├── centos7.0
│   ├── centos7.1
│   ├── centos7.2
│   ├── centos7.3
│   ├── centos7.4
│   ├── esxi6.0u1
│   ├── esxi6.0u2
│   ├── esxi6.0u3
│   ├── esxi6.5d
│   ├── iqiyi
│   ├── kylin_advanced_7.2
│   ├── kylin_trusted_6.0_b31
│   ├── memdisk
│   ├── rhel6.5
│   ├── rhel6.6
│   ├── rhel6.7
│   ├── rhel6.8
│   ├── rhel6.9
│   ├── rhel7.0
│   ├── rhel7.1
│   ├── rhel7.2
│   ├── rhel7.3
│   ├── sles11sp3
│   ├── sles11sp4
│   ├── sles12
│   ├── sles12sp1
│   ├── sles12sp2
│   ├── sles12sp3
│   ├── ubuntu12.04.5
│   ├── ubuntu14.04.4
│   ├── ubuntu14.10
│   ├── ubuntu15.04
│   ├── ubuntu16.04
│   ├── win2012r2
│   ├── Win2012_R2.iso
│   ├── win2012r2pe.iso
│   ├── win2016pe.iso
│   ├── xen7.1
│   └── xen7.2
├── LETV
│   ├── initrd.img
│   └── vmlinuz
├── menu.c32
├── MPT
│   ├── initrd-mpt-new.img
│   ├── mpt_centos20171227_3790953388.img
│   ├── mpt_centos20180125_3923548331.img
│   ├── mpt_centos20180131_3949938949.img
│   ├── mpt_centos20180204_3970388857.img
│   ├── mpt_centos20180312_4142020988.img
│   └── vmlinuz-2.6.32-573.el6.x86_64
├── new\ file~
├── Pikachu_ipxe.efi
├── Pikachu_ipxe.lkrn
├── pxeboot.0
├── pxelinux.0
├── pxelinux.cfg
│   ├── 01-ec-b1-d7-42-29-f9
│   ├── bak
│   ├── default
│   ├── default~
│   ├── default.ipxe
│   ├── esxi6.0u1
│   ├── esxi6.0u2
│   ├── esxi6.0u3
│   ├── esxi6.5d
│   └── H3C.jpg
├── reboot.c32
├── RHEL6.5x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL6.6x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL6.7x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL6.8x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL7.0x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL7.1x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL7.2x64
│   ├── initrd.img
│   └── vmlinuz
├── RHEL7.3x64
│   ├── initrd.img
│   └── vmlinuz
├── SLES11.3x64
│   ├── initrd
│   └── linux
├── SLES11.4x64
│   ├── initrd
│   └── linux
├── SLES11SP1x64
│   ├── initrd
│   └── linux
├── SLES11SP1x86
│   ├── initrd
│   └── linux
├── SLES12SP1x64
│   ├── initrd
│   └── linux
├── SLES12SP2x64
│   ├── initrd
│   └── linux
├── SLES12x64
│   ├── initrd
│   └── linux
├── splash.xpm.gz
├── TLinux
│   ├── initrd-mpt--2016-12-11-centos6.7.img
│   └── vmlinuz
├── Tlinux_20161109
│   ├── INITRD.IMG
│   └── VMLINUZ
├── Ubuntu12.4x64
│   ├── boot-screens
│   ├── initrd.gz
│   ├── linux
│   ├── pxelinux.0
│   └── pxelinux.cfg
├── Ubuntu14.04.3x64
│   ├── initrd.gz
│   └── linux
├── Ubuntu14.10x64
│   ├── boot-screens
│   ├── initrd.gz
│   ├── linux
│   ├── pxelinux.0
│   └── pxelinux.cfg
├── Ubuntu15.04x64
│   ├── boot-screens
│   ├── initrd.gz
│   ├── linux
│   ├── pxelinux.0
│   └── pxelinux.cfg
├── Ubuntu16.04x64
│   ├── boot-screens
│   ├── initrd.gz
│   ├── linux
│   ├── pxelinux.0
│   └── pxelinux.cfg
├── vesamenu.c32
├── VMWARE5.5.0
│   ├── boot.cfg
│   └── mboot.c32
├── VMWARE5.5U3
│   ├── BOOT.CFG
│   └── MBOOT.C32
├── VMWARE6.0U2
│   ├── BOOT.CFG
│   └── MBOOT.C32
├── Win2012R2x64
│   └── sources
├── X86_IMG_CENTOS6U5
│   ├── initrd0.img
│   ├── V103
│   └── vmlinuz0
├── X86_IMG_CENTOS7U2
│   ├── V101
│   ├── V103
│   ├── V105
│   └── V106
├── X86_IMG_CENTOS7U3
│   └── V100
├── X86_TEST_CENTOS6U5
│   └── baidu
└── ZhuangBeiCentOS7.2x64
    ├── initrd0.img
    └── vmlinuz0
```