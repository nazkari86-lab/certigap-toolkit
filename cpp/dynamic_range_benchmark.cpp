#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

#include "certigap_core.cpp"
#include "certigap_range.hpp"


struct Operation {
    int type = 0;  // 0=get, 1=range, 2=update
    int left = 0;
    int right = 0;
    double value = 0.0;
};

static uint64_t next_u64(uint64_t& state) {
    state ^= state << 7;
    state ^= state >> 9;
    return state;
}

static int random_int(uint64_t& state, int left, int right) {
    return left + static_cast<int>(next_u64(state) % static_cast<uint64_t>(right - left + 1));
}

static double random_unit(uint64_t& state) {
    return static_cast<double>(next_u64(state) >> 11) * (1.0 / 9007199254740992.0);
}

static std::vector<Operation> make_trace(int n, int count, const std::string& workload) {
    uint64_t state = 20260730 + static_cast<uint64_t>(n) * 17 + workload.size();
    int hot_width = std::max(2, n / 10);
    std::vector<Operation> out;
    out.reserve(count);
    for (int step = 0; step < count; ++step) {
        double draw = random_unit(state);
        if (workload == "uniform_mixed") {
            if (draw < 0.20) {
                int key = random_int(state, 1, n);
                out.push_back({2, key, key, static_cast<double>((step * 17) % 101)});
            } else if (draw < 0.45) {
                int key = random_int(state, 1, n);
                out.push_back({0, key, key, 0.0});
            } else {
                int left = random_int(state, 1, n);
                int right = random_int(state, left, std::min(n, left + random_int(state, 0, std::max(1, n / 4))));
                out.push_back({1, left, right, 0.0});
            }
        } else if (workload == "hotspot_point") {
            if (draw < 0.10) {
                int key = random_int(state, 1, n);
                out.push_back({2, key, key, static_cast<double>((step * 19) % 97)});
            } else if (draw < 0.85) {
                int key = random_unit(state) < 0.90 ? random_int(state, 1, hot_width) : random_int(state, 1, n);
                out.push_back({0, key, key, 0.0});
            } else {
                int left = random_int(state, 1, hot_width);
                int right = random_int(state, left, std::min(n, left + hot_width));
                out.push_back({1, left, right, 0.0});
            }
        } else {
            int center = n / 2;
            if (draw < 0.15) {
                int key = random_int(state, std::max(1, center - hot_width), std::min(n, center + hot_width));
                out.push_back({2, key, key, static_cast<double>((step * 23) % 89)});
            } else if (draw < 0.25) {
                int key = random_int(state, 1, n);
                out.push_back({0, key, key, 0.0});
            } else {
                int left = random_int(state, std::max(1, center - 2 * hot_width), std::min(n, center + hot_width));
                int right = random_int(state, left, std::min(n, left + 2 * hot_width));
                out.push_back({1, left, right, 0.0});
            }
        }
    }
    return out;
}

class ArrayIndex {
public:
    explicit ArrayIndex(std::vector<double> values) : values_(std::move(values)) {}
    double get(int key) const { return values_[key - 1]; }
    double range_sum(int left, int right) const {
        return std::accumulate(values_.begin() + left - 1, values_.begin() + right, 0.0);
    }
    void point_update(int key, double value) { values_[key - 1] = value; }
private:
    std::vector<double> values_;
};

class FenwickIndex {
public:
    explicit FenwickIndex(const std::vector<double>& values) : values_(values), tree_(values.size() + 1, 0.0) {
        for (int key = 1; key <= static_cast<int>(values.size()); ++key) add(key, values[key - 1]);
    }
    double get(int key) const { return prefix(key) - prefix(key - 1); }
    double range_sum(int left, int right) const { return prefix(right) - prefix(left - 1); }
    void point_update(int key, double value) {
        double delta = value - values_[key - 1];
        values_[key - 1] = value;
        add(key, delta);
    }
private:
    std::vector<double> values_;
    std::vector<double> tree_;
    void add(int key, double delta) {
        while (key < static_cast<int>(tree_.size())) {
            tree_[key] += delta;
            key += key & -key;
        }
    }
    double prefix(int key) const {
        double result = 0.0;
        while (key > 0) {
            result += tree_[key];
            key -= key & -key;
        }
        return result;
    }
};

class SegmentTreeIndex {
public:
    explicit SegmentTreeIndex(const std::vector<double>& values) {
        size_ = 1;
        while (size_ < static_cast<int>(values.size())) size_ <<= 1;
        tree_.assign(2 * size_, 0.0);
        std::copy(values.begin(), values.end(), tree_.begin() + size_);
        for (int i = size_ - 1; i > 0; --i) tree_[i] = tree_[2 * i] + tree_[2 * i + 1];
    }
    double get(int key) const { return tree_[size_ + key - 1]; }
    double range_sum(int left, int right) const {
        int l = size_ + left - 1;
        int r = size_ + right;
        double result = 0.0;
        while (l < r) {
            if (l & 1) result += tree_[l++];
            if (r & 1) result += tree_[--r];
            l >>= 1;
            r >>= 1;
        }
        return result;
    }
    void point_update(int key, double value) {
        int index = size_ + key - 1;
        tree_[index] = value;
        for (index >>= 1; index > 0; index >>= 1) tree_[index] = tree_[2 * index] + tree_[2 * index + 1];
    }
private:
    int size_ = 0;
    std::vector<double> tree_;
};

