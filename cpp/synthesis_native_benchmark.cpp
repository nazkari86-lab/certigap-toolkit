#include "certigap_synth.hpp"
#include "synthesis_native_cases.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

class ArrayIndex {
public:
    explicit ArrayIndex(std::vector<double> values)
        : values_(std::move(values)) {}
    double get(int key) const { return values_[key - 1]; }
    double range_query(int left, int right) const {
        return std::accumulate(
            values_.begin() + left - 1, values_.begin() + right, 0.0
        );
    }
    void point_update(int key, double value) { values_[key - 1] = value; }
private:
    std::vector<double> values_;
};

class FenwickIndex {
public:
    explicit FenwickIndex(const std::vector<double>& values)
        : values_(values), tree_(values.size() + 1, 0.0) {
        for (int key = 1; key <= static_cast<int>(values.size()); ++key) {
            add(key, values[key - 1]);
        }
    }
    double get(int key) const { return values_[key - 1]; }
    double range_query(int left, int right) const {
        return prefix(right) - prefix(left - 1);
    }
    void point_update(int key, double value) {
        const double delta = value - values_[key - 1];
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

class SegmentIndex {
public:
    explicit SegmentIndex(const std::vector<double>& values)
        : values_(values) {
        size_ = 1;
        while (size_ < static_cast<int>(values.size())) size_ <<= 1;
        tree_.assign(2 * size_, 0.0);
        std::copy(values.begin(), values.end(), tree_.begin() + size_);
        for (int index = size_ - 1; index > 0; --index) {
            tree_[index] = tree_[2 * index] + tree_[2 * index + 1];
        }
    }
    double get(int key) const { return values_[key - 1]; }
    double range_query(int left, int right) const {
        int lower = size_ + left - 1;
        int upper = size_ + right;
        double result = 0.0;
        while (lower < upper) {
            if (lower & 1) result += tree_[lower++];
            if (upper & 1) result += tree_[--upper];
            lower >>= 1;
            upper >>= 1;
        }
        return result;
    }
    void point_update(int key, double value) {
        values_[key - 1] = value;
        int index = size_ + key - 1;
        tree_[index] = value;
        for (index >>= 1; index > 0; index >>= 1) {
            tree_[index] = tree_[2 * index] + tree_[2 * index + 1];
        }
    }
private:
    int size_ = 0;
    std::vector<double> values_;
    std::vector<double> tree_;
};

template <class Index>
double execute(
    Index& index,
    const synthesis_cases::Operation* operations,
    std::size_t count
) {
    double checksum = 0.0;
    for (std::size_t position = 0; position < count; ++position) {
        const auto& operation = operations[position];
        if (operation.kind == 0) {
            checksum += index.get(operation.left);
        } else if (operation.kind == 1) {
            checksum += index.range_query(operation.left, operation.right);
        } else {
            index.point_update(operation.left, operation.value);
        }
    }
    return checksum;
}

struct Measurement {
    double median = 0.0;
    double p95 = 0.0;
    double mad = 0.0;
    double checksum = 0.0;
};

template <class Factory>
Measurement measure(
    Factory factory,
    const synthesis_cases::Case& scenario,
    double expected
) {
    std::vector<double> samples;
    samples.reserve(9);
    double checksum = 0.0;
    auto warmup = factory();
    if (std::abs(
            execute(warmup, scenario.operations, scenario.operation_count)
            - expected
        ) > 1e-8) {
        throw std::runtime_error("warmup checksum mismatch");
    }
    for (int repeat = 0; repeat < 9; ++repeat) {
        auto index = factory();
        const auto start = std::chrono::steady_clock::now();
        checksum = execute(index, scenario.operations, scenario.operation_count);
        const auto stop = std::chrono::steady_clock::now();
        if (std::abs(checksum - expected) > 1e-8) {
            throw std::runtime_error("checksum mismatch");
        }
        samples.push_back(
            std::chrono::duration<double, std::nano>(stop - start).count()
            / static_cast<double>(scenario.operation_count)
        );
    }
    std::sort(samples.begin(), samples.end());
    std::vector<double> deviations;
    deviations.reserve(samples.size());
    for (double sample : samples) {
        deviations.push_back(std::abs(sample - samples[4]));
    }
    std::sort(deviations.begin(), deviations.end());
    return {samples[4], samples[8], deviations[4], checksum};
}

void emit(
    const synthesis_cases::Case& scenario,
    const std::string& method,
    const Measurement& result,
    std::size_t memory_slots,
    std::size_t blocks
) {
    std::cout << scenario.name << ',' << scenario.n << ',' << method << ','
              << scenario.operation_count << ",9,"
              << std::fixed << std::setprecision(6)
              << result.median << ',' << result.p95 << ',' << result.mad << ','
              << result.checksum << ",true,"
              << memory_slots << ',' << blocks << '\n';
}

}  // namespace

int main() {
    std::cout
        << "scenario,n,method,operations,repeats,median_ns_per_operation,"
           "p95_batch_ns_per_operation,mad_ns_per_operation,checksum,correct,"
           "memory_slots,blocks\n";
    for (std::size_t index = 0; index < synthesis_cases::case_count; ++index) {
        const auto& scenario = synthesis_cases::cases[index];
        std::vector<double> values(scenario.n);
        for (int key = 0; key < scenario.n; ++key) {
            values[key] = static_cast<double>((key * 13 + 7) % 101);
        }
        ArrayIndex oracle(values);
        const double expected = execute(
            oracle, scenario.operations, scenario.operation_count
        );
        const auto array = measure(
            [&]() { return ArrayIndex(values); }, scenario, expected
        );
        emit(scenario, "array", array, values.size(), 0);
        const auto fenwick = measure(
            [&]() { return FenwickIndex(values); }, scenario, expected
        );
        emit(scenario, "fenwick", fenwick, 2 * values.size() + 1, 0);
        const auto segment = measure(
            [&]() { return SegmentIndex(values); }, scenario, expected
        );
        int power = 1;
        while (power < scenario.n) power <<= 1;
        emit(scenario, "segment_tree", segment, values.size() + 2 * power, 0);
        const std::vector<int> uniform(
            scenario.uniform_boundaries,
            scenario.uniform_boundaries + scenario.uniform_count
        );
        const auto uniform_result = measure(
            [&]() {
                return certigap::VariableBlockIndex(
                    values, uniform, certigap::Aggregate::Sum
                );
            },
            scenario,
            expected
        );
        emit(
            scenario,
            "uniform_block",
            uniform_result,
            2 * values.size() + 2 * uniform.size(),
            uniform.size()
        );
        const std::vector<int> synthesized(
            scenario.synthesized_boundaries,
            scenario.synthesized_boundaries + scenario.synthesized_count
        );
        const auto synthesized_result = measure(
            [&]() {
                return certigap::VariableBlockIndex(
                    values, synthesized, certigap::Aggregate::Sum
                );
            },
            scenario,
            expected
        );
        emit(
            scenario,
            "certigap_x",
            synthesized_result,
            2 * values.size() + 2 * synthesized.size(),
            synthesized.size()
        );
    }
}
