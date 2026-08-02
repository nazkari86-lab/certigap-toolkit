#include "certigap_tracking.hpp"

#include <chrono>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>


namespace {

using Clock = std::chrono::steady_clock;
volatile double sink = 0.0;

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

template <class Factory, class Execute>
void benchmark(
    int n,
    const std::string& workload_name,
    const std::vector<certigap::TrackingOperation>& operations,
    const std::string& implementation,
    Factory factory,
    Execute execute
) {
    std::vector<double> candidate_samples;
    std::vector<double> baseline_samples;
    std::vector<double> ratio_samples;
    double final_checksum = 0.0;
    double final_baseline_checksum = 0.0;
    for (int repeat = 0; repeat < 7; ++repeat) {
        auto run_candidate = [&] {
            auto index = factory();
            double checksum = 0.0;
            const auto start = Clock::now();
            for (const auto& operation : operations) {
                execute(index, operation, checksum);
            }
            const auto stop = Clock::now();
            final_checksum = checksum;
            sink += checksum;
            return std::chrono::duration<double, std::nano>(stop - start).count()
                / operations.size();
        };
        auto run_baseline = [&] {
            std::vector<double> values(n);
            std::iota(values.begin(), values.end(), 1.0);
            certigap::detail::FenwickRuntime index(values);
            double checksum = 0.0;
            const auto start = Clock::now();
            for (const auto& operation : operations) {
                if (operation.kind == certigap::TrackingOperationKind::Get) {
                    checksum += index.get(operation.left);
                } else if (
                    operation.kind == certigap::TrackingOperationKind::Range
                ) {
                    checksum += index.range_query(
                        operation.left, operation.right);
                } else {
                    index.point_update(operation.left, operation.value);
                }
            }
            const auto stop = Clock::now();
            final_baseline_checksum = checksum;
            sink += checksum;
            return std::chrono::duration<double, std::nano>(stop - start).count()
                / operations.size();
        };
        double candidate = 0.0;
        double baseline = 0.0;
        if (repeat % 2 == 0) {
            baseline = run_baseline();
            candidate = run_candidate();
        } else {
            candidate = run_candidate();
            baseline = run_baseline();
        }
        candidate_samples.push_back(candidate);
        baseline_samples.push_back(baseline);
        ratio_samples.push_back(candidate / baseline);
    }
    std::cout << n << ',' << workload_name << ',' << implementation << ','
              << operations.size() << ',' << std::setprecision(12)
              << median(candidate_samples) << ',' << median(baseline_samples)
              << ',' << median(ratio_samples) << ',' << final_checksum
              << ',' << final_baseline_checksum << '\n';
}

template <bool Checked>
void execute_frozen(
    certigap::FrozenTrackingIndex& index,
    const certigap::TrackingOperation& operation,
    double& checksum
) {
    if (operation.kind == certigap::TrackingOperationKind::Get) {
        checksum += Checked
            ? index.get(operation.left)
            : index.unchecked_get(operation.left);
    } else if (operation.kind == certigap::TrackingOperationKind::Range) {
        checksum += Checked
            ? index.range_query(operation.left, operation.right)
            : index.unchecked_range_query(operation.left, operation.right);
    } else if constexpr (Checked) {
        index.point_update(operation.left, operation.value);
    } else {
        index.unchecked_point_update(operation.left, operation.value);
    }
}

template <bool Checked>
void execute_fast(
    certigap::FastTrackingAutoIndex& index,
    const certigap::TrackingOperation& operation,
    double& checksum
) {
    if (operation.kind == certigap::TrackingOperationKind::Get) {
        checksum += Checked
            ? index.get(operation.left)
            : index.unchecked_get(operation.left);
    } else if (operation.kind == certigap::TrackingOperationKind::Range) {
        checksum += Checked
            ? index.range_query(operation.left, operation.right)
            : index.unchecked_range_query(operation.left, operation.right);
    } else if constexpr (Checked) {
        index.point_update(operation.left, operation.value);
    } else {
        index.unchecked_point_update(operation.left, operation.value);
    }
}

template <bool Checked>
void execute_static(
    certigap::StaticTrackingIndex<
        certigap::Backend::Fenwick, certigap::Aggregate::Sum>& index,
    const certigap::TrackingOperation& operation,
    double& checksum
) {
    if (operation.kind == certigap::TrackingOperationKind::Get) {
        checksum += Checked
            ? index.get(operation.left)
            : index.unchecked_get(operation.left);
    } else if (operation.kind == certigap::TrackingOperationKind::Range) {
        checksum += Checked
            ? index.range_query(operation.left, operation.right)
            : index.unchecked_range_query(operation.left, operation.right);
    } else if constexpr (Checked) {
        index.point_update(operation.left, operation.value);
    } else {
        index.unchecked_point_update(operation.left, operation.value);
    }
}

void execute_detached(
    certigap::FastTrackingAutoIndex& index,
    const certigap::TrackingOperation& operation,
    double& checksum
) {
    if (operation.kind == certigap::TrackingOperationKind::Get) {
        checksum += index.hot_get(operation.left);
    } else if (operation.kind == certigap::TrackingOperationKind::Range) {
        checksum += index.hot_range_query(operation.left, operation.right);
    } else {
        index.hot_point_update(operation.left, operation.value);
    }
}

}  // namespace

int main(int argc, char** argv) {
    const int count = argc > 1 ? std::stoi(argv[1]) : 5000;
    if (count <= 0) return 2;
    const std::vector<std::string> workloads = {
        "stable_points", "stable_ranges", "stable_updates",
        "range_to_update", "update_to_range", "alternating",
        "short_phases", "read_mostly",
    };
    std::cout << "n,workload,implementation,operations,ns_per_operation,"
                 "baseline_ns_per_operation,ratio_to_direct,checksum,"
                 "baseline_checksum\n";
    for (int n : {16, 64, 256, 4096}) {
        std::vector<double> values(n);
        std::iota(values.begin(), values.end(), 1.0);
        for (const auto& name : workloads) {
            const auto operations = workload(n, count, name);
            benchmark(
                n, name, operations, "frozen_fenwick_checked",
                [&] {
                    return certigap::FrozenTrackingIndex(
                        values, certigap::Aggregate::Sum,
                        certigap::Backend::Fenwick);
                }, execute_frozen<true>
            );
            benchmark(
                n, name, operations, "frozen_fenwick_unchecked",
                [&] {
                    return certigap::FrozenTrackingIndex(
                        values, certigap::Aggregate::Sum,
                        certigap::Backend::Fenwick);
                }, execute_frozen<false>
            );
            benchmark(
                n, name, operations, "static_fenwick_checked",
                [&] {
                    return certigap::StaticTrackingIndex<
                        certigap::Backend::Fenwick,
                        certigap::Aggregate::Sum>(values);
                }, execute_static<true>
            );
            benchmark(
                n, name, operations, "static_fenwick_unchecked",
                [&] {
                    return certigap::StaticTrackingIndex<
                        certigap::Backend::Fenwick,
                        certigap::Aggregate::Sum>(values);
                }, execute_static<false>
            );
            benchmark(
                n, name, operations, "fast_checked",
                [&] { return certigap::FastTrackingAutoIndex(values); },
                execute_fast<true>
            );
            benchmark(
                n, name, operations, "fast_unchecked",
                [&] { return certigap::FastTrackingAutoIndex(values); },
                execute_fast<false>
            );
            benchmark(
                n, name, operations, "fast_detached_data_plane",
                [&] { return certigap::FastTrackingAutoIndex(values); },
                execute_detached
            );
        }
    }
    return sink == -1.0 ? 1 : 0;
}
