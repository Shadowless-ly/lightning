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
if [ -z "$conda" ];then
    sh $(basename ${CONDA_PATH}) -bf
fi
# export PATH="/root/miniconda3/bin:$PATH"
# export PATH="/miniconda3/bin:$PATH"
# echo 'export PATH="/miniconda3/bin:$PATH"'
# source /root/.bashrc
# echo 'export PATH="/miniconda3/bin:$PATH"' >> $boot_path
# echo '/usr/bin/python /tasktracker.py' >> $boot_path
# chmod a+x $boot_path >> /lightning.log
# python2 pyipmi.py disk || python pyipmi disk || python3 pyipmi disk
echo '==============ENV Shell Script Done====================='
# ping 192.168.1.1 -c 3



