sudo cat <<EOF >/lib/systemd/system/streamlitinterface.service
[Unit]
Description=streamlit for inteface
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
ExecStart=streamlit run --server.port 8000 $PWD/frontend.py 
Restart=always
Environment=USER=igor HOME=$PWD
[Install]
WantedBy=multi-user.target
EOF