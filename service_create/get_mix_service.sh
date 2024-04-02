#!/bin/bash
sudo touch /lib/systemd/system/getmix.service
sudo cat <<EOF >/lib/systemd/system/getmix.service
[Unit]
Description=mix log service
After=syslog.target
After=network.target

[Service]
LimitMEMLOCK=infinity
LimitNOFILE=65535
RestartSec=2s
Type=simple
User=igor
Group=igor
WorkingDirectory=$PWD
ExecStart=/usr/bin/python3  $PWD/get_mixes.py
Restart=always
Environment=USER=igor HOME=$PWD
[Install]
WantedBy=multi-user.target
EOF