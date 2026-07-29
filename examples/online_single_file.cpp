#include <iostream>
#include <vector>

#include "certigap.hpp"


int main() {
    std::vector<double> values(32);
    for (int index = 0; index < 32; ++index) {
        values[index] = static_cast<double>(index);
    }

    certigap::Index index(values);

    // Real calls are profiled automatically. Explicit observations let an
    // application warm the profile without executing the operations.
    for (int repetition = 0; repetition < 100; ++repetition) {
        index.observe_range(3, 30);
    }

    index.optimize();
    std::cout << "selected=" << index.selected_name() << '\n';
    std::cout << "sum=" << index.range_query(3, 30) << '\n';

    auto snapshot = index.snapshot();
    index.point_update(2, 100.0);
    std::cout << "old=" << snapshot.get(2)
              << " current=" << index.get(2) << '\n';
}
