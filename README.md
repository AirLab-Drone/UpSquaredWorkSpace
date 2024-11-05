# UpSquaredWorkSpace


### 相機權限 (RGB and thermal camera)
開機執行  
1. 編輯 rc.local 文件（如果沒有，則創建一個）：
```
sudo nano /etc/rc.local
```

2. 在文件中添加以下內容，將 chmod 指令放在 exit 0 之前：
```
#!/bin/bash
chmod 777 /dev/video*
exit 0
```

3. 確保 rc.local 文件具有可執行權限：
```
sudo chmod +x /etc/rc.local
```

重新差拔  
1. 創建規則文件
使用以下命令創建新的 udev 規則文件：
```
sudo nano /etc/udev/rules.d/99-video-devices.rules
```
2. 添加規則內容
在文件中添加以下內容，設置 /dev/video* 設備的讀寫權限：
```
KERNEL=="video[0-9]*", MODE="0666"
```
3. 保存並退出
在 nano 編輯器中：

按 Ctrl + O 以保存文件。
按 Ctrl + X 以退出編輯器。
4. 重新加載並觸發 udev 規則
添加規則後，使用以下命令重新加載 udev 規則並使其生效：
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

------ 


### aruco_detect
```
pip install pyudev
```


### flight_control
```
pip install opencv-python opencv-contrib-python scipy cv_bridge
```
mavros  
```
sudo apt install ros-humble-mavros ros-humble-mavros-extras
wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
chmod a+x install_geographiclib_datasets.sh
./install_geographiclib_datasets.sh
```
### GPIO
```sudo -H pip3 install python-periphery```



