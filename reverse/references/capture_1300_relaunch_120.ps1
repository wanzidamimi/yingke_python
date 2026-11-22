pktmon filter remove
pktmon filter add inke1300_relaunch -t TCP -p 1300
pktmon start --capture --pkt-size 0 --flags 0x112 --file-name d:\Scrapy-project\yingke_python\reverse\logs\danmu_1300_relaunch.etl
Start-Sleep -Seconds 120
pktmon stop
pktmon etl2pcap d:\Scrapy-project\yingke_python\reverse\logs\danmu_1300_relaunch.etl -o d:\Scrapy-project\yingke_python\reverse\logs\danmu_1300_relaunch.pcapng
