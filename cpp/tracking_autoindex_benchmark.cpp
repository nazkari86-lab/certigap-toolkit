#include "certigap_tracking.hpp"

#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>


namespace {

using Clock = std::chrono::steady_clock;
using Runtime = std::variant<
    certigap::detail::ArrayRuntime,
    certigap::detail::PrefixRuntime,
    certigap::detail::FenwickRuntime,
    certigap::detail::SqrtRuntime,
    certigap::detail::SegmentRuntime
>;

volatile double sink = 0.0;

Runtime make_runtime(certigap::Backend backend, const std::vector<double>& values) {
    Runtime runtime(std::in_place_type<certigap::detail::ArrayRuntime>,
                    values, certigap::Aggregate::Sum);
    if (backend == certigap::Backend::PrefixSum) {
        runtime.emplace<certigap::detail::PrefixRuntime>(values);
    } else if (backend == certigap::Backend::Fenwick) {
        runtime.emplace<certigap::detail::FenwickRuntime>(values);
    } else if (backend == certigap::Backend::SqrtDecomposition) {
        runtime.emplace<certigap::detail::SqrtRuntime>(
            values, certigap::Aggregate::Sum);
    } else if (backend == certigap::Backend::SegmentTree) {
        runtime.emplace<certigap::detail::SegmentRuntime>(
            values, certigap::Aggregate::Sum);
    }
    return runtime;
}

std::vector<certigap::TrackingOperation> workload(
    int n, int count, const std::string& name
) {
    std::vector<certigap::TrackingOperation> result;
    result.reserve(count);
    for (int index = 0; index < count; ++index) {
        const int key = 1 + (index * 17) % n;
        if (name == "stable_points") {
            result.push_back(certigap::TrackingOperation::get(key));
            continue;
        }
        if (name == "stable_updates") {
            result.push_back(certigap::TrackingOperation::update(
                key, static_cast<double>((index % 101) - 50)));
            continue;
        }
        bool range = false;
        if (name == "stable_ranges") range = true;
        else if (name == "range_to_update") range = index < count / 2;
        else if (name == "update_to_range") range = index >= count / 2;
        else if (name == "alternating") range = index % 2 == 0;
        else if (name == "short_phases") range = (index / 64) % 2 == 0;
        else range = index % 10 < 7;
        if (range) {
            const int left = 1 + (index * 7) % std::max(1, n / 4);
            result.push_back(certigap::TrackingOperation::range(left, n));
        } else if (name == "read_mostly" && index % 10 >= 7 && index % 2) {
            result.push_back(certigap::TrackingOperation::get(key));
        } else {
            result.push_back(certigap::TrackingOperation::update(
                key, static_cast<double>((index % 101) - 50)));
        }
    }
    return result;
}

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
}

void benchmark_fixed(
    int n,
    const std::string& workload_name,
    const std::vector<certigap::TrackingOperation>& operations,
    certigap::Backend backend
) {
    std::vector<double> samples;
    double final_checksum = 0.0;
    for (int repeat = 0; repeat < 5; ++repeat) {
        std::vector<double> values(n);
        std::iota(values.begin(), values.end(), 1.0);
        Runtime runtime = make_runtime(backend, values);
        double checksum = 0.0;
        const auto start = Clock::now();
        for (const auto& operation : operations) {
            if (operation.kind == certigap::TrackingOperationKind::Get) {
                checksum += std::visit([&](const auto& item) {
                    return item.get(operation.left);
                }, runtime);
            } else if (operation.kind == certigap::TrackingOperationKind::Range) {
                checksum += std::visit([&](const auto& item) {
                    return item.range_query(operation.left, operation.right);
                }, runtime);
            } else {
                std::visit([&](auto& item) {
                    item.point_update(operation.left, operation.value);
                }, runtime);
            }
        }
        const auto stop = Clock::now();
        samples.push_back(std::chrono::duration<double, std::nano>(stop - start).count()
                          / operations.size());
        final_checksum = checksum;
        sink += checksum;
    }
    std::cout << n << ',' << workload_name << ',' << certigap::backend_name(backend)
              << ',' << operations.size()
              << ',' << std::setprecision(12) << median(samples)
              << ",0," << final_checksum << '\n';
}

