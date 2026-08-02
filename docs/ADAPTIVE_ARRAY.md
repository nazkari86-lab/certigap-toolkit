# Adaptive Array

`certigap::adaptive_array<T>` is the low-friction runtime interface for users
who want automatic profiling without manually calling `observe_*` or
`optimize()`.

```cpp
#include <vector>
#include "certigap.hpp"

certigap::AutoTunePolicy policy;
policy.profile_path = "catalog.certigap-profile";

certigap::adaptive_array<double> data(values, policy);
auto value = data.get(4);
auto total = data.range_sum(10, 30);
data.update(4, 100.0);
```

The wrapper follows normal C++ indexing: positions are zero-based and ranges
are half-open `[first,last)`. The lower-level `certigap::Index` retains its
existing one-based inclusive API.

## Automatic Policy

Tracked operations build the workload profile. At `warmup_operations`, the
wrapper scores the five native runtime candidates. A backend change is retained
only when its modeled relative improvement reaches
`minimum_relative_improvement`; otherwise the complete previous index is
restored. Later checks require both `check_interval` new operations and the
declared TV-drift threshold.

```cpp
policy.warmup_operations = 256;
policy.check_interval = 10'000;
policy.minimum_tv_drift = 0.10;
policy.minimum_relative_improvement = 0.05;
```

Automatic maintenance runs synchronously after a tracked operation. For a
latency-critical request path, disable it and move work to an application-safe
boundary:

```cpp
policy.automatic_maintenance = false;
// Request path records operations only.
data.range_sum(10, 30);
// Maintenance thread or explicit lifecycle boundary:
data.maintenance();
```

This is not an internally managed background thread. The application retains
control over scheduling and synchronization.

## Persistent Profiles

When `profile_path` is set, a prior workload profile is loaded during
construction and saved after decisions and, by default, on destruction. Values
are never written to this file; the calling application remains their source of
truth. Explicit persistence reports I/O errors:

```cpp
data.save_profile();
```

The strict text format records version, array size, aggregate, and positive
get/update/range weights. Import is transactional: malformed headers, size or
aggregate mismatches, invalid keys, non-finite weights, trailing content,
record-limit violations, and total-weight overflow are rejected before profile
state changes.

## Explainability

```cpp
std::cout << data.explain() << '\n';
```

Example:

```text
selected=fenwick observed=256 attempted=true switched=true improvement=81.2% reason="candidate passed deployment threshold"
```

Inspect a persisted profile without compiling the application:

```bash
certigap profile-explain catalog.certigap-profile
```

The percentage is improvement in the declared structural cost model. It is not
a measured latency prediction or a statistical no-regression guarantee. Use
SafeAutoIndex or Martingale SafeAutoIndex when deployment requires a
statistical gate.

The native validation artifact covers automatic point/range selection,
threshold rejection, explicit maintenance, and profile restoration in six
deterministic scenarios.
