#!/bin/sh
set -e
CONDA_PATH="http://os.com/tools/Miniconda3.sh"
PYIPMI_PATH="http://os.com/tools/pyipmi.py"
download () {
	wget -N $CONDA_PATH -O $(basename ${CONDA_PATH}) -q
	wget -N $PYIPMI_PATH -O $(basename ${PYIPMI_PATH}) -q
}

 set_mode () {
	chmod 755 $(basename ${CONDA_PATH})
	chmod 755 $(basename ${PYIPMI_PATH})
}

find_path () {
   redhat=`cat /proc/version | grep -i "red hat" |wc -l`
   suse=`cat /proc/version | grep -i "suse" |wc -l`
   ubuntu=`cat /proc/version | grep -i "ubuntu" |wc -l`
   kylin=`cat /proc/version | grep -i "neokylin" |wc -l`
   if [ $redhat -eq 1 ] || [ $kylin -eq 1 ]
   then
   echo	/etc/rc.d/rc.local
   elif [ $suse -eq 1 ]
   then
   echo /etc/rc.d/boot.local
   elif [ $ubuntu -eq 1 ]
   then
   echo /etc/rc.local
   else
   echo "unknown system"
   fi
}

boot_path=`find_path`
download || echo "Download Failed"
set_mode || echo "Change Mode Failed"
if_conda = `type conda 2> /dev/null`
if [ -z "$conda" ];then
    sh $(basename ${CONDA_PATH}) -bf
fi
# export PATH="/root/miniconda3/bin:$PATH"
# echo 'export PATH="/root/miniconda3/bin:$PATH"' >> /root/.bashrc
# source /root/.bashrc
# echo 'export PATH="/root/miniconda3/bin:$PATH"' >> $boot_path
# echo '/usr/bin/python /tasktracker.py' >> $boot_path
# python2 pyipmi.py pxe || python pyipmi pxe || python3 pyipmi pxe
echo '===============OS_INSTALL_BEGIN Shell Script Done================='
# sleep 10
# reboot