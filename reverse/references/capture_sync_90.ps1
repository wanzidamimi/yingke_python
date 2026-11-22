pktmon filter remove
pktmon start --capture --pkt-size 0 --flags 0x112 --file-name d:\Scrapy-project\yingke_python\reverse\logs\danmu_sync.etl
Start-Sleep -Seconds 90
pktmon stop
pktmon etl2pcap d:\Scrapy-project\yingke_python\reverse\logs\danmu_sync.etl -o d:\Scrapy-project\yingke_python\reverse\logs\danmu_sync.pcapng
