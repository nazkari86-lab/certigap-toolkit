# SQLite and YCSB-Compatible Pilot

This is a real SQLite execution pilot with YCSB-compatible A/B/C/F operation mixes plus a CertiGap-specific range workload. It is not the official Java YCSB harness and not a SQLite extension.

| Workload | Backend | Median ns/op | 95% bootstrap CI | p95 |
|---|---|---:|---:|---:|
| A | sqlite_btree | 649.8 | [640.2, 676.1] | 726.3 |
| A | fenwick | 209.3 | [200.2, 222.4] | 223.9 |
| A | certigap_h | 559.7 | [551.4, 568.7] | 591.9 |
| B | sqlite_btree | 706.4 | [702.9, 713.1] | 788.1 |
| B | fenwick | 52.7 | [52.3, 58.8] | 59.5 |
| B | certigap_h | 152.1 | [150.1, 173.4] | 183.8 |
| C | sqlite_btree | 662.9 | [645.5, 671.6] | 771.4 |
| C | fenwick | 35.6 | [35.4, 35.7] | 41.0 |
| C | certigap_h | 114.8 | [112.5, 116.5] | 126.5 |
| F | sqlite_btree | 1016.0 | [975.9, 1042.5] | 1122.6 |
| F | fenwick | 251.1 | [241.8, 252.9] | 280.6 |
| F | certigap_h | 631.6 | [601.6, 660.4] | 785.9 |
| R | sqlite_btree | 1187.0 | [1127.2, 1238.3] | 1382.0 |
| R | fenwick | 281.5 | [251.0, 293.3] | 407.5 |
| R | certigap_h | 284.9 | [260.5, 297.6] | 307.6 |
