# SQLite and YCSB-Compatible Pilot

This is a real SQLite execution pilot with YCSB-compatible A/B/C/F operation mixes plus a CertiGap-specific range workload. It is not the official Java YCSB harness and not a SQLite extension.

| Workload | Backend | Median ns/op | 95% bootstrap CI | p95 |
|---|---|---:|---:|---:|
| A | sqlite_btree | 1180.5 | [1177.9, 1188.2] | 1216.3 |
| A | fenwick | 373.0 | [372.0, 374.9] | 379.2 |
| A | certigap_h | 961.3 | [955.1, 969.4] | 997.7 |
| B | sqlite_btree | 1259.5 | [1248.2, 1454.6] | 1974.5 |
| B | fenwick | 195.4 | [177.7, 199.0] | 221.4 |
| B | certigap_h | 405.2 | [378.0, 453.8] | 612.3 |
| C | sqlite_btree | 1445.4 | [1301.4, 1886.0] | 2249.3 |
| C | fenwick | 85.3 | [84.1, 85.9] | 98.0 |
| C | certigap_h | 226.5 | [225.0, 231.4] | 241.8 |
| F | sqlite_btree | 1867.7 | [1844.8, 2118.2] | 2831.5 |
| F | fenwick | 479.6 | [426.6, 491.0] | 579.8 |
| F | certigap_h | 1598.0 | [1578.3, 1611.2] | 1648.5 |
| R | sqlite_btree | 3943.0 | [3050.1, 4961.9] | 6968.2 |
| R | fenwick | 728.6 | [624.9, 963.2] | 1334.9 |
| R | certigap_h | 775.1 | [652.7, 942.4] | 1298.5 |
