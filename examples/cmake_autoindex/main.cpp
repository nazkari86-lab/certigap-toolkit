#include <cmath>
#include <iostream>
#include <vector>

#include "generated_index.hpp"


int main() {
    std::vector<double> values(16);
    for (int index = 0; index < 16; ++index) {
        values[index] = static_cast<double>(index);
    }

    certigap_generated::Index index(values);
    auto snapshot = index.snapshot();
    index.point_update(2, 100.0);

    if (std::abs(snapshot.get(2) - 1.0) > 1e-12) return 2;
    if (std::abs(index.get(2) - 100.0) > 1e-12) return 3;
    if (std::abs(index.range_query(1, 3) - 102.0) > 1e-12) return 4;

    std::cout << certigap_generated::kSelectedName << '\n';
    std::cout << index.artifact_sha256() << '\n';
    return 0;
}
