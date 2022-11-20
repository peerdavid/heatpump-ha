# heatpump-ha
Connect a heatpump to home assistant via an MQTT Bus.

# How to run as a service

# Run as service
Create the following file with `sudo nano /etc/systemd/system/ha_bridge.service`:
```
[Unit]
Description=HomeAssistant Bridge
After=multi-user.target
[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 /home/pi/Dev/heatpump-ha/ha_bridge.py --mqtt_server=YOUR_MQTT_SERVER --mqtt_user=YOUR_USER --mqtt_passwd=YOUR_PASSWORD
[Install]
WantedBy=multi-user.target
```

Next reload the deamon and enable our service so it works also after a restart:
```
sudo systemctl daemon-reload
sudo systemctl enable ha_bridge.service
sudo systemctl start ha_bridge.service
```

To show output logs of your service, simply call
```
journalctl -f -u ha_bridge.service
```