void benchmark_tracking(
    int n,
    const std::string& workload_name,
    const std::vector<certigap::TrackingOperation>& operations,
    bool record_history,
    bool rebuild_metric
) {
    std::vector<double> samples;
    std::size_t switches = 0;
    double final_checksum = 0.0;
    for (int repeat = 0; repeat < 5; ++repeat) {
        std::vector<double> values(n);
        std::iota(values.begin(), values.end(), 1.0);
        certigap::TrackingPolicyCpp policy;
        policy.migration_cost_units = 8.0;
        policy.record_history = record_history;
        if (rebuild_metric) {
            policy.backends = {
                certigap::Backend::SortedArray,
                certigap::Backend::PrefixSum,
                certigap::Backend::Fenwick,
                certigap::Backend::SqrtDecomposition,
                certigap::Backend::SegmentTree,
            };
            policy.migration_matrix = certigap::tracking_rebuild_metric(
                values.size(), policy.backends);
        }
        certigap::TrackingAutoIndexCpp index(
            values, certigap::Aggregate::Sum, policy);
        double checksum = 0.0;
        const auto start = Clock::now();
        const auto results = index.run_batch(operations);
        const auto stop = Clock::now();
        for (const auto& result : results) {
            if (result) checksum += *result;
        }
        samples.push_back(std::chrono::duration<double, std::nano>(stop - start).count()
                          / operations.size());
        switches = index.switch_count();
        final_checksum = checksum;
        sink += checksum;
    }
    std::cout << n << ',' << workload_name << ','
              << "tracking_native_"
              << (rebuild_metric ? "rebuild_metric_" : "uniform_")
              << (record_history ? "audit" : "production")
              << ',' << operations.size()
              << ',' << std::setprecision(12) << median(samples)
              << ',' << switches << ',' << final_checksum << '\n';
}

void benchmark_fast(
    int n,
    const std::string& workload_name,
    const std::vector<certigap::TrackingOperation>& operations
) {
    std::vector<double> samples;
    std::size_t switches = 0;
    double final_checksum = 0.0;
    for (int repeat = 0; repeat < 5; ++repeat) {
        std::vector<double> values(n);
        std::iota(values.begin(), values.end(), 1.0);
        certigap::FastTrackingAutoIndex index(values);
        double checksum = 0.0;
        const auto start = Clock::now();
        for (const auto& operation : operations) {
            if (operation.kind == certigap::TrackingOperationKind::Get) {
                checksum += index.get(operation.left);
            } else if (operation.kind == certigap::TrackingOperationKind::Range) {
                checksum += index.range_query(operation.left, operation.right);
            } else {
                index.point_update(operation.left, operation.value);
            }
        }
        index.flush();
        const auto stop = Clock::now();
        samples.push_back(
            std::chrono::duration<double, std::nano>(stop - start).count()
                / operations.size()
        );
        switches = index.switch_count();
        final_checksum = checksum;
        sink += checksum;
    }
    std::cout << n << ',' << workload_name
              << ",tracking_native_fast_sampled," << operations.size()
              << ',' << std::setprecision(12) << median(samples)
              << ',' << switches << ',' << final_checksum << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    const int count = argc > 1 ? std::stoi(argv[1]) : 50000;
    std::cout << "n,workload,implementation,operations,ns_per_operation,switches,checksum\n";
    const std::vector<certigap::Backend> backends = {
        certigap::Backend::SortedArray,
        certigap::Backend::PrefixSum,
        certigap::Backend::Fenwick,
        certigap::Backend::SqrtDecomposition,
        certigap::Backend::SegmentTree,
    };
    for (int n : {16, 64, 256, 4096}) {
        for (const std::string name : {
            "stable_points", "stable_ranges", "stable_updates",
            "range_to_update", "update_to_range", "alternating",
            "short_phases", "read_mostly"
        }) {
            const auto operations = workload(n, count, name);
            for (auto backend : backends) {
                benchmark_fixed(n, name, operations, backend);
            }
            benchmark_tracking(n, name, operations, false, false);
            benchmark_tracking(n, name, operations, false, true);
            benchmark_tracking(n, name, operations, true, true);
            benchmark_fast(n, name, operations);
        }
    }
    return sink == std::numeric_limits<double>::infinity();
}
