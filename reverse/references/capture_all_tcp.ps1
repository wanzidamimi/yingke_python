pktmon filter remove
pktmon filter add alltcp -t TCP
pktmon start --capture --pkt-size 0 --flags 0x112 --file-name d:\Scrapy-project\yingke_python\reverse\logs\danmu_alltcp.etl
Start-Sleep -Seconds 150
pktmon stop
pktmon etl2pcap d:\Scrapy-project\yingke_python\reverse\logs\danmu_alltcp.etl -o d:\Scrapy-project\yingke_python\reverse\logs\danmu_alltcp.pcapng
