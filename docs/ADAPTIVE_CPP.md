# Adaptive Single-Header C++

`certigap.hpp` is the lowest-friction CertiGap interface. It requires only a
C++17 compiler: no Python, generated file, JSON, or custom compiler.

For the simplest container-like interface, use `adaptive_array<T>`:

```cpp
certigap::AutoTunePolicy policy;
policy.profile_path = "workload.profile";
certigap::adaptive_array<double> data(values, policy);

auto total = data.range_sum(2, 30);  // Zero-based [2,30).
std::cout << data.explain() << '\n';
```

It profiles operations, automatically evaluates deployment after warmup,
rejects backend changes below a declared score improvement, and restores the
profile on the next run. See [`ADAPTIVE_ARRAY.md`](ADAPTIVE_ARRAY.md).

## Online Compiler

Download
[`cpp/certigap.hpp`](../cpp/certigap.hpp), add it beside the program, and use:

```cpp
#include <iostream>
#include <vector>
#include "certigap.hpp"

int main() {
    std::vector<double> values{1, 2, 3, 4, 5};
    certigap::Index index(values);

    for (int repetition = 0; repetition < 100; ++repetition) {
        index.observe_range(1, 4);
    }
    index.optimize();

    std::cout << index.selected_name() << '\n';
    std::cout << index.range_query(1, 4) << '\n';
}
```

Compile as C++17:

```bash
g++ -std=c++17 -O2 main.cpp -o app
./app
```

## Automatic Profiling

Normal operations record themselves:

```cpp
index.get(key);
index.range_query(left, right);
index.point_update(key, value);
```

Use `peek` and `peek_range` for const, untracked inspection:

```cpp
double value = index.peek(key);
double total = index.peek_range(left, right);
```

Explicit observations warm the profile without executing an operation:

```cpp
index.observe_get(key, count);
index.observe_range(left, right, count);
index.observe_update(key, count);
```

Do not record an operation explicitly and then execute its tracked form unless
double weight is intended.

## Selection

```cpp
certigap::OptimizeOptions options;
options.aggregate = certigap::Aggregate::Sum;
options.memory_limit_slots = 4096;
options.tail_weight = 0.10;

auto backend = index.optimize(options);
std::cout << certigap::backend_name(backend) << '\n';

for (const auto& row : index.leaderboard()) {
    std::cout << certigap::backend_name(row.backend)
              << " score=" << row.score
              << " feasible=" << row.feasible << '\n';
}
```

The deterministic runtime portfolio contains a contiguous array, Fenwick
tree, iterative segment tree, point-weighted CertiRange, and
range-coverage-weighted CertiRange.

The range topology uses a difference-array coverage profile, prefix sums, and
depth-safe weighted splits. Profiling does not expand every range over every
covered key. Backend unit costs, memory/build penalties, maximum depth, and a
mandatory CertiRange constraint are configurable. Fenwick is automatically
infeasible for minimum and maximum aggregates.

## Drift Reoptimization

```cpp
certigap::RebuildPolicy policy;
policy.minimum_new_operations = 10'000;
policy.minimum_tv_drift = 0.10;

if (index.maybe_reoptimize(policy)) {
    std::cout << "new backend=" << index.selected_name() << '\n';
}
```

Reoptimization is explicit rather than silently occurring inside a query.
This avoids unpredictable latency spikes. TV drift is measured over the
current range-coverage routing distribution relative to the profile at the
previous optimization.

This statement applies to the lower-level `Index`. `adaptive_array` offers an
opt-in automatic policy; disable `automatic_maintenance` to preserve explicit
maintenance boundaries.

## Snapshots

```cpp
auto snapshot = index.snapshot();
index.point_update(2, 100);

assert(snapshot.peek(2) != index.peek(2));
```

Adaptive snapshots are independent value-copies. They copy the active runtime,
canonical values, point/update counts, and `q` distinct range records, taking
`O(n+q)` logical space. This is semantic isolation, not the Python CertiRange
path-copy implementation.

## CMake FetchContent

```cmake
include(FetchContent)
FetchContent_Declare(
    certigap
    GIT_REPOSITORY https://github.com/nazkari86-lab/certigap-toolkit.git
    GIT_TAG v1.10.1
)
FetchContent_MakeAvailable(certigap)

add_executable(app main.cpp)
target_link_libraries(app PRIVATE CertiGap::certigap)
```

Installed packages support:

```cmake
find_package(CertiGap 1.7 REQUIRED)
target_link_libraries(app PRIVATE CertiGap::certigap)
```

## Which Mode To Use

- Use `certigap.hpp` for learning, online compilers, prototypes, and simple
  application integration.
- Use `certigap-compile` when selection must be reproduced, independently
  verified, embedded into generated C++, and separated from runtime latency.
- Use the Python research API for exact/anytime algorithms, certificates, and
  benchmark reproduction.

The adaptive runtime returns all five candidate reports and a deterministic
minimum under its declared model, but it does not export the independently
replayed omission-resistant certificate of `certigap-compile`.
