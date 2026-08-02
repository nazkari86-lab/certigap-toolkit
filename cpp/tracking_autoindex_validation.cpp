#include "certigap_tracking.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include <random>


namespace {

double aggregate_range(
    const std::vector<double>& values,
    int left,
    int right,
    certigap::Aggregate aggregate
) {
    double result = aggregate == certigap::Aggregate::Sum
        ? 0.0
        : (aggregate == certigap::Aggregate::Min
            ? std::numeric_limits<double>::infinity()
            : -std::numeric_limits<double>::infinity());
    for (int key = left; key <= right; ++key) {
        if (aggregate == certigap::Aggregate::Sum) result += values[key - 1];
        else if (aggregate == certigap::Aggregate::Min) {
            result = std::min(result, values[key - 1]);
        } else result = std::max(result, values[key - 1]);
    }
    return result;
}

void randomized_correctness(certigap::Aggregate aggregate, int seed) {
    std::mt19937 generator(seed);
    std::uniform_int_distribution<int> value_distribution(-100, 100);
    constexpr int n = 37;
    std::vector<double> values(n);
    for (double& value : values) value = value_distribution(generator);
    certigap::TrackingPolicyCpp policy;
    policy.migration_cost_units = 0.5 + seed % 5;
    certigap::TrackingAutoIndexCpp index(values, aggregate, policy);
    for (int operation = 0; operation < 1000; ++operation) {
        const int kind = static_cast<int>(generator() % 3);
        const int left = 1 + static_cast<int>(generator() % n);
        if (kind == 0) {
            assert(index.get(left) == values[left - 1]);
        } else if (kind == 1) {
            const int right = left + static_cast<int>(generator() % (n - left + 1));
            assert(index.range_query(left, right)
                == aggregate_range(values, left, right, aggregate));
        } else {
            const double value = value_distribution(generator);
            index.point_update(left, value);
            values[left - 1] = value;
        }
    }
    assert(index.history().size() == 1000);
    assert(index.comparator_oracle().path.size() == 1000);
    assert(index.migration_is_metric());
    assert(index.wfa_competitive_factor()
        == 2 * static_cast<int>(index.candidates().size()) - 1);
}

void verify_structural_costs() {
    certigap::TrackingPolicyCpp policy;
    policy.migration_cost_units = 1000.0;
    certigap::TrackingAutoIndexCpp index(
        std::vector<double>(16, 1.0), certigap::Aggregate::Sum, policy);
    index.range_query(3, 14);
    const auto& costs = index.history().back().service_costs;
    // Candidate order: array, prefix, Fenwick, sqrt, segment.
    assert((costs == std::vector<double>{12.0, 2.0, 4.0, 6.0, 4.0}));
    index.point_update(5, 3.0);
    const auto& update = index.history().back().service_costs;
    assert((update == std::vector<double>{1.0, 13.0, 4.0, 5.0, 5.0}));
}

void verify_oracle_against_enumeration() {
    certigap::TrackingPolicyCpp policy;
    policy.migration_cost_units = 2.0;
    policy.backends = {
        certigap::Backend::SortedArray,
        certigap::Backend::PrefixSum,
        certigap::Backend::Fenwick,
    };
    certigap::TrackingAutoIndexCpp index(
        std::vector<double>(8, 1.0), certigap::Aggregate::Sum, policy);
    index.range_query(1, 8);
    index.point_update(3, 4.0);
    index.get(3);
    const auto oracle = index.exact_oracle(1);
    double best = std::numeric_limits<double>::infinity();
    std::vector<certigap::Backend> path(3);
    for (int a = 0; a < 3; ++a) for (int b = 0; b < 3; ++b) {
        for (int c = 0; c < 3; ++c) {
            const int choices[] = {a, b, c};
            int prior = 0;
            int switches = 0;
            double cost = 0.0;
            for (int time = 0; time < 3; ++time) {
                if (choices[time] != prior) { ++switches; cost += 2.0; }
                cost += index.history()[time].service_costs[choices[time]];
                prior = choices[time];
            }
            if (switches <= 1) best = std::min(best, cost);
        }
    }
    assert(std::abs(oracle.cost - best) <= 1e-12);
}

void verify_matrix_boundary_and_batch() {
    certigap::TrackingPolicyCpp policy;
    policy.backends = {
        certigap::Backend::SortedArray,
        certigap::Backend::PrefixSum,
        certigap::Backend::Fenwick,
    };
    policy.migration_matrix = {
        {0.0, 1.0, 2.0},
        {4.0, 0.0, 1.0},
        {2.0, 1.0, 0.0},
    };
    certigap::TrackingAutoIndexCpp directed(
        std::vector<double>(8, 1.0), certigap::Aggregate::Sum, policy);
    assert(!directed.migration_is_metric());
    assert(directed.wfa_competitive_factor() == 0);
    const auto results = directed.run_batch({
        certigap::TrackingOperation::range(1, 8),
        certigap::TrackingOperation::update(1, 9.0),
        certigap::TrackingOperation::get(1),
    });
    assert(results[0] == 8.0);
    assert(!results[1].has_value());
    assert(results[2] == 9.0);

    const auto metric = certigap::tracking_rebuild_metric(8, policy.backends);
    policy.migration_matrix = metric;
    certigap::TrackingAutoIndexCpp rebuild_aware(
        std::vector<double>(8, 1.0), certigap::Aggregate::Sum, policy);
    assert(rebuild_aware.migration_is_metric());
    assert(rebuild_aware.wfa_competitive_factor() == 5);
}

void verify_fail_closed_inputs() {
    bool rejected = false;
    try {
        certigap::TrackingPolicyCpp policy;
        policy.migration_matrix = {{0.0}};
        certigap::TrackingAutoIndexCpp invalid(
            std::vector<double>(8, 1.0), certigap::Aggregate::Sum, policy);
    } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected);
    rejected = false;
    try {
        certigap::TrackingAutoIndexCpp invalid(
            {1.0, std::numeric_limits<double>::quiet_NaN()});
    } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected);
}

}  // namespace

int main() {
    verify_structural_costs();
    verify_oracle_against_enumeration();
    verify_matrix_boundary_and_batch();
    verify_fail_closed_inputs();
    for (int seed = 1; seed <= 8; ++seed) {
        randomized_correctness(certigap::Aggregate::Sum, 1000 + seed);
        randomized_correctness(certigap::Aggregate::Min, 2000 + seed);
        randomized_correctness(certigap::Aggregate::Max, 3000 + seed);
    }
    std::cout << "native_tracking_validation,passed,24000_random_operations\n";
}
