# SOSD-Derived Streaming Results

- Full compressed distributions validated: `4`.
- Dataset/workload cases: `16`.
- CertiGap partial routing beats `std::lower_bound` in `10/16` cases.
- Fastest-method counts: `eytzinger` 7, `sosd_radix_spline` 9.

These are local-machine measurements on deterministic rank samples. They are not the official SOSD harness, and all four query workloads are synthetic. The CSV retains every loss and includes build time and index size.
