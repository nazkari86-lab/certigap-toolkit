#include "certigap_concurrent.hpp"

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <optional>
#include <string>
#include <thread>


namespace {

using Clock = std::chrono::steady_clock;
volatile double sink = 0.0;
bool measured_atomics_lock_free = false;

struct Query {
    int left = 1;
    int right = 1;
};

struct SnapshotSessionIndex {
    explicit SnapshotSessionIndex(const std::vector<double>& values)
        : index(std::make_unique<certigap::ConcurrentPrefixIndex>(values)) {
        if (!index->rebuild_now()) std::abort();
        view.emplace(index->snapshot_view());
    }

    std::unique_ptr<certigap::ConcurrentPrefixIndex> index;
    std::optional<certigap::ConcurrentPrefixIndex::SnapshotReadView> view;
};

std::vector<Query> queries(int n, int count, const std::string& scenario) {
    std::vector<Query> result;
    result.reserve(count);
    for (int operation = 0; operation < count; ++operation) {
        if (scenario == "points") {
            const int key = 1 + (operation * 17) % n;
            result.push_back({key, key});
        } else {
            const int left = 1 + (operation * 7) % std::max(1, n / 4);
            result.push_back({left, n});
        }
    }
    return result;
}

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
}

template <class Index, class Execute>
std::pair<double, double> run_single(
    Index& index, const std::vector<Query>& stream, Execute execute
) {
    double checksum = 0.0;
    const auto start = Clock::now();
    for (const auto& query : stream) checksum += execute(index, query);
    const auto stop = Clock::now();
    sink += checksum;
    return {
        std::chrono::duration<double, std::nano>(stop - start).count()
            / stream.size(),
        checksum,
    };
}

template <class Factory, class Execute>
void benchmark(
    int n,
    const std::string& scenario,
    const std::string& implementation,
    int threads,
    const std::vector<Query>& stream,
    Factory factory,
    Execute execute
) {
    std::vector<double> samples;
    double final_checksum = 0.0;
    for (int repeat = 0; repeat < 5; ++repeat) {
        auto index = factory();
        if (threads == 1) {
            const auto [elapsed, checksum] = run_single(index, stream, execute);
            samples.push_back(elapsed);
            final_checksum = checksum;
            continue;
        }
        std::atomic<int> ready{0};
        std::atomic<bool> start{false};
        std::vector<double> checksums(threads, 0.0);
        std::vector<std::thread> readers;
        readers.reserve(threads);
        for (int thread = 0; thread < threads; ++thread) {
            readers.emplace_back([&, thread] {
                ready.fetch_add(1, std::memory_order_release);
                while (!start.load(std::memory_order_acquire)) {}
                double checksum = 0.0;
                for (
                    std::size_t offset = thread;
                    offset < stream.size();
                    offset += threads
                ) checksum += execute(index, stream[offset]);
                checksums[thread] = checksum;
            });
        }
        while (ready.load(std::memory_order_acquire) != threads) {}
        const auto begin = Clock::now();
        start.store(true, std::memory_order_release);
        for (auto& reader : readers) reader.join();
        const auto end = Clock::now();
        final_checksum = std::accumulate(
            checksums.begin(), checksums.end(), 0.0);
        sink += final_checksum;
        samples.push_back(
            std::chrono::duration<double, std::nano>(end - begin).count()
            / stream.size());
    }
    std::cout << n << ',' << scenario << ',' << implementation << ','
              << threads << ',' << stream.size() << ','
              << std::setprecision(12) << median(samples) << ','
              << final_checksum << ','
              << (measured_atomics_lock_free ? "true" : "false") << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    const int count = argc > 1 ? std::stoi(argv[1]) : 50000;
    if (count <= 0) return 2;
    certigap::ConcurrentPrefixIndex atomic_probe({1.0});
    measured_atomics_lock_free = atomic_probe.snapshot_atomics_lock_free();
    std::cout << "n,scenario,implementation,threads,operations,"
                 "ns_per_operation,checksum,atomics_lock_free\n";
    for (int n : {4096, 65536}) {
        std::vector<double> values(n);
        std::iota(values.begin(), values.end(), 1.0);
        for (const std::string scenario : {"points", "ranges"}) {
            const auto stream = queries(n, count, scenario);
            for (int threads : {1, 4}) {
                benchmark(
                    n, scenario, "direct_fenwick", threads, stream,
                    [&] { return certigap::detail::FenwickRuntime(values); },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index.get(query.left)
                            : index.range_query(query.left, query.right);
                    }
                );
                benchmark(
                    n, scenario, "direct_prefix", threads, stream,
                    [&] { return certigap::detail::PrefixRuntime(values); },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index.get(query.left)
                            : index.range_query(query.left, query.right);
                    }
                );
                benchmark(
                    n, scenario, "concurrent_fallback", threads, stream,
                    [&] { return std::make_unique<certigap::ConcurrentPrefixIndex>(
                        values); },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index->get(query.left)
                            : index->range_query(query.left, query.right);
                    }
                );
                benchmark(
                    n, scenario, "concurrent_snapshot", threads, stream,
                    [&] {
                        auto index = std::make_unique<
                            certigap::ConcurrentPrefixIndex>(values);
                        if (!index->rebuild_now()) std::abort();
                        return index;
                    },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index->get(query.left)
                            : index->range_query(query.left, query.right);
                    }
                );
                benchmark(
                    n, scenario, "concurrent_snapshot_session", threads, stream,
                    [&] { return SnapshotSessionIndex(values); },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index.view->get(query.left)
                            : index.view->range_query(query.left, query.right);
                    }
                );
                benchmark(
                    n, scenario, "concurrent_snapshot_session_unchecked",
                    threads, stream,
                    [&] { return SnapshotSessionIndex(values); },
                    [&](const auto& index, const Query& query) {
                        return scenario == "points"
                            ? index.view->unchecked_get(query.left)
                            : index.view->unchecked_range_query(
                                query.left, query.right);
                    }
                );
            }
        }
    }
    return sink == -1.0 ? 1 : 0;
}
