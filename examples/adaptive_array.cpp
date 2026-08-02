#include <iostream>
#include <vector>

#include "certigap.hpp"


int main(int argc, char** argv) {
    std::vector<double> values(128);
    for (int index = 0; index < 128; ++index) {
        values[index] = static_cast<double>(index);
    }

    certigap::AutoTunePolicy policy;
    policy.warmup_operations = 64;
    policy.check_interval = 256;
    policy.minimum_relative_improvement = 0.05;
    if (argc == 2) policy.profile_path = argv[1];

    certigap::adaptive_array<double> data(values, policy);
    for (int repetition = 0; repetition < 64; ++repetition) {
        data.range_sum(8, 96);
    }

    std::cout << data.explain() << '\n';
    std::cout << "range_sum=" << data.range_sum(8, 96) << '\n';
    return 0;
}
