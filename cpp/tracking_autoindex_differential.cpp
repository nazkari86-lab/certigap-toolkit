#include "certigap_tracking.hpp"

#include <iomanip>
#include <iostream>


int main() {
    constexpr int n = 32;
    certigap::TrackingPolicyCpp policy;
    policy.migration_cost_units = 3.0;
    certigap::TrackingAutoIndexCpp index(
        std::vector<double>(n, 1.0), certigap::Aggregate::Sum, policy);
    const std::vector<certigap::TrackingOperation> operations = {
        certigap::TrackingOperation::get(7),
        certigap::TrackingOperation::range(1, 32),
        certigap::TrackingOperation::range(3, 27),
        certigap::TrackingOperation::update(5, 9.0),
        certigap::TrackingOperation::range(8, 8),
        certigap::TrackingOperation::update(32, -4.0),
    };
    index.run_batch(operations);
    std::cout << std::setprecision(17);
    for (std::size_t time = 0; time < operations.size(); ++time) {
        std::cout << time;
        for (double cost : index.history()[time].service_costs) {
            std::cout << ',' << cost;
        }
        std::cout << ',' << static_cast<int>(index.history()[time].selected)
                  << ',' << index.history()[time].cumulative_cost << '\n';
    }
}
