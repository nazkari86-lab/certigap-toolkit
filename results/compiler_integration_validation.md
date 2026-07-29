# Compiler integration validation

- Deterministic generated headers: `24/24`.
- Independently verified source artifacts: `24/24`.
- Candidate count per artifact: `5`.
- Selected backend distribution: `{'certirange_range': 5, 'fenwick': 4, 'segment_tree': 3, 'sorted_array': 12}`.
- Cross-language executable coverage is enforced by `tests/test_compiler_integration.py`.
- The CMake example compiles a generated CertiRange topology and checks snapshot isolation.

Header hashes cover exact generated C++ source. They certify deterministic code generation from a verified artifact, not compiler binary equivalence across toolchains.
