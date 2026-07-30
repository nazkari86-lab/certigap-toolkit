# Compiler And CMake Integration

CertiGap uses a profile-guided build step. It is not a GCC or Clang plugin:
the compiler consumes an operation trace before the C++ build, verifies all
five portfolio candidates, and emits a normal C++17 configuration header.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install certigap_toolkit-1.9.0-py3-none-any.whl

certigap-compile include-dir
```

The last command prints the directory containing
`certigap_autoindex.hpp`.

For a simpler no-Python runtime mode, the same directory also contains the
standalone [`certigap.hpp`](ADAPTIVE_CPP.md).

## Input

The strict schema is
[`schemas/certigap_compile_input_v1.schema.json`](../schemas/certigap_compile_input_v1.schema.json).
Keys are 1-based ranks in a fixed ordered universe.

```json
{
  "schema": "certigap-compile-input-v1",
  "values": [0, 1, 2, 3],
  "train_trace": {
    "n": 4,
    "operations": [
      {"kind": "range", "left": 1, "right": 3},
      {"kind": "get", "left": 1},
      {"kind": "update", "left": 2, "value": 10}
    ]
  },
  "holdout_trace": {
    "n": 4,
    "operations": [{"kind": "range", "left": 2, "right": 4}]
  },
  "constraints": {
    "aggregate": "sum",
    "budget": 3,
    "memory_limit_slots": 64
  }
}
```

`right` defaults to `left`; `value` defaults to zero. Unknown fields, invalid
ranges, non-finite values, unsupported constraints, and conflicting output
paths fail closed.

## Compile And Verify

```bash
certigap-compile compile trace.json \
  --artifact build/selection.json \
  --header build/generated_index.hpp \
  --namespace my_project::generated

certigap-compile verify build/selection.json
```

The generated header embeds:

- selected backend and aggregate;
- key-universe size;
- verified artifact SHA-256;
- exact completed topology for a selected CertiRange backend;
- verified training score.

The verifier is run before code generation. Repeating compilation with the
same input and namespace produces byte-identical header text.

## C++ Usage

```cpp
#include "generated_index.hpp"

std::vector<double> values = load_values();
my_project::generated::Index index(values);

double item = index.get(1);
double total = index.range_query(1, 10);
index.point_update(2, 100.0);

auto old_view = index.snapshot();
```

The reusable header supports array, Fenwick, segment tree, and both CertiRange
variants. Selection is compile-time through `if constexpr`; no runtime
portfolio dispatch remains. `sum`, `min`, and `max` are supported, while
Fenwick is statically restricted to `sum`.

C++ `snapshot()` currently returns an independent value-copy in `O(n)` space
and time. It preserves old values correctly but does not claim the Python
CertiRange runtime's `O(h)` path-copy efficiency.

## CMake

The complete source-checkout example is in
[`examples/cmake_autoindex`](../examples/cmake_autoindex).

```bash
cmake -S examples/cmake_autoindex -B build/cmake-autoindex
cmake --build build/cmake-autoindex
build/cmake-autoindex/certigap_autoindex_example
```

For an installed package, obtain the include path during configuration:

```cmake
execute_process(
    COMMAND certigap-compile include-dir
    OUTPUT_VARIABLE CERTIGAP_INCLUDE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)

add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/generated_index.hpp"
           "${CMAKE_CURRENT_BINARY_DIR}/selection.json"
    COMMAND certigap-compile compile "${CMAKE_SOURCE_DIR}/trace.json"
            --artifact "${CMAKE_CURRENT_BINARY_DIR}/selection.json"
            --header "${CMAKE_CURRENT_BINARY_DIR}/generated_index.hpp"
    DEPENDS "${CMAKE_SOURCE_DIR}/trace.json"
    VERBATIM
)

target_include_directories(
    app PRIVATE
    "${CMAKE_CURRENT_BINARY_DIR}"
    "${CERTIGAP_INCLUDE_DIR}"
)
```

## Claim Boundary

The artifact certifies selection over the declared fixed portfolio and
analytical/calibrated work model. The generated header preserves that selected
configuration. It does not prove that GCC and Clang emit identical machine
code, nor that analytical work units equal production latency. Backend unit
costs should be calibrated on the target system when latency matters.