template <class Index>
static double execute(Index& index, const std::vector<Operation>& operations) {
    double checksum = 0.0;
    for (const auto& operation : operations) {
        if (operation.type == 0) checksum += index.get(operation.left);
        else if (operation.type == 1) checksum += index.range_sum(operation.left, operation.right);
        else index.point_update(operation.left, operation.value);
    }
    return checksum;
}

template <class Factory>
static std::pair<std::vector<double>, double> measure(
    Factory factory, const std::vector<Operation>& operations, int repeats, double expected
) {
    std::vector<double> samples;
    samples.reserve(repeats);
    double checksum = 0.0;
    for (int repeat = 0; repeat < repeats; ++repeat) {
        auto index = factory();
        auto started = std::chrono::steady_clock::now();
        checksum = execute(index, operations);
        auto stopped = std::chrono::steady_clock::now();
        if (std::abs(checksum - expected) > 1e-8) throw std::runtime_error("checksum mismatch");
        samples.push_back(
            std::chrono::duration<double, std::nano>(stopped - started).count() / operations.size()
        );
    }
    std::sort(samples.begin(), samples.end());
    return {samples, checksum};
}

static void emit(
    int n,
    const std::string& workload,
    const std::string& method,
    int operations,
    int repeats,
    const std::vector<double>& samples,
    double checksum,
    int height,
    int hot_key_depth,
    int nodes
) {
    size_t p95 = std::min(samples.size() - 1, (samples.size() * 95 + 99) / 100 - 1);
    std::cout << n << ',' << workload << ',' << method << ',' << operations << ',' << repeats << ','
              << std::fixed << std::setprecision(3) << samples[samples.size() / 2] << ','
              << samples[p95] << ',' << checksum << ",true," << height << ','
              << hot_key_depth << ',' << nodes << '\n';
}

int main(int argc, char** argv) {
    int operations_count = argc > 1 ? std::atoi(argv[1]) : 200000;
    int repeats = argc > 2 ? std::atoi(argv[2]) : 7;
    if (operations_count < 1 || repeats < 1) return 2;
    std::cout << "n,workload,method,operations,repeats,median_ns_per_operation,"
                 "p95_batch_ns_per_operation,checksum,correct,height,hot_key_depth,node_count\n";
    for (int n : {1024, 16384, 100000}) {
        std::vector<double> values(n);
        for (int i = 0; i < n; ++i) values[i] = static_cast<double>((i * 13 + 7) % 101);
        for (const std::string workload : {"uniform_mixed", "hotspot_point", "clustered_range"}) {
            auto operations = make_trace(n, operations_count, workload);
            ArrayIndex oracle(values);
            double expected = execute(oracle, operations);
            std::vector<double> weights(n + 1, 0.0);
            for (const auto& operation : operations) {
                if (operation.type == 0 || operation.type == 2) weights[operation.left] += 1.0;
                else {
                    weights[operation.left] += 0.5;
                    weights[operation.right] += 0.5;
                }
            }
            double total = std::accumulate(weights.begin() + 1, weights.end(), 0.0);
            for (int key = 1; key <= n; ++key) weights[key] = weights[key] / total;
            int budget = std::min(8, n - 1);
            auto routing = pruned_beam_solve(weights, budget, 0.10, 32, 16).tree;
            int max_depth = 2 * interval_cost(n) + 1;

            auto array_result = measure([&]() { return ArrayIndex(values); }, operations, repeats, expected);
            emit(n, workload, "array", operations_count, repeats, array_result.first, array_result.second, 0, 0, n);
            auto fenwick_result = measure([&]() { return FenwickIndex(values); }, operations, repeats, expected);
            emit(n, workload, "fenwick", operations_count, repeats, fenwick_result.first, fenwick_result.second, interval_cost(n), interval_cost(n), n + 1);
            auto segment_result = measure([&]() { return SegmentTreeIndex(values); }, operations, repeats, expected);
            emit(n, workload, "segment_tree", operations_count, repeats, segment_result.first, segment_result.second, interval_cost(n), interval_cost(n), 2 * n);
            CertiRangeSum metadata(routing, values, max_depth);
            auto certirange_result = measure(
                [&]() { return CertiRangeSum(routing, values, max_depth); },
                operations,
                repeats,
                expected
            );
            emit(
                n, workload, "certirange", operations_count, repeats,
                certirange_result.first, certirange_result.second,
                metadata.height(), metadata.query_depth(1), metadata.node_count()
            );
        }
    }
}
