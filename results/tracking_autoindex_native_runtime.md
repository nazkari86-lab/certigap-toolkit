# Native TrackingAutoIndex Runtime Benchmark

This benchmark executes the same deterministic phased streams at `n=64,256,4096`.
Native rows use five median C++ repetitions; the Python reference uses three.
Construction is excluded, while in-stream migrations and WFA accounting are included.

## Results

- Correctness checksum agreement across every implementation/configuration: `True`.
- Native rebuild-aware production latency: `61.23` to `317.23` ns/op.
- Native uniform-metric production is `173.2x` to `15952.7x` faster than the full Python uniform-metric research reference on the matching streams.
- Against the fastest fixed C++ backend, online tracking costs `11.2x` median and `21.7x` worst-case. Tracking is therefore not a drop-in latency winner when the best backend is known in advance.
- Recording the full audit trajectory costs `2.04x` median over production mode.
- On `read_mostly` at `n=256,4096`, rebuild-aware migration reduces switching by `360x` to `394x` and improves runtime by `3.6x` to `16.4x` versus the naive uniform migration model.

## Interpretation

The native core removes Python from the hot path and makes causal representation
tracking practical when workload adaptation matters more than minimum single-backend
latency. The rebuild-aware matrix is a positive symmetric metric, so it preserves the
classical metric precondition checked by the API. Arbitrary directed matrices remain
available for empirical deployment, but the API returns no competitive factor for them.

Raw data: `tracking_autoindex_native_runtime.csv`.
