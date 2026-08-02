#include "certigap_concurrent.hpp"

#include <atomic>
#include <cassert>
#include <cmath>
#include <iostream>
#include <numeric>
#include <thread>
#include <unordered_set>


namespace {

void verify_snapshot_lifecycle() {
    std::vector<double> values(1024);
    std::iota(values.begin(), values.end(), 1.0);
    certigap::ConcurrentPrefixPolicy policy;
    policy.recommendation_range_queries = 4;
    certigap::ConcurrentPrefixIndex index(values, policy);
    const double expected = 1024.0 * 1025.0 / 2.0;
    for (int repeat = 0; repeat < 4; ++repeat) {
        assert(index.range_query(1, 1024) == expected);
    }
    assert(index.rebuild_recommended());
    assert(index.rebuild_now());
    assert(index.snapshot_active());
    auto explanation = index.explain();
    assert(explanation.snapshot_version == explanation.version);
    assert(explanation.rebuilds_published == 1);
    assert(index.range_query(100, 900)
        == (100.0 + 900.0) * 801.0 / 2.0);

    {
        auto view = index.snapshot_view();
        assert(view.active());
        assert(view.version() == 0);
        index.point_update(10, 10000.0);
        assert(!index.snapshot_active());
        assert(index.get(10) == 10000.0);
        assert(index.range_query(1, 1024) == expected - 10.0 + 10000.0);
        assert(view.range_query(1, 1024) == expected);
        assert(!index.request_rebuild());
    }
    explanation = index.explain();
    assert(explanation.version == 1);
    assert(explanation.invalidations == 1);
    assert(index.rebuild_now());
    assert(index.explain().snapshot_version == 1);
}

void verify_concurrent_readers_and_catchup() {
    constexpr int n = 200000;
    std::vector<double> expected(n, 1.0);
    std::unordered_set<double> valid_sums;
    double running_sum = static_cast<double>(n);
    valid_sums.insert(running_sum);
    for (int operation = 0; operation < 4000; ++operation) {
        const double value = static_cast<double>((operation % 211) - 100);
        running_sum += value - 1.0;
        valid_sums.insert(running_sum);
    }
    certigap::ConcurrentPrefixPolicy policy;
    policy.max_update_log_entries = 16384;
    policy.max_catchup_rounds = 64;
    certigap::ConcurrentPrefixIndex index(expected, policy);
    assert(index.request_rebuild());

    std::atomic<bool> stop{false};
    std::atomic<std::uint64_t> reads{0};
    std::vector<std::thread> readers;
    for (int reader = 0; reader < 4; ++reader) {
        readers.emplace_back([&] {
            while (!stop.load(std::memory_order_acquire)) {
                const double value = index.range_query(1, n);
                assert(std::isfinite(value));
                assert(valid_sums.count(value) == 1);
                reads.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    for (int operation = 0; operation < 4000; ++operation) {
        const int key = 1 + (operation * 97) % n;
        const double value = static_cast<double>((operation % 211) - 100);
        index.point_update(key, value);
        expected[key - 1] = value;
    }
    stop.store(true, std::memory_order_release);
    for (auto& reader : readers) reader.join();
    index.wait_for_rebuild();
    assert(reads.load(std::memory_order_relaxed) > 0);

    const double expected_sum = std::accumulate(
        expected.begin(), expected.end(), 0.0);
    assert(index.range_query(1, n) == expected_sum);
    if (!index.snapshot_active()) assert(index.rebuild_now());
    assert(index.snapshot_active());
    assert(index.range_query(1, n) == expected_sum);
    const auto explanation = index.explain();
    assert(explanation.snapshot_version == explanation.version);
    assert(explanation.rebuilds_started >= 1);
    assert(explanation.rebuilds_published >= 1);
}

void verify_limits_and_fail_closed_inputs() {
    certigap::ConcurrentPrefixPolicy policy;
    policy.max_snapshot_bytes = 1;
    certigap::ConcurrentPrefixIndex limited(
        std::vector<double>(128, 1.0), policy);
    assert(!limited.request_rebuild());
    assert(limited.explain().budget_rejections == 1);

    bool rejected = false;
    try {
        certigap::ConcurrentPrefixPolicy invalid;
        invalid.max_update_log_entries = 0;
        certigap::ConcurrentPrefixIndex index(
            std::vector<double>(8, 1.0), invalid);
    } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected);

    rejected = false;
    try {
        certigap::ConcurrentPrefixIndex index({1.0, 2.0});
        index.range_query(0, 2);
    } catch (const std::out_of_range&) { rejected = true; }
    assert(rejected);
}

}  // namespace

int main() {
    verify_snapshot_lifecycle();
    verify_concurrent_readers_and_catchup();
    verify_limits_and_fail_closed_inputs();
    std::cout << "concurrent_tracking_validation,passed,4000_updates,4_readers\n";
}
