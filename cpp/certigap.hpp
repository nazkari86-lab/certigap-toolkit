// CertiGap single-header distribution. Generated; do not edit.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>


namespace certigap {

enum class Backend {
    SortedArray,
    PrefixSum,
    Fenwick,
    SqrtDecomposition,
    SegmentTree,
    SparseTable,
    CertiRangePoint,
    CertiRangeRange,
};

enum class Aggregate {
    Sum,
    Min,
    Max,
};

struct TopologyNode {
    int left;
    int right;
    int threshold;
    int left_child;
    int right_child;

    constexpr bool leaf() const { return left_child < 0; }
};

template <class Config>
class AutoIndex {
public:
    explicit AutoIndex(const std::vector<double>& values) : values_(values) {
        if (values_.size() != Config::kN || values_.empty()) {
            throw std::invalid_argument("values size differs from generated config");
        }
        for (double value : values_) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("values must be finite");
            }
        }
        if constexpr (Config::kBackend == Backend::PrefixSum) {
            static_assert(
                Config::kAggregate == Aggregate::Sum,
                "prefix-sum generated backend supports sum only"
            );
            rebuild_prefix();
        } else if constexpr (Config::kBackend == Backend::Fenwick) {
            static_assert(
                Config::kAggregate == Aggregate::Sum,
                "Fenwick generated backend supports sum only"
            );
            fenwick_.assign(values_.size() + 1, 0.0);
            for (int key = 1; key <= static_cast<int>(values_.size()); ++key) {
                fenwick_add(key, values_[key - 1]);
            }
        } else if constexpr (
            Config::kBackend == Backend::SqrtDecomposition
        ) {
            block_size_ = std::max(
                1, static_cast<int>(std::ceil(std::sqrt(values_.size())))
            );
            blocks_.assign(
                (values_.size() + block_size_ - 1) / block_size_, identity()
            );
            for (int block = 0; block < static_cast<int>(blocks_.size()); ++block) {
                rebuild_block(block);
            }
        } else if constexpr (Config::kBackend == Backend::SegmentTree) {
            segment_size_ = 1;
            while (segment_size_ < static_cast<int>(values_.size())) {
                segment_size_ <<= 1;
            }
            segment_.assign(2 * segment_size_, identity());
            std::copy(
                values_.begin(), values_.end(),
                segment_.begin() + segment_size_
            );
            for (int index = segment_size_ - 1; index > 0; --index) {
                segment_[index] = combine(
                    segment_[2 * index], segment_[2 * index + 1]
                );
            }
        } else if constexpr (Config::kBackend == Backend::SparseTable) {
            static_assert(
                Config::kAggregate != Aggregate::Sum,
                "sparse-table backend supports idempotent min/max only"
            );
            rebuild_sparse();
        } else if constexpr (
            Config::kBackend == Backend::CertiRangePoint
            || Config::kBackend == Backend::CertiRangeRange
        ) {
            static_assert(
                Config::kTopology.size() == 2 * Config::kN - 1,
                "generated CertiRange topology must be a complete binary tree"
            );
            certi_aggregate_.assign(Config::kTopology.size(), identity());
            validate_topology(0, 1, static_cast<int>(Config::kN));
            build_certi(0);
        }
    }

    double get(int key) const {
        validate_key(key);
        if constexpr (Config::kBackend == Backend::SegmentTree) {
            return segment_[segment_size_ + key - 1];
        } else if constexpr (
            Config::kBackend == Backend::CertiRangePoint
            || Config::kBackend == Backend::CertiRangeRange
        ) {
            int index = 0;
            while (!Config::kTopology[index].leaf()) {
                index = key <= Config::kTopology[index].threshold
                    ? Config::kTopology[index].left_child
                    : Config::kTopology[index].right_child;
            }
            return certi_aggregate_[index];
        } else {
            return values_[key - 1];
        }
    }

    double range_query(int left, int right) const {
        validate_range(left, right);
        if constexpr (Config::kBackend == Backend::SortedArray) {
            double result = identity();
            for (int key = left; key <= right; ++key) {
                result = combine(result, values_[key - 1]);
            }
            return result;
        } else if constexpr (Config::kBackend == Backend::PrefixSum) {
            return prefix_[right] - prefix_[left - 1];
        } else if constexpr (Config::kBackend == Backend::Fenwick) {
            return fenwick_prefix(right) - fenwick_prefix(left - 1);
        } else if constexpr (
            Config::kBackend == Backend::SqrtDecomposition
        ) {
            int index = left - 1;
            double result = identity();
            while (index < right && index % block_size_ != 0) {
                result = combine(result, values_[index++]);
            }
            while (index + block_size_ <= right) {
                result = combine(result, blocks_[index / block_size_]);
                index += block_size_;
            }
            while (index < right) {
                result = combine(result, values_[index++]);
            }
            return result;
        } else if constexpr (Config::kBackend == Backend::SegmentTree) {
            int lower = segment_size_ + left - 1;
            int upper = segment_size_ + right;
            double left_result = identity();
            double right_result = identity();
            while (lower < upper) {
                if (lower & 1) {
                    left_result = combine(left_result, segment_[lower++]);
                }
                if (upper & 1) {
                    right_result = combine(segment_[--upper], right_result);
                }
                lower >>= 1;
                upper >>= 1;
            }
            return combine(left_result, right_result);
        } else if constexpr (Config::kBackend == Backend::SparseTable) {
            int level = sparse_logs_[right - left + 1];
            int width = 1 << level;
            return combine(
                sparse_[level][left - 1],
                sparse_[level][right - width]
            );
        } else {
            return certi_range(0, left, right);
        }
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("value must be finite");
        }
        if constexpr (Config::kBackend == Backend::PrefixSum) {
            double delta = value - values_[key - 1];
            values_[key - 1] = value;
            for (int index = key; index < static_cast<int>(prefix_.size()); ++index) {
                prefix_[index] += delta;
            }
        } else if constexpr (Config::kBackend == Backend::Fenwick) {
            double delta = value - values_[key - 1];
            values_[key - 1] = value;
            fenwick_add(key, delta);
        } else if constexpr (
            Config::kBackend == Backend::SqrtDecomposition
        ) {
            values_[key - 1] = value;
            rebuild_block((key - 1) / block_size_);
        } else if constexpr (Config::kBackend == Backend::SegmentTree) {
            values_[key - 1] = value;
            int index = segment_size_ + key - 1;
            segment_[index] = value;
            for (index >>= 1; index > 0; index >>= 1) {
                segment_[index] = combine(
                    segment_[2 * index], segment_[2 * index + 1]
                );
            }
        } else if constexpr (Config::kBackend == Backend::SparseTable) {
            values_[key - 1] = value;
            rebuild_sparse();
        } else if constexpr (
            Config::kBackend == Backend::CertiRangePoint
            || Config::kBackend == Backend::CertiRangeRange
        ) {
            values_[key - 1] = value;
            certi_update(0, key, value);
        } else {
            values_[key - 1] = value;
        }
    }

    AutoIndex snapshot() const { return *this; }

    static constexpr Backend backend() { return Config::kBackend; }
    static constexpr Aggregate aggregate() { return Config::kAggregate; }
    static constexpr std::string_view artifact_sha256() {
        return Config::kArtifactSha256;
    }

private:
    std::vector<double> values_;
    std::vector<double> prefix_;
    std::vector<double> fenwick_;
    std::vector<double> blocks_;
    std::vector<double> segment_;
    std::vector<std::vector<double>> sparse_;
    std::vector<int> sparse_logs_;
    std::vector<double> certi_aggregate_;
    int block_size_ = 0;
    int segment_size_ = 0;

    static constexpr double identity() {
        if constexpr (Config::kAggregate == Aggregate::Sum) {
            return 0.0;
        } else if constexpr (Config::kAggregate == Aggregate::Min) {
            return std::numeric_limits<double>::infinity();
        } else {
            return -std::numeric_limits<double>::infinity();
        }
    }

    static constexpr double combine(double left, double right) {
        if constexpr (Config::kAggregate == Aggregate::Sum) {
            return left + right;
        } else if constexpr (Config::kAggregate == Aggregate::Min) {
            return left < right ? left : right;
        } else {
            return left > right ? left : right;
        }
    }

    void validate_key(int key) const {
        if (key < 1 || key > static_cast<int>(values_.size())) {
            throw std::out_of_range("key out of range");
        }
    }

    void validate_range(int left, int right) const {
        if (
            left < 1 || right < left
            || right > static_cast<int>(values_.size())
        ) {
            throw std::out_of_range("invalid range");
        }
    }

    void fenwick_add(int key, double delta) {
        while (key < static_cast<int>(fenwick_.size())) {
            fenwick_[key] += delta;
            key += key & -key;
        }
    }

    double fenwick_prefix(int key) const {
        double result = 0.0;
        while (key > 0) {
            result += fenwick_[key];
            key -= key & -key;
        }
        return result;
    }

    void rebuild_prefix() {
        prefix_.assign(values_.size() + 1, 0.0);
        for (std::size_t index = 0; index < values_.size(); ++index) {
            prefix_[index + 1] = prefix_[index] + values_[index];
        }
    }

    void rebuild_block(int block) {
        int left = block * block_size_;
        int right = std::min(
            static_cast<int>(values_.size()), left + block_size_
        );
        double result = identity();
        for (int index = left; index < right; ++index) {
            result = combine(result, values_[index]);
        }
        blocks_[block] = result;
    }

    void rebuild_sparse() {
        int n = static_cast<int>(values_.size());
        sparse_logs_.assign(n + 1, 0);
        for (int length = 2; length <= n; ++length) {
            sparse_logs_[length] = sparse_logs_[length / 2] + 1;
        }
        sparse_.clear();
        sparse_.push_back(values_);
        for (int level = 1; (1 << level) <= n; ++level) {
            int width = 1 << level;
            int half = width >> 1;
            sparse_.push_back(std::vector<double>(n - width + 1));
            for (int left = 0; left + width <= n; ++left) {
                sparse_[level][left] = combine(
                    sparse_[level - 1][left],
                    sparse_[level - 1][left + half]
                );
            }
        }
    }

    void validate_topology(int index, int expected_left, int expected_right) {
        if (index < 0 || index >= static_cast<int>(Config::kTopology.size())) {
            throw std::invalid_argument("topology child index out of range");
        }
        const auto& node = Config::kTopology[index];
        if (node.left != expected_left || node.right != expected_right) {
            throw std::invalid_argument("topology interval mismatch");
        }
        if (node.leaf()) {
            if (
                node.left != node.right || node.left_child != -1
                || node.right_child != -1
            ) {
                throw std::invalid_argument("invalid topology leaf");
            }
            return;
        }
        if (node.threshold < node.left || node.threshold >= node.right) {
            throw std::invalid_argument("invalid topology threshold");
        }
        validate_topology(
            node.left_child, node.left, node.threshold
        );
        validate_topology(
            node.right_child, node.threshold + 1, node.right
        );
    }

    double build_certi(int index) {
        const auto& node = Config::kTopology[index];
        if (node.leaf()) {
            certi_aggregate_[index] = values_[node.left - 1];
        } else {
            certi_aggregate_[index] = combine(
                build_certi(node.left_child),
                build_certi(node.right_child)
            );
        }
        return certi_aggregate_[index];
    }

    double certi_range(int index, int query_left, int query_right) const {
        const auto& node = Config::kTopology[index];
        if (query_right < node.left || node.right < query_left) {
            return identity();
        }
        if (query_left <= node.left && node.right <= query_right) {
            return certi_aggregate_[index];
        }
        return combine(
            certi_range(node.left_child, query_left, query_right),
            certi_range(node.right_child, query_left, query_right)
        );
    }

    double certi_update(int index, int key, double value) {
        const auto& node = Config::kTopology[index];
        if (node.leaf()) {
            certi_aggregate_[index] = value;
        } else if (key <= node.threshold) {
            certi_update(node.left_child, key, value);
            certi_aggregate_[index] = combine(
                certi_aggregate_[node.left_child],
                certi_aggregate_[node.right_child]
            );
        } else {
            certi_update(node.right_child, key, value);
            certi_aggregate_[index] = combine(
                certi_aggregate_[node.left_child],
                certi_aggregate_[node.right_child]
            );
        }
        return certi_aggregate_[index];
    }
};

}  // namespace certigap

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <numeric>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>
#include <variant>


namespace certigap {

struct OptimizeOptions {
    Aggregate aggregate = Aggregate::Sum;
    double tail_weight = 0.10;
    std::size_t memory_limit_slots = std::numeric_limits<std::size_t>::max();
    int max_depth = 0;
    bool require_certirange = false;
    double memory_weight = 0.0;
    double build_weight = 0.0;
    double array_unit_cost = 1.0;
    double prefix_unit_cost = 1.0;
    double fenwick_unit_cost = 1.0;
    double sqrt_unit_cost = 1.0;
    double segment_tree_unit_cost = 1.0;
    double sparse_unit_cost = 1.0;
    double certirange_unit_cost = 1.0;
};

struct RebuildPolicy {
    std::uint64_t minimum_new_operations = 10'000;
    double minimum_tv_drift = 0.10;
};

struct AutoTunePolicy {
    std::uint64_t warmup_operations = 256;
    std::uint64_t check_interval = 10'000;
    double minimum_tv_drift = 0.10;
    double minimum_relative_improvement = 0.05;
    bool automatic_maintenance = true;
    bool save_profile_on_destruction = true;
    std::string profile_path;
};

struct AutoTuneDecision {
    bool attempted = false;
    bool switched = false;
    std::string previous = "sorted_array";
    std::string selected = "sorted_array";
    std::string reason = "collecting warmup profile";
    double observed_operations = 0.0;
    double previous_score = 0.0;
    double selected_score = 0.0;
    double relative_improvement = 0.0;
};

struct CandidateReport {
    Backend backend = Backend::SortedArray;
    bool feasible = false;
    std::string reason;
    double mean_work = 0.0;
    double max_work = 0.0;
    double score = 0.0;
    std::size_t memory_slots = 0;
    int height = 0;
    std::size_t build_units = 0;
};

inline constexpr std::string_view backend_name(Backend backend) {
    switch (backend) {
        case Backend::SortedArray: return "sorted_array";
        case Backend::PrefixSum: return "prefix_sum";
        case Backend::Fenwick: return "fenwick";
        case Backend::SqrtDecomposition: return "sqrt_decomposition";
        case Backend::SegmentTree: return "segment_tree";
        case Backend::SparseTable: return "sparse_table";
        case Backend::CertiRangePoint: return "certirange_point";
        case Backend::CertiRangeRange: return "certirange_range";
    }
    return "unknown";
}

namespace detail {

inline double identity(Aggregate aggregate) {
    if (aggregate == Aggregate::Sum) return 0.0;
    if (aggregate == Aggregate::Min) {
        return std::numeric_limits<double>::infinity();
    }
    return -std::numeric_limits<double>::infinity();
}

inline double combine(double left, double right, Aggregate aggregate) {
    if (aggregate == Aggregate::Sum) return left + right;
    if (aggregate == Aggregate::Min) return std::min(left, right);
    return std::max(left, right);
}

inline int minimum_height(std::size_t size) {
    int height = 0;
    std::size_t capacity = 1;
    while (capacity < size) {
        capacity <<= 1;
        ++height;
    }
    return height;
}

class ArrayRuntime {
public:
    ArrayRuntime(std::vector<double> values, Aggregate aggregate)
        : values_(std::move(values)), aggregate_(aggregate) {}

    double get(int key) const { return values_[key - 1]; }

    double range_query(int left, int right) const {
        double result = identity(aggregate_);
        for (int key = left; key <= right; ++key) {
            result = combine(result, values_[key - 1], aggregate_);
        }
        return result;
    }

    void point_update(int key, double value) { values_[key - 1] = value; }

private:
    std::vector<double> values_;
    Aggregate aggregate_;
};

class PrefixRuntime {
public:
    explicit PrefixRuntime(std::vector<double> values)
        : values_(std::move(values)), prefix_(values_.size() + 1, 0.0) {
        rebuild();
    }

    double get(int key) const { return values_[key - 1]; }

    double range_query(int left, int right) const {
        return prefix_[right] - prefix_[left - 1];
    }

    void point_update(int key, double value) {
        const double delta = value - values_[key - 1];
        values_[key - 1] = value;
        for (int index = key; index < static_cast<int>(prefix_.size()); ++index) {
            prefix_[index] += delta;
        }
    }

private:
    std::vector<double> values_;
    std::vector<double> prefix_;

    void rebuild() {
        for (std::size_t index = 0; index < values_.size(); ++index) {
            prefix_[index + 1] = prefix_[index] + values_[index];
        }
    }
};

class FenwickRuntime {
public:
    explicit FenwickRuntime(const std::vector<double>& values)
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

class SqrtRuntime {
public:
    SqrtRuntime(std::vector<double> values, Aggregate aggregate)
        : values_(std::move(values)), aggregate_(aggregate) {
        block_size_ = std::max(
            1,
            static_cast<int>(std::ceil(std::sqrt(values_.size())))
        );
        blocks_.assign(
            (values_.size() + block_size_ - 1) / block_size_,
            identity(aggregate_)
        );
        for (int block = 0; block < static_cast<int>(blocks_.size()); ++block) {
            rebuild_block(block);
        }
    }

    double get(int key) const { return values_[key - 1]; }

    double range_query(int left, int right) const {
        int index = left - 1;
        double result = identity(aggregate_);
        while (index < right && index % block_size_ != 0) {
            result = combine(result, values_[index++], aggregate_);
        }
        while (index + block_size_ <= right) {
            result = combine(
                result, blocks_[index / block_size_], aggregate_
            );
            index += block_size_;
        }
        while (index < right) {
            result = combine(result, values_[index++], aggregate_);
        }
        return result;
    }

    void point_update(int key, double value) {
        values_[key - 1] = value;
        rebuild_block((key - 1) / block_size_);
    }

private:
    std::vector<double> values_;
    std::vector<double> blocks_;
    Aggregate aggregate_;
    int block_size_ = 1;

    void rebuild_block(int block) {
        const int first = block * block_size_;
        const int last = std::min(
            static_cast<int>(values_.size()), first + block_size_
        );
        double result = identity(aggregate_);
        for (int index = first; index < last; ++index) {
            result = combine(result, values_[index], aggregate_);
        }
        blocks_[block] = result;
    }
};

class SegmentRuntime {
public:
    SegmentRuntime(const std::vector<double>& values, Aggregate aggregate)
        : aggregate_(aggregate) {
        size_ = 1;
        while (size_ < static_cast<int>(values.size())) size_ <<= 1;
        tree_.assign(2 * size_, identity(aggregate_));
        std::copy(values.begin(), values.end(), tree_.begin() + size_);
        for (int index = size_ - 1; index > 0; --index) {
            tree_[index] = combine(
                tree_[2 * index], tree_[2 * index + 1], aggregate_
            );
        }
    }

    double get(int key) const { return tree_[size_ + key - 1]; }

    double range_query(int left, int right) const {
        int lower = size_ + left - 1;
        int upper = size_ + right;
        double left_result = identity(aggregate_);
        double right_result = identity(aggregate_);
        while (lower < upper) {
            if (lower & 1) {
                left_result = combine(
                    left_result, tree_[lower++], aggregate_
                );
            }
            if (upper & 1) {
                right_result = combine(
                    tree_[--upper], right_result, aggregate_
                );
            }
            lower >>= 1;
            upper >>= 1;
        }
        return combine(left_result, right_result, aggregate_);
    }

    void point_update(int key, double value) {
        int index = size_ + key - 1;
        tree_[index] = value;
        for (index >>= 1; index > 0; index >>= 1) {
            tree_[index] = combine(
                tree_[2 * index], tree_[2 * index + 1], aggregate_
            );
        }
    }

private:
    Aggregate aggregate_;
    int size_ = 0;
    std::vector<double> tree_;
};

class SparseRuntime {
public:
    SparseRuntime(std::vector<double> values, Aggregate aggregate)
        : values_(std::move(values)), aggregate_(aggregate) {
        if (aggregate_ == Aggregate::Sum) {
            throw std::invalid_argument(
                "sparse table supports idempotent min/max only"
            );
        }
        rebuild();
    }

    double get(int key) const { return values_[key - 1]; }

    double range_query(int left, int right) const {
        const int level = logs_[right - left + 1];
        const int width = 1 << level;
        return combine(
            table_[level][left - 1],
            table_[level][right - width],
            aggregate_
        );
    }

    void point_update(int key, double value) {
        values_[key - 1] = value;
        rebuild();
    }

private:
    std::vector<double> values_;
    Aggregate aggregate_;
    std::vector<std::vector<double>> table_;
    std::vector<int> logs_;

    void rebuild() {
        logs_.assign(values_.size() + 1, 0);
        for (std::size_t length = 2; length < logs_.size(); ++length) {
            logs_[length] = logs_[length / 2] + 1;
        }
        table_.clear();
        table_.push_back(values_);
        for (
            int level = 1;
            (1 << level) <= static_cast<int>(values_.size());
            ++level
        ) {
            const int width = 1 << level;
            const int half = width >> 1;
            std::vector<double> row(values_.size() - width + 1);
            for (int index = 0; index < static_cast<int>(row.size()); ++index) {
                row[index] = combine(
                    table_[level - 1][index],
                    table_[level - 1][index + half],
                    aggregate_
                );
            }
            table_.push_back(std::move(row));
        }
    }
};

struct RuntimeNode {
    int left = 0;
    int right = 0;
    int threshold = 0;
    int left_child = -1;
    int right_child = -1;
    double aggregate = 0.0;

    bool leaf() const { return left_child < 0; }
};

inline int weighted_threshold(
    int left,
    int right,
    const std::vector<double>& prefix
) {
    const double base = prefix[left - 1];
    const double target = base + (prefix[right] - base) / 2.0;
    auto begin = prefix.begin() + left;
    auto end = prefix.begin() + right;
    int threshold = static_cast<int>(
        std::lower_bound(begin, end, target) - prefix.begin()
    );
    return std::max(left, std::min(right - 1, threshold));
}

inline int build_topology(
    std::vector<RuntimeNode>& nodes,
    int left,
    int right,
    int remaining_depth,
    const std::vector<double>& prefix
) {
    const int index = static_cast<int>(nodes.size());
    nodes.push_back({left, right, left, -1, -1, 0.0});
    if (left == right) return index;
    const int size = right - left + 1;
    int threshold = left + (right - left) / 2;
    if (remaining_depth > minimum_height(size)) {
        const int proposed = weighted_threshold(left, right, prefix);
        const bool fits =
            minimum_height(proposed - left + 1) <= remaining_depth - 1
            && minimum_height(right - proposed) <= remaining_depth - 1;
        if (fits) threshold = proposed;
    }
    nodes[index].threshold = threshold;
    nodes[index].left_child = build_topology(
        nodes, left, threshold, remaining_depth - 1, prefix
    );
    nodes[index].right_child = build_topology(
        nodes, threshold + 1, right, remaining_depth - 1, prefix
    );
    return index;
}

class CertiRuntime {
public:
    CertiRuntime(
        const std::vector<double>& values,
        Aggregate aggregate,
        std::vector<RuntimeNode> nodes
    ) : aggregate_(aggregate), nodes_(std::move(nodes)) {
        if (nodes_.size() != 2 * values.size() - 1) {
            throw std::invalid_argument("incomplete adaptive topology");
        }
        build(0, values);
    }

    double get(int key) const {
        int index = 0;
        while (!nodes_[index].leaf()) {
            index = key <= nodes_[index].threshold
                ? nodes_[index].left_child
                : nodes_[index].right_child;
        }
        return nodes_[index].aggregate;
    }

    double range_query(int left, int right) const {
        return range_query(0, left, right);
    }

    void point_update(int key, double value) {
        point_update(0, key, value);
    }

private:
    Aggregate aggregate_;
    std::vector<RuntimeNode> nodes_;

    double build(int index, const std::vector<double>& values) {
        auto& node = nodes_[index];
        if (node.leaf()) {
            node.aggregate = values[node.left - 1];
        } else {
            node.aggregate = combine(
                build(node.left_child, values),
                build(node.right_child, values),
                aggregate_
            );
        }
        return node.aggregate;
    }

    double range_query(int index, int left, int right) const {
        const auto& node = nodes_[index];
        if (right < node.left || node.right < left) {
            return identity(aggregate_);
        }
        if (left <= node.left && node.right <= right) {
            return node.aggregate;
        }
        return combine(
            range_query(node.left_child, left, right),
            range_query(node.right_child, left, right),
            aggregate_
        );
    }

    double point_update(int index, int key, double value) {
        auto& node = nodes_[index];
        if (node.leaf()) {
            node.aggregate = value;
        } else {
            point_update(
                key <= node.threshold ? node.left_child : node.right_child,
                key,
                value
            );
            node.aggregate = combine(
                nodes_[node.left_child].aggregate,
                nodes_[node.right_child].aggregate,
                aggregate_
            );
        }
        return node.aggregate;
    }
};

struct WorkAccumulator {
    double total_weight = 0.0;
    double weighted_work = 0.0;
    double maximum_work = 0.0;

    void add(double work, double weight) {
        if (weight <= 0.0) return;
        total_weight += weight;
        weighted_work += work * weight;
        maximum_work = std::max(maximum_work, work);
    }
};

inline int fenwick_prefix_steps(int key) {
    int steps = 0;
    while (key > 0) {
        ++steps;
        key -= key & -key;
    }
    return steps;
}

inline int fenwick_update_steps(int key, int n) {
    int steps = 0;
    while (key <= n) {
        ++steps;
        key += key & -key;
    }
    return steps;
}

inline int segment_range_steps(int left, int right, int size) {
    int lower = size + left - 1;
    int upper = size + right;
    int steps = 0;
    while (lower < upper) {
        if (lower & 1) {
            ++steps;
            ++lower;
        }
        if (upper & 1) {
            --upper;
            ++steps;
        }
        lower >>= 1;
        upper >>= 1;
    }
    return std::max(1, steps);
}

inline int sqrt_range_steps(int left, int right, int block_size) {
    int index = left - 1;
    int steps = 0;
    while (index < right && index % block_size != 0) {
        ++steps;
        ++index;
    }
    while (index + block_size <= right) {
        ++steps;
        index += block_size;
    }
    return steps + right - index;
}

inline std::size_t sparse_table_entries(std::size_t size) {
    std::size_t entries = 0;
    for (std::size_t width = 1; width <= size; width <<= 1) {
        entries += size - width + 1;
        if (width > size / 2) break;
    }
    return entries;
}

inline void topology_depths(
    const std::vector<RuntimeNode>& nodes,
    int index,
    int depth,
    std::vector<int>& result
) {
    const auto& node = nodes[index];
    if (node.leaf()) {
        result[node.left - 1] = depth;
        return;
    }
    topology_depths(nodes, node.left_child, depth + 1, result);
    topology_depths(nodes, node.right_child, depth + 1, result);
}

inline int topology_range_visits(
    const std::vector<RuntimeNode>& nodes,
    int index,
    int left,
    int right
) {
    const auto& node = nodes[index];
    if (right < node.left || node.right < left) return 1;
    if (left <= node.left && node.right <= right) return 1;
    if (node.leaf()) return 1;
    return 1
        + topology_range_visits(nodes, node.left_child, left, right)
        + topology_range_visits(nodes, node.right_child, left, right);
}

}  // namespace detail

class AdaptiveIndex {
public:
    explicit AdaptiveIndex(
        const std::vector<double>& values,
        Aggregate aggregate = Aggregate::Sum
    )
        : values_(values),
          point_counts_(values.size(), 0.0),
          update_counts_(values.size(), 0.0),
          aggregate_(aggregate),
          runtime_(detail::ArrayRuntime(values, aggregate)) {
        if (values_.empty()) {
            throw std::invalid_argument("values must not be empty");
        }
        for (double value : values_) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("values must be finite");
            }
        }
        options_.aggregate = aggregate;
    }

    double get(int key) {
        validate_key(key);
        observe_get(key);
        return peek(key);
    }

    double peek(int key) const {
        validate_key(key);
        return std::visit(
            [key](const auto& runtime) { return runtime.get(key); },
            runtime_
        );
    }

    double range_query(int left, int right) {
        validate_range(left, right);
        observe_range(left, right);
        return peek_range(left, right);
    }

    double peek_range(int left, int right) const {
        validate_range(left, right);
        return std::visit(
            [left, right](const auto& runtime) {
                return runtime.range_query(left, right);
            },
            runtime_
        );
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("value must be finite");
        }
        observe_update(key);
        values_[key - 1] = value;
        std::visit(
            [key, value](auto& runtime) {
                runtime.point_update(key, value);
            },
            runtime_
        );
    }

    void observe_get(int key, double weight = 1.0) {
        validate_key(key);
        validate_weight(weight);
        point_counts_[key - 1] += weight;
        record(weight);
    }

    void observe_range(int left, int right, double weight = 1.0) {
        validate_range(left, right);
        validate_weight(weight);
        range_counts_[{left, right}] += weight;
        record(weight);
    }

    void observe_update(int key, double weight = 1.0) {
        validate_key(key);
        validate_weight(weight);
        update_counts_[key - 1] += weight;
        record(weight);
    }

    Backend optimize() {
        return optimize(options_);
    }

    Backend optimize(const OptimizeOptions& options) {
        validate_options(options);
        if (observed_weight_ <= 0.0) {
            throw std::logic_error(
                "optimize requires at least one observed operation"
            );
        }
        options_ = options;
        aggregate_ = options.aggregate;
        const int balanced_height = detail::minimum_height(values_.size());
        const int max_depth = options.max_depth == 0
            ? 2 * balanced_height + 1
            : options.max_depth;
        auto point_topology = make_topology(false, max_depth);
        auto range_topology = make_topology(true, max_depth);
        leaderboard_.clear();
        leaderboard_.reserve(8);
        leaderboard_.push_back(score_candidate(
            Backend::SortedArray, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::PrefixSum, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::Fenwick, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::SqrtDecomposition, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::SegmentTree, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::SparseTable, {}, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::CertiRangePoint, point_topology, options
        ));
        leaderboard_.push_back(score_candidate(
            Backend::CertiRangeRange, range_topology, options
        ));
        std::size_t best = leaderboard_.size();
        for (std::size_t index = 0; index < leaderboard_.size(); ++index) {
            if (!leaderboard_[index].feasible) continue;
            if (
                best == leaderboard_.size()
                || leaderboard_[index].score < leaderboard_[best].score - 1e-12
                || (
                    std::abs(
                        leaderboard_[index].score - leaderboard_[best].score
                    ) <= 1e-12
                    && leaderboard_[index].memory_slots
                        < leaderboard_[best].memory_slots
                )
            ) {
                best = index;
            }
        }
        if (best == leaderboard_.size()) {
            throw std::invalid_argument(
                "no adaptive candidate satisfies the constraints"
            );
        }
        selected_ = leaderboard_[best].backend;
        if (selected_ == Backend::SortedArray) {
            runtime_.emplace<detail::ArrayRuntime>(values_, aggregate_);
        } else if (selected_ == Backend::PrefixSum) {
            runtime_.emplace<detail::PrefixRuntime>(values_);
        } else if (selected_ == Backend::Fenwick) {
            runtime_.emplace<detail::FenwickRuntime>(values_);
        } else if (selected_ == Backend::SqrtDecomposition) {
            runtime_.emplace<detail::SqrtRuntime>(values_, aggregate_);
        } else if (selected_ == Backend::SegmentTree) {
            runtime_.emplace<detail::SegmentRuntime>(values_, aggregate_);
        } else if (selected_ == Backend::SparseTable) {
            runtime_.emplace<detail::SparseRuntime>(values_, aggregate_);
        } else if (selected_ == Backend::CertiRangePoint) {
            runtime_.emplace<detail::CertiRuntime>(
                values_, aggregate_, std::move(point_topology)
            );
        } else {
            runtime_.emplace<detail::CertiRuntime>(
                values_, aggregate_, std::move(range_topology)
            );
        }
        optimized_ = true;
        observed_weight_at_last_optimize_ = observed_weight_;
        last_routing_distribution_ = routing_distribution();
        return selected_;
    }

    bool maybe_reoptimize(const RebuildPolicy& policy = RebuildPolicy{}) {
        if (policy.minimum_new_operations == 0) {
            throw std::invalid_argument(
                "minimum_new_operations must be positive"
            );
        }
        if (
            !std::isfinite(policy.minimum_tv_drift)
            || policy.minimum_tv_drift < 0.0
            || policy.minimum_tv_drift > 1.0
        ) {
            throw std::invalid_argument(
                "minimum_tv_drift must lie in [0,1]"
            );
        }
        const double new_weight =
            observed_weight_ - observed_weight_at_last_optimize_;
        if (
            new_weight
            < static_cast<double>(policy.minimum_new_operations)
        ) {
            return false;
        }
        if (!optimized_) {
            optimize(options_);
            return true;
        }
        const auto current = routing_distribution();
        double tv = 0.0;
        for (std::size_t index = 0; index < current.size(); ++index) {
            tv += std::abs(
                current[index] - last_routing_distribution_[index]
            );
        }
        tv *= 0.5;
        if (tv + 1e-12 < policy.minimum_tv_drift) return false;
        optimize(options_);
        return true;
    }

    AdaptiveIndex snapshot() const { return *this; }

    Backend selected_backend() const { return selected_; }
    std::string_view selected_name() const { return backend_name(selected_); }
    bool optimized() const { return optimized_; }
    double observed_weight() const { return observed_weight_; }
    const std::vector<CandidateReport>& leaderboard() const {
        return leaderboard_;
    }

    void export_profile(std::ostream& output) const {
        output << "CERTIGAP_PROFILE_V1\n";
        output << "size " << values_.size() << '\n';
        output << "aggregate " << aggregate_name(aggregate_) << '\n';
        output << std::setprecision(17);
        for (std::size_t index = 0; index < point_counts_.size(); ++index) {
            if (point_counts_[index] > 0.0) {
                output << "get " << index + 1 << ' '
                       << point_counts_[index] << '\n';
            }
        }
        for (std::size_t index = 0; index < update_counts_.size(); ++index) {
            if (update_counts_[index] > 0.0) {
                output << "update " << index + 1 << ' '
                       << update_counts_[index] << '\n';
            }
        }
        for (const auto& [range, weight] : range_counts_) {
            output << "range " << range.first << ' ' << range.second
                   << ' ' << weight << '\n';
        }
        output << "end\n";
        if (!output) throw std::runtime_error("failed to write profile");
    }

    void import_profile(std::istream& input, bool merge = false) {
        std::string magic;
        if (!(input >> magic) || magic != "CERTIGAP_PROFILE_V1") {
            throw std::invalid_argument("invalid CertiGap profile header");
        }
        std::string field;
        std::size_t size = 0;
        std::string aggregate;
        if (!(input >> field >> size) || field != "size" || size != values_.size()) {
            throw std::invalid_argument("profile size mismatch");
        }
        if (!(input >> field >> aggregate) || field != "aggregate") {
            throw std::invalid_argument("profile aggregate is missing");
        }
        if (aggregate != aggregate_name(aggregate_)) {
            throw std::invalid_argument("profile aggregate mismatch");
        }
        std::vector<double> points(values_.size(), 0.0);
        std::vector<double> updates(values_.size(), 0.0);
        std::map<std::pair<int, int>, double> ranges;
        std::size_t records = 0;
        bool ended = false;
        while (input >> field) {
            if (field == "end") {
                ended = true;
                break;
            }
            if (++records > 1'000'000) {
                throw std::invalid_argument("profile record limit exceeded");
            }
            if (field == "get" || field == "update") {
                int key = 0;
                double weight = 0.0;
                if (!(input >> key >> weight)) {
                    throw std::invalid_argument("invalid point profile record");
                }
                validate_key(key);
                validate_profile_weight(weight);
                auto& target = field == "get" ? points : updates;
                target[key - 1] += weight;
            } else if (field == "range") {
                int left = 0;
                int right = 0;
                double weight = 0.0;
                if (!(input >> left >> right >> weight)) {
                    throw std::invalid_argument("invalid range profile record");
                }
                validate_range(left, right);
                validate_profile_weight(weight);
                ranges[{left, right}] += weight;
            } else {
                throw std::invalid_argument("unknown profile record");
            }
        }
        input >> std::ws;
        if (!ended || !input.eof()) {
            throw std::invalid_argument("profile has trailing or missing content");
        }
        double imported_weight = std::accumulate(
            points.begin(), points.end(), 0.0
        );
        imported_weight = std::accumulate(
            updates.begin(), updates.end(), imported_weight
        );
        for (const auto& entry : ranges) imported_weight += entry.second;
        if (
            !std::isfinite(imported_weight)
            || (merge && !std::isfinite(profile_weight() + imported_weight))
        ) {
            throw std::invalid_argument("profile weight overflow");
        }
        if (!merge) {
            point_counts_ = std::move(points);
            update_counts_ = std::move(updates);
            range_counts_ = std::move(ranges);
        } else {
            for (std::size_t index = 0; index < points.size(); ++index) {
                point_counts_[index] += points[index];
                update_counts_[index] += updates[index];
            }
            for (const auto& [range, weight] : ranges) {
                range_counts_[range] += weight;
            }
        }
        observed_weight_ = profile_weight();
        observed_weight_at_last_optimize_ = 0.0;
        optimized_ = false;
        selected_ = Backend::SortedArray;
        runtime_.emplace<detail::ArrayRuntime>(values_, aggregate_);
        leaderboard_.clear();
        last_routing_distribution_.clear();
    }

    void save_profile(const std::string& path) const {
        std::ofstream output(path, std::ios::out | std::ios::trunc);
        if (!output) throw std::runtime_error("cannot open profile for writing");
        export_profile(output);
    }

    bool load_profile(const std::string& path, bool merge = false) {
        std::ifstream input(path);
        if (!input) return false;
        import_profile(input, merge);
        return true;
    }

private:
    using Runtime = std::variant<
        detail::ArrayRuntime,
        detail::PrefixRuntime,
        detail::FenwickRuntime,
        detail::SqrtRuntime,
        detail::SegmentRuntime,
        detail::SparseRuntime,
        detail::CertiRuntime
    >;

    std::vector<double> values_;
    std::vector<double> point_counts_;
    std::vector<double> update_counts_;
    std::map<std::pair<int, int>, double> range_counts_;
    Aggregate aggregate_ = Aggregate::Sum;
    Runtime runtime_;
    Backend selected_ = Backend::SortedArray;
    bool optimized_ = false;
    double observed_weight_ = 0.0;
    double observed_weight_at_last_optimize_ = 0.0;
    OptimizeOptions options_;
    std::vector<CandidateReport> leaderboard_;
    std::vector<double> last_routing_distribution_;

    void validate_key(int key) const {
        if (key < 1 || key > static_cast<int>(values_.size())) {
            throw std::out_of_range("key out of range");
        }
    }

    void validate_range(int left, int right) const {
        if (
            left < 1 || right < left
            || right > static_cast<int>(values_.size())
        ) {
            throw std::out_of_range("invalid range");
        }
    }

    static void validate_weight(double weight) {
        if (!std::isfinite(weight) || weight <= 0.0) {
            throw std::invalid_argument("observation weight must be positive");
        }
    }

    static void validate_profile_weight(double weight) {
        if (!std::isfinite(weight) || weight <= 0.0) {
            throw std::invalid_argument("profile weight must be positive");
        }
    }

    static constexpr std::string_view aggregate_name(Aggregate aggregate) {
        if (aggregate == Aggregate::Sum) return "sum";
        if (aggregate == Aggregate::Min) return "min";
        return "max";
    }

    double profile_weight() const {
        double total = std::accumulate(
            point_counts_.begin(), point_counts_.end(), 0.0
        );
        total = std::accumulate(
            update_counts_.begin(), update_counts_.end(), total
        );
        for (const auto& entry : range_counts_) total += entry.second;
        return total;
    }

    void record(double weight) {
        observed_weight_ += weight;
    }

    void validate_options(const OptimizeOptions& options) const {
        if (
            !std::isfinite(options.tail_weight)
            || options.tail_weight < 0.0
            || options.tail_weight > 1.0
        ) {
            throw std::invalid_argument("tail_weight must lie in [0,1]");
        }
        if (
            options.memory_limit_slots == 0
            || options.max_depth < 0
            || (
                options.max_depth > 0
                && options.max_depth
                    < detail::minimum_height(values_.size())
            )
        ) {
            throw std::invalid_argument("resource constraints are infeasible");
        }
        for (double value : {
            options.memory_weight,
            options.build_weight,
            options.array_unit_cost,
            options.prefix_unit_cost,
            options.fenwick_unit_cost,
            options.sqrt_unit_cost,
            options.segment_tree_unit_cost,
            options.sparse_unit_cost,
            options.certirange_unit_cost,
        }) {
            if (!std::isfinite(value) || value < 0.0) {
                throw std::invalid_argument("cost weights must be non-negative");
            }
        }
        if (
            options.array_unit_cost == 0.0
            || options.prefix_unit_cost == 0.0
            || options.fenwick_unit_cost == 0.0
            || options.sqrt_unit_cost == 0.0
            || options.segment_tree_unit_cost == 0.0
            || options.sparse_unit_cost == 0.0
            || options.certirange_unit_cost == 0.0
        ) {
            throw std::invalid_argument("unit costs must be positive");
        }
    }

    std::vector<double> routing_weights(bool ranges) const {
        const int n = static_cast<int>(values_.size());
        std::vector<double> weights(n, 1e-12);
        for (int index = 0; index < n; ++index) {
            weights[index] += point_counts_[index] + update_counts_[index];
        }
        if (ranges) {
            std::vector<double> difference(n + 1, 0.0);
            for (const auto& entry : range_counts_) {
                const int left = entry.first.first;
                const int right = entry.first.second;
                const double per_key =
                    entry.second / static_cast<double>(right - left + 1);
                difference[left - 1] += per_key;
                difference[right] -= per_key;
            }
            double running = 0.0;
            for (int index = 0; index < n; ++index) {
                running += difference[index];
                weights[index] += running;
            }
        } else {
            for (const auto& entry : range_counts_) {
                weights[entry.first.first - 1] += entry.second * 0.5;
                weights[entry.first.second - 1] += entry.second * 0.5;
            }
        }
        return weights;
    }

    std::vector<double> routing_distribution() const {
        auto weights = routing_weights(true);
        const double total = std::accumulate(
            weights.begin(), weights.end(), 0.0
        );
        for (double& value : weights) value /= total;
        return weights;
    }

    std::vector<detail::RuntimeNode> make_topology(
        bool ranges,
        int max_depth
    ) const {
        auto weights = routing_weights(ranges);
        std::vector<double> prefix(weights.size() + 1, 0.0);
        for (std::size_t index = 0; index < weights.size(); ++index) {
            prefix[index + 1] = prefix[index] + weights[index];
        }
        std::vector<detail::RuntimeNode> nodes;
        nodes.reserve(2 * values_.size() - 1);
        detail::build_topology(
            nodes,
            1,
            static_cast<int>(values_.size()),
            max_depth,
            prefix
        );
        return nodes;
    }

    detail::WorkAccumulator work_for(
        Backend backend,
        const std::vector<detail::RuntimeNode>& topology,
        double unit_cost
    ) const {
        const int n = static_cast<int>(values_.size());
        int size = 1;
        while (size < n) size <<= 1;
        std::vector<int> depths(n, 0);
        if (!topology.empty()) {
            detail::topology_depths(topology, 0, 0, depths);
        }
        detail::WorkAccumulator result;
        for (int key = 1; key <= n; ++key) {
            double get_work = 1.0;
            double update_work = 1.0;
            if (backend == Backend::PrefixSum) {
                update_work = n - key + 2;
            } else if (backend == Backend::Fenwick) {
                update_work = detail::fenwick_update_steps(key, n);
            } else if (backend == Backend::SqrtDecomposition) {
                const int block_size = std::max(
                    1,
                    static_cast<int>(std::ceil(std::sqrt(values_.size())))
                );
                const int block_start = ((key - 1) / block_size) * block_size;
                update_work = std::min(block_size, n - block_start) + 1;
            } else if (backend == Backend::SegmentTree) {
                update_work = detail::minimum_height(values_.size()) + 1;
            } else if (backend == Backend::SparseTable) {
                update_work = detail::sparse_table_entries(values_.size()) + 1;
            } else if (
                backend == Backend::CertiRangePoint
                || backend == Backend::CertiRangeRange
            ) {
                get_work = depths[key - 1] + 1;
                update_work = get_work;
            }
            result.add(get_work * unit_cost, point_counts_[key - 1]);
            result.add(update_work * unit_cost, update_counts_[key - 1]);
        }
        for (const auto& entry : range_counts_) {
            const int left = entry.first.first;
            const int right = entry.first.second;
            double work = right - left + 1;
            if (backend == Backend::PrefixSum) {
                work = left == 1 ? 1 : 2;
            } else if (backend == Backend::Fenwick) {
                work = std::max(
                    1,
                    detail::fenwick_prefix_steps(right)
                        + detail::fenwick_prefix_steps(left - 1)
                );
            } else if (backend == Backend::SqrtDecomposition) {
                const int block_size = std::max(
                    1,
                    static_cast<int>(std::ceil(std::sqrt(values_.size())))
                );
                work = detail::sqrt_range_steps(left, right, block_size);
            } else if (backend == Backend::SegmentTree) {
                work = detail::segment_range_steps(left, right, size);
            } else if (backend == Backend::SparseTable) {
                work = 2;
            } else if (
                backend == Backend::CertiRangePoint
                || backend == Backend::CertiRangeRange
            ) {
                work = detail::topology_range_visits(
                    topology, 0, left, right
                );
            }
            result.add(work * unit_cost, entry.second);
        }
        return result;
    }

    CandidateReport score_candidate(
        Backend backend,
        const std::vector<detail::RuntimeNode>& topology,
        const OptimizeOptions& options
    ) const {
        const std::size_t n = values_.size();
        std::size_t size = 1;
        while (size < n) size <<= 1;
        CandidateReport report;
        report.backend = backend;
        report.feasible = true;
        report.reason = "feasible";
        double unit_cost = options.array_unit_cost;
        if (backend == Backend::PrefixSum) {
            unit_cost = options.prefix_unit_cost;
            report.memory_slots = 3 * n + 1;
            report.height = 1;
            report.build_units = n;
            if (options.aggregate != Aggregate::Sum) {
                report.feasible = false;
                report.reason = "prefix sum supports sum only";
            }
        } else if (backend == Backend::Fenwick) {
            unit_cost = options.fenwick_unit_cost;
            report.memory_slots = 3 * n + 1;
            report.height = detail::minimum_height(n);
            report.build_units = n * (report.height + 1);
            if (options.aggregate != Aggregate::Sum) {
                report.feasible = false;
                report.reason = "Fenwick supports sum only";
            }
        } else if (backend == Backend::SqrtDecomposition) {
            unit_cost = options.sqrt_unit_cost;
            const std::size_t block_size = std::max<std::size_t>(
                1,
                static_cast<std::size_t>(std::ceil(std::sqrt(n)))
            );
            const std::size_t blocks = (n + block_size - 1) / block_size;
            report.memory_slots = 2 * n + blocks;
            report.height = 1;
            report.build_units = n + blocks;
        } else if (backend == Backend::SegmentTree) {
            unit_cost = options.segment_tree_unit_cost;
            report.memory_slots = n + 2 * size;
            report.height = detail::minimum_height(n);
            report.build_units = 2 * size;
        } else if (backend == Backend::SparseTable) {
            unit_cost = options.sparse_unit_cost;
            const std::size_t entries = detail::sparse_table_entries(n);
            report.memory_slots = 3 * n + entries;
            report.height = 1;
            report.build_units = entries;
            if (options.aggregate == Aggregate::Sum) {
                report.feasible = false;
                report.reason = "sparse table supports idempotent min/max only";
            }
        } else if (
            backend == Backend::CertiRangePoint
            || backend == Backend::CertiRangeRange
        ) {
            unit_cost = options.certirange_unit_cost;
            report.memory_slots = 3 * n - 1;
            report.build_units = 2 * n - 1;
            std::vector<int> depths(n, 0);
            detail::topology_depths(topology, 0, 0, depths);
            report.height = *std::max_element(depths.begin(), depths.end());
        } else {
            report.memory_slots = 2 * n;
            report.height = 0;
            report.build_units = n;
        }
        if (
            options.require_certirange
            && backend != Backend::CertiRangePoint
            && backend != Backend::CertiRangeRange
        ) {
            report.feasible = false;
            report.reason = "CertiRange backend required";
        }
        if (report.memory_slots > options.memory_limit_slots) {
            report.feasible = false;
            report.reason = "memory limit exceeded";
        }
        if (
            options.max_depth > 0 && report.height > options.max_depth
        ) {
            report.feasible = false;
            report.reason = "depth limit exceeded";
        }
        const auto work = work_for(backend, topology, unit_cost);
        report.mean_work = work.weighted_work / work.total_weight;
        report.max_work = work.maximum_work;
        report.score =
            (1.0 - options.tail_weight) * report.mean_work
            + options.tail_weight * report.max_work
            + options.memory_weight * report.memory_slots
            + options.build_weight * report.build_units;
        return report;
    }
};

using Index = AdaptiveIndex;

template <class T = double>
class adaptive_array {
    static_assert(std::is_arithmetic<T>::value, "adaptive_array requires arithmetic values");

public:
    explicit adaptive_array(
        const std::vector<T>& values,
        AutoTunePolicy policy = {},
        OptimizeOptions options = {}
    )
        : index_(to_double(values), options.aggregate),
          policy_(std::move(policy)),
          options_(options),
          values_size_(values.size()) {
        validate_policy();
        if (!policy_.profile_path.empty()) {
            index_.load_profile(policy_.profile_path);
            decision_.observed_operations = index_.observed_weight();
            if (index_.observed_weight() >= policy_.warmup_operations) {
                maintenance();
            }
        }
    }

    adaptive_array(const adaptive_array&) = default;
    adaptive_array(adaptive_array&&) noexcept = default;
    adaptive_array& operator=(const adaptive_array&) = default;
    adaptive_array& operator=(adaptive_array&&) noexcept = default;

    ~adaptive_array() {
        if (
            policy_.save_profile_on_destruction
            && !policy_.profile_path.empty()
        ) {
            try {
                index_.save_profile(policy_.profile_path);
            } catch (...) {
                // Destructors cannot report persistence errors safely.
            }
        }
    }

    T get(int position) {
        const T result = static_cast<T>(index_.get(internal_key(position)));
        automatic_maintenance();
        return result;
    }

    double range_query(int first, int last) {
        validate_half_open_range(first, last);
        const double result = index_.range_query(first + 1, last);
        automatic_maintenance();
        return result;
    }

    double range_sum(int first, int last) {
        if (options_.aggregate != Aggregate::Sum) {
            throw std::logic_error("range_sum requires the sum aggregate");
        }
        return range_query(first, last);
    }

    void update(int position, T value) {
        index_.point_update(internal_key(position), static_cast<double>(value));
        automatic_maintenance();
    }

    bool maintenance() {
        const double observed = index_.observed_weight();
        decision_.observed_operations = observed;
        const double threshold = index_.optimized()
            ? last_attempt_weight_ + static_cast<double>(policy_.check_interval)
            : (
                last_attempt_weight_ == 0.0
                    ? static_cast<double>(policy_.warmup_operations)
                    : last_attempt_weight_
                        + static_cast<double>(policy_.check_interval)
            );
        if (observed + 1e-12 < threshold) return false;

        AdaptiveIndex previous = index_;
        const Backend previous_backend = previous.selected_backend();
        bool attempted = false;
        if (!index_.optimized()) {
            index_.optimize(options_);
            attempted = true;
        } else {
            RebuildPolicy rebuild;
            rebuild.minimum_new_operations = policy_.check_interval;
            rebuild.minimum_tv_drift = policy_.minimum_tv_drift;
            attempted = index_.maybe_reoptimize(rebuild);
        }
        last_attempt_weight_ = observed;
        if (!attempted) {
            decision_.attempted = false;
            decision_.reason = "profile drift below reoptimization threshold";
            return false;
        }

        const auto& rows = index_.leaderboard();
        const auto previous_row = std::find_if(
            rows.begin(), rows.end(),
            [previous_backend](const CandidateReport& row) {
                return row.backend == previous_backend;
            }
        );
        const auto selected_row = std::find_if(
            rows.begin(), rows.end(),
            [this](const CandidateReport& row) {
                return row.backend == index_.selected_backend();
            }
        );
        if (previous_row == rows.end() || selected_row == rows.end()) {
            throw std::logic_error("adaptive leaderboard is incomplete");
        }
        const double denominator = std::max(std::abs(previous_row->score), 1e-12);
        const double improvement =
            (previous_row->score - selected_row->score) / denominator;
        decision_.attempted = true;
        decision_.previous = std::string(backend_name(previous_backend));
        decision_.previous_score = previous_row->score;
        decision_.selected_score = selected_row->score;
        decision_.relative_improvement = improvement;
        if (
            index_.selected_backend() != previous_backend
            && improvement + 1e-12 < policy_.minimum_relative_improvement
        ) {
            index_ = std::move(previous);
            decision_.switched = false;
            decision_.selected = decision_.previous;
            decision_.reason = "candidate improvement below deployment threshold";
            persist_after_decision();
            return false;
        }
        decision_.switched = index_.selected_backend() != previous_backend;
        decision_.selected = std::string(index_.selected_name());
        decision_.reason = decision_.switched
            ? "candidate passed deployment threshold"
            : "current backend remains optimal";
        persist_after_decision();
        return decision_.switched;
    }

    void save_profile() const {
        if (policy_.profile_path.empty()) {
            throw std::logic_error("profile_path is not configured");
        }
        index_.save_profile(policy_.profile_path);
    }

    bool load_profile(bool merge = false) {
        if (policy_.profile_path.empty()) {
            throw std::logic_error("profile_path is not configured");
        }
        const bool loaded = index_.load_profile(policy_.profile_path, merge);
        if (loaded) {
            last_attempt_weight_ = 0.0;
            decision_ = {};
            decision_.observed_operations = index_.observed_weight();
        }
        return loaded;
    }

    std::string explain() const {
        std::ostringstream output;
        output << "selected=" << index_.selected_name()
               << " observed=" << index_.observed_weight()
               << " attempted=" << std::boolalpha << decision_.attempted
               << " switched=" << decision_.switched
               << " improvement=" << std::setprecision(6)
               << 100.0 * decision_.relative_improvement << "%"
               << " reason=\"" << decision_.reason << "\"";
        return output.str();
    }

    std::size_t size() const { return values_size_; }
    std::string_view selected_name() const { return index_.selected_name(); }
    bool optimized() const { return index_.optimized(); }
    double observed_operations() const { return index_.observed_weight(); }
    const AutoTuneDecision& decision() const { return decision_; }
    const std::vector<CandidateReport>& leaderboard() const {
        return index_.leaderboard();
    }

private:
    AdaptiveIndex index_;
    AutoTunePolicy policy_;
    OptimizeOptions options_;
    AutoTuneDecision decision_;
    double last_attempt_weight_ = 0.0;
    std::size_t values_size_ = 0;

    static std::vector<double> to_double(const std::vector<T>& values) {
        if (
            values.size()
            > static_cast<std::size_t>(std::numeric_limits<int>::max())
        ) {
            throw std::length_error("adaptive_array exceeds key range");
        }
        std::vector<double> result;
        result.reserve(values.size());
        for (const T value : values) result.push_back(static_cast<double>(value));
        return result;
    }

    void validate_policy() {
        if (
            policy_.warmup_operations == 0 || policy_.check_interval == 0
            || !std::isfinite(policy_.minimum_tv_drift)
            || policy_.minimum_tv_drift < 0.0
            || policy_.minimum_tv_drift > 1.0
            || !std::isfinite(policy_.minimum_relative_improvement)
            || policy_.minimum_relative_improvement < 0.0
        ) {
            throw std::invalid_argument("invalid auto-tune policy");
        }
    }

    int internal_key(int position) const {
        if (position < 0 || static_cast<std::size_t>(position) >= values_size_) {
            throw std::out_of_range("adaptive_array position out of range");
        }
        return position + 1;
    }

    void validate_half_open_range(int first, int last) const {
        if (
            first < 0 || last <= first
            || static_cast<std::size_t>(last) > values_size_
        ) {
            throw std::out_of_range("invalid adaptive_array range");
        }
    }

    void automatic_maintenance() {
        if (policy_.automatic_maintenance) maintenance();
    }

    void persist_after_decision() const {
        if (!policy_.profile_path.empty()) {
            index_.save_profile(policy_.profile_path);
        }
    }
};

template <class T = double>
using AdaptiveArray = adaptive_array<T>;

}  // namespace certigap
#include <optional>
#include <set>


namespace certigap {

enum class TrackingOperationKind { Get, Range, Update };

struct TrackingOperation {
    TrackingOperationKind kind = TrackingOperationKind::Get;
    int left = 1;
    int right = 1;
    double value = 0.0;

    static TrackingOperation get(int key) {
        return {TrackingOperationKind::Get, key, key, 0.0};
    }

    static TrackingOperation range(int left, int right) {
        return {TrackingOperationKind::Range, left, right, 0.0};
    }

    static TrackingOperation update(int key, double value) {
        return {TrackingOperationKind::Update, key, key, value};
    }
};

struct TrackingCostModel {
    double array_unit_cost = 1.0;
    double prefix_unit_cost = 1.0;
    double fenwick_unit_cost = 1.0;
    double sqrt_unit_cost = 1.0;
    double segment_tree_unit_cost = 1.0;
    double sparse_unit_cost = 1.0;
};

struct TrackingPolicyCpp {
    double migration_cost_units = 8.0;
    int max_comparator_switches = 4;
    Backend initial_backend = Backend::SortedArray;
    std::vector<Backend> backends;
    std::vector<std::vector<double>> migration_matrix;
    TrackingCostModel costs;
    bool record_history = true;
};

struct TrackingStepCpp {
    TrackingOperation operation;
    std::vector<double> service_costs;
    std::vector<double> work_function;
    Backend previous = Backend::SortedArray;
    Backend selected = Backend::SortedArray;
    bool switched = false;
    double migration_cost = 0.0;
    double service_cost = 0.0;
    double cumulative_cost = 0.0;
};

struct TrackingOracleCpp {
    double cost = 0.0;
    int switches = 0;
    std::vector<Backend> path;
};

struct TrackingExplanationCpp {
    Backend selected = Backend::SortedArray;
    std::size_t operations = 0;
    std::size_t switches = 0;
    double cumulative_cost = 0.0;
    bool migration_is_metric = false;
    int wfa_competitive_factor = 0;
};

namespace detail {

inline bool tracking_supported_backend(Backend backend) {
    return backend == Backend::SortedArray
        || backend == Backend::PrefixSum
        || backend == Backend::Fenwick
        || backend == Backend::SqrtDecomposition
        || backend == Backend::SegmentTree
        || backend == Backend::SparseTable;
}

inline std::vector<Backend> default_tracking_backends(Aggregate aggregate) {
    if (aggregate == Aggregate::Sum) {
        return {
            Backend::SortedArray,
            Backend::PrefixSum,
            Backend::Fenwick,
            Backend::SqrtDecomposition,
            Backend::SegmentTree,
        };
    }
    return {
        Backend::SortedArray,
        Backend::SqrtDecomposition,
        Backend::SegmentTree,
        Backend::SparseTable,
    };
}

inline int tracking_fenwick_prefix_steps(int key) {
    int steps = 0;
    while (key > 0) {
        ++steps;
        key -= key & -key;
    }
    return steps;
}

inline int tracking_fenwick_update_steps(int key, int n) {
    int steps = 0;
    while (key <= n) {
        ++steps;
        key += key & -key;
    }
    return steps;
}

inline int tracking_segment_range_steps(int left, int right, int size) {
    left = size + left - 1;
    right = size + right;
    int steps = 0;
    while (left < right) {
        if (left & 1) {
            ++steps;
            ++left;
        }
        if (right & 1) {
            --right;
            ++steps;
        }
        left >>= 1;
        right >>= 1;
    }
    return std::max(1, steps);
}

inline int tracking_sqrt_range_steps(
    int left, int right, int block_size
) {
    int index = left - 1;
    int steps = 0;
    while (index < right && index % block_size != 0) {
        ++steps;
        ++index;
    }
    while (index + block_size <= right) {
        ++steps;
        index += block_size;
    }
    return steps + right - index;
}

inline std::size_t tracking_sparse_entries(std::size_t n) {
    std::size_t entries = 0;
    for (std::size_t width = 1; width <= n; width <<= 1) {
        entries += n - width + 1;
        if (width > n / 2) break;
    }
    return entries;
}

}  // namespace detail

inline std::vector<std::vector<double>> tracking_rebuild_metric(
    std::size_t n,
    const std::vector<Backend>& backends,
    double unit_scale = 1.0
) {
    if (n == 0 || !std::isfinite(unit_scale) || unit_scale <= 0.0) {
        throw std::invalid_argument("invalid rebuild metric parameters");
    }
    std::size_t power_of_two = 1;
    int height = 0;
    while (power_of_two < n) { power_of_two <<= 1; ++height; }
    const std::size_t block = std::max<std::size_t>(
        1, static_cast<std::size_t>(std::ceil(std::sqrt(n))));
    std::vector<double> build;
    build.reserve(backends.size());
    for (Backend backend : backends) {
        double units = static_cast<double>(n);
        if (backend == Backend::Fenwick) {
            units = static_cast<double>(n) * (height + 1);
        } else if (backend == Backend::SqrtDecomposition) {
            units = static_cast<double>(n + (n + block - 1) / block);
        } else if (backend == Backend::SegmentTree) {
            units = static_cast<double>(2 * power_of_two);
        } else if (backend == Backend::SparseTable) {
            units = static_cast<double>(detail::tracking_sparse_entries(n));
        } else if (!detail::tracking_supported_backend(backend)) {
            throw std::invalid_argument("unsupported rebuild metric backend");
        }
        build.push_back(units * unit_scale);
    }
    std::vector<std::vector<double>> metric(
        backends.size(), std::vector<double>(backends.size(), 0.0));
    for (std::size_t i = 0; i < backends.size(); ++i) {
        for (std::size_t j = 0; j < backends.size(); ++j) {
            if (i != j) metric[i][j] = std::max(build[i], build[j]);
        }
    }
    return metric;
}

class TrackingAutoIndexCpp {
public:
    explicit TrackingAutoIndexCpp(
        const std::vector<double>& values,
        Aggregate aggregate = Aggregate::Sum,
        TrackingPolicyCpp policy = {}
    )
        : values_(values), aggregate_(aggregate), policy_(std::move(policy)),
          runtime_(detail::ArrayRuntime(values, aggregate)) {
        validate_values();
        candidates_ = policy_.backends.empty()
            ? detail::default_tracking_backends(aggregate_)
            : policy_.backends;
        validate_candidates();
        initial_index_ = candidate_index(policy_.initial_backend);
        selected_index_ = initial_index_;
        build_migration_matrix();
        work_.resize(candidates_.size());
        service_scratch_.resize(candidates_.size());
        work_scratch_.resize(candidates_.size());
        for (std::size_t index = 0; index < candidates_.size(); ++index) {
            work_[index] = distance(initial_index_, index);
        }
        rebuild_runtime(candidates_[selected_index_]);
    }

    double get(int key) {
        const auto result = execute(TrackingOperation::get(key));
        return *result;
    }

    double range_query(int left, int right) {
        const auto result = execute(TrackingOperation::range(left, right));
        return *result;
    }

    void point_update(int key, double value) {
        execute(TrackingOperation::update(key, value));
    }

    std::vector<std::optional<double>> run_batch(
        const std::vector<TrackingOperation>& operations
    ) {
        std::vector<std::optional<double>> results;
        results.reserve(operations.size());
        for (const auto& operation : operations) {
            results.push_back(execute(operation));
        }
        return results;
    }

    Backend selected_backend() const { return candidates_[selected_index_]; }
    std::string_view selected_name() const {
        return backend_name(selected_backend());
    }
    const std::vector<Backend>& candidates() const { return candidates_; }
    const std::vector<TrackingStepCpp>& history() const { return history_; }
    bool migration_is_metric() const { return migration_is_metric_; }

    std::size_t switch_count() const {
        return switches_;
    }

    double cumulative_cost() const {
        return cumulative_cost_;
    }

    int wfa_competitive_factor() const {
        return migration_is_metric_
            ? 2 * static_cast<int>(candidates_.size()) - 1
            : 0;
    }

    TrackingExplanationCpp explain() const {
        return {
            selected_backend(), operations_, switch_count(),
            cumulative_cost(), migration_is_metric_,
            wfa_competitive_factor(),
        };
    }

    TrackingOracleCpp exact_oracle(int max_switches) const {
        if (max_switches < 0) {
            throw std::invalid_argument("max_switches must be non-negative");
        }
        if (!policy_.record_history) {
            throw std::logic_error("exact oracle requires record_history=true");
        }
        const int horizon = static_cast<int>(history_.size());
        const int limit = std::min(max_switches, horizon);
        const std::size_t m = candidates_.size();
        const double infinity = std::numeric_limits<double>::infinity();
        const auto state = [limit](std::size_t candidate, int switches) {
            return candidate * static_cast<std::size_t>(limit + 1)
                + static_cast<std::size_t>(switches);
        };
        const std::size_t states = m * static_cast<std::size_t>(limit + 1);
        std::vector<double> previous(states, infinity);
        previous[state(initial_index_, 0)] = 0.0;
        std::vector<std::vector<std::size_t>> parents;
        parents.reserve(history_.size());
        for (const auto& step : history_) {
            std::vector<double> current(states, infinity);
            std::vector<std::size_t> parent(states, states);
            for (std::size_t target = 0; target < m; ++target) {
                for (int switches = 0; switches <= limit; ++switches) {
                    for (std::size_t prior = 0; prior < m; ++prior) {
                        const int changed = prior == target ? 0 : 1;
                        if (switches < changed) continue;
                        const std::size_t prior_state = state(
                            prior, switches - changed
                        );
                        const double value = previous[prior_state]
                            + distance(prior, target)
                            + step.service_costs[target];
                        const std::size_t target_state = state(target, switches);
                        if (value < current[target_state] - epsilon_) {
                            current[target_state] = value;
                            parent[target_state] = prior_state;
                        }
                    }
                }
            }
            previous = std::move(current);
            parents.push_back(std::move(parent));
        }
        std::size_t terminal = 0;
        for (std::size_t index = 1; index < states; ++index) {
            const int candidate = static_cast<int>(index / (limit + 1));
            const int switches = static_cast<int>(index % (limit + 1));
            const int best_candidate = static_cast<int>(terminal / (limit + 1));
            const int best_switches = static_cast<int>(terminal % (limit + 1));
            if (
                previous[index] < previous[terminal] - epsilon_
                || (
                    std::abs(previous[index] - previous[terminal]) <= epsilon_
                    && (switches < best_switches
                        || (switches == best_switches
                            && candidate < best_candidate))
                )
            ) terminal = index;
        }
        TrackingOracleCpp result;
        result.cost = previous[terminal];
        result.switches = static_cast<int>(terminal % (limit + 1));
        result.path.resize(history_.size());
        for (std::size_t time = history_.size(); time > 0; --time) {
            result.path[time - 1] = candidates_[terminal / (limit + 1)];
            terminal = parents[time - 1][terminal];
        }
        return result;
    }

    TrackingOracleCpp comparator_oracle() const {
        return exact_oracle(policy_.max_comparator_switches);
    }

    TrackingOracleCpp unrestricted_oracle() const {
        return exact_oracle(static_cast<int>(history_.size()));
    }

private:
    using Runtime = std::variant<
        detail::ArrayRuntime,
        detail::PrefixRuntime,
        detail::FenwickRuntime,
        detail::SqrtRuntime,
        detail::SegmentRuntime,
        detail::SparseRuntime
    >;

    static constexpr double epsilon_ = 1e-12;
    std::vector<double> values_;
    Aggregate aggregate_;
    TrackingPolicyCpp policy_;
    std::vector<Backend> candidates_;
    std::vector<std::vector<double>> migration_;
    std::vector<double> work_;
    std::vector<double> service_scratch_;
    std::vector<double> work_scratch_;
    std::vector<TrackingStepCpp> history_;
    Runtime runtime_;
    std::size_t initial_index_ = 0;
    std::size_t selected_index_ = 0;
    bool migration_is_metric_ = false;
    std::size_t operations_ = 0;
    std::size_t switches_ = 0;
    double cumulative_cost_ = 0.0;

    void validate_values() const {
        if (values_.empty()) throw std::invalid_argument("values must not be empty");
        if (values_.size() > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
            throw std::length_error("key universe exceeds int range");
        }
        for (double value : values_) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("values must be finite");
            }
        }
    }

    void validate_candidates() const {
        if (candidates_.empty()) {
            throw std::invalid_argument("tracking portfolio must not be empty");
        }
        std::set<Backend> unique;
        for (Backend backend : candidates_) {
            if (!detail::tracking_supported_backend(backend)) {
                throw std::invalid_argument("unsupported tracking backend");
            }
            if (!unique.insert(backend).second) {
                throw std::invalid_argument("tracking backends must be unique");
            }
            if (
                aggregate_ != Aggregate::Sum
                && (backend == Backend::PrefixSum || backend == Backend::Fenwick)
            ) throw std::invalid_argument("sum-only backend is infeasible");
            if (aggregate_ == Aggregate::Sum && backend == Backend::SparseTable) {
                throw std::invalid_argument("sparse table is infeasible for sum");
            }
        }
        validate_cost(policy_.costs.array_unit_cost);
        validate_cost(policy_.costs.prefix_unit_cost);
        validate_cost(policy_.costs.fenwick_unit_cost);
        validate_cost(policy_.costs.sqrt_unit_cost);
        validate_cost(policy_.costs.segment_tree_unit_cost);
        validate_cost(policy_.costs.sparse_unit_cost);
        if (policy_.max_comparator_switches < 0) {
            throw std::invalid_argument("max comparator switches must be non-negative");
        }
    }

    static void validate_cost(double value) {
        if (!std::isfinite(value) || value <= 0.0) {
            throw std::invalid_argument("unit costs must be finite and positive");
        }
    }

    std::size_t candidate_index(Backend backend) const {
        const auto found = std::find(candidates_.begin(), candidates_.end(), backend);
        if (found == candidates_.end()) {
            throw std::invalid_argument("initial backend is infeasible");
        }
        return static_cast<std::size_t>(found - candidates_.begin());
    }

    void build_migration_matrix() {
        const std::size_t m = candidates_.size();
        if (policy_.migration_matrix.empty()) {
            validate_cost(policy_.migration_cost_units);
            migration_.assign(m, std::vector<double>(m, policy_.migration_cost_units));
            for (std::size_t index = 0; index < m; ++index) {
                migration_[index][index] = 0.0;
            }
        } else {
            if (policy_.migration_matrix.size() != m) {
                throw std::invalid_argument("migration matrix size mismatch");
            }
            migration_ = policy_.migration_matrix;
            for (const auto& row : migration_) {
                if (row.size() != m) {
                    throw std::invalid_argument("migration matrix size mismatch");
                }
                for (double value : row) {
                    if (!std::isfinite(value) || value < 0.0) {
                        throw std::invalid_argument("migration costs must be finite and non-negative");
                    }
                }
            }
            for (std::size_t index = 0; index < m; ++index) {
                if (std::abs(migration_[index][index]) > epsilon_) {
                    throw std::invalid_argument("migration matrix diagonal must be zero");
                }
            }
        }
        migration_is_metric_ = true;
        for (std::size_t i = 0; i < m; ++i) {
            for (std::size_t j = 0; j < m; ++j) {
                if (i != j && migration_[i][j] <= 0.0) migration_is_metric_ = false;
                if (std::abs(migration_[i][j] - migration_[j][i]) > epsilon_) {
                    migration_is_metric_ = false;
                }
                for (std::size_t k = 0; k < m; ++k) {
                    if (migration_[i][k] > migration_[i][j] + migration_[j][k] + epsilon_) {
                        migration_is_metric_ = false;
                    }
                }
            }
        }
    }

    double distance(std::size_t from, std::size_t to) const {
        return migration_[from][to];
    }

    double unit_cost(Backend backend) const {
        if (backend == Backend::PrefixSum) return policy_.costs.prefix_unit_cost;
        if (backend == Backend::Fenwick) return policy_.costs.fenwick_unit_cost;
        if (backend == Backend::SqrtDecomposition) return policy_.costs.sqrt_unit_cost;
        if (backend == Backend::SegmentTree) return policy_.costs.segment_tree_unit_cost;
        if (backend == Backend::SparseTable) return policy_.costs.sparse_unit_cost;
        return policy_.costs.array_unit_cost;
    }

    double service_cost(Backend backend, const TrackingOperation& operation) const {
        const int n = static_cast<int>(values_.size());
        int cost = 1;
        if (backend == Backend::SortedArray) {
            cost = operation.kind == TrackingOperationKind::Range
                ? operation.right - operation.left + 1 : 1;
        } else if (backend == Backend::PrefixSum) {
            if (operation.kind == TrackingOperationKind::Update) {
                cost = n - operation.left + 2;
            } else if (operation.kind == TrackingOperationKind::Range) {
                cost = operation.left == 1 ? 1 : 2;
            }
        } else if (backend == Backend::Fenwick) {
            if (operation.kind == TrackingOperationKind::Update) {
                cost = detail::tracking_fenwick_update_steps(operation.left, n);
            } else if (operation.kind == TrackingOperationKind::Range) {
                cost = std::max(1,
                    detail::tracking_fenwick_prefix_steps(operation.right)
                    + detail::tracking_fenwick_prefix_steps(operation.left - 1));
            }
        } else if (backend == Backend::SqrtDecomposition) {
            const int block = std::max(1, static_cast<int>(std::ceil(std::sqrt(n))));
            if (operation.kind == TrackingOperationKind::Update) {
                const int start = ((operation.left - 1) / block) * block;
                cost = std::min(block, n - start) + 1;
            } else if (operation.kind == TrackingOperationKind::Range) {
                cost = detail::tracking_sqrt_range_steps(
                    operation.left, operation.right, block);
            }
        } else if (backend == Backend::SegmentTree) {
            int size = 1;
            int height = 0;
            while (size < n) { size <<= 1; ++height; }
            if (operation.kind == TrackingOperationKind::Update) cost = height + 1;
            else if (operation.kind == TrackingOperationKind::Range) {
                cost = detail::tracking_segment_range_steps(
                    operation.left, operation.right, size);
            }
        } else if (backend == Backend::SparseTable) {
            if (operation.kind == TrackingOperationKind::Update) {
                cost = static_cast<int>(detail::tracking_sparse_entries(values_.size()) + 1);
            } else if (operation.kind == TrackingOperationKind::Range) cost = 2;
        }
        return cost * unit_cost(backend);
    }

    void validate_operation(const TrackingOperation& operation) const {
        const int n = static_cast<int>(values_.size());
        if (operation.left < 1 || operation.left > n) {
            throw std::out_of_range("tracking key out of range");
        }
        if (operation.kind == TrackingOperationKind::Range
            && (operation.right < operation.left || operation.right > n)) {
            throw std::out_of_range("invalid tracking range");
        }
        if (operation.kind == TrackingOperationKind::Update
            && !std::isfinite(operation.value)) {
            throw std::invalid_argument("update value must be finite");
        }
    }

    void rebuild_runtime(Backend backend) {
        if (backend == Backend::SortedArray) {
            runtime_.emplace<detail::ArrayRuntime>(values_, aggregate_);
        } else if (backend == Backend::PrefixSum) {
            runtime_.emplace<detail::PrefixRuntime>(values_);
        } else if (backend == Backend::Fenwick) {
            runtime_.emplace<detail::FenwickRuntime>(values_);
        } else if (backend == Backend::SqrtDecomposition) {
            runtime_.emplace<detail::SqrtRuntime>(values_, aggregate_);
        } else if (backend == Backend::SegmentTree) {
            runtime_.emplace<detail::SegmentRuntime>(values_, aggregate_);
        } else {
            runtime_.emplace<detail::SparseRuntime>(values_, aggregate_);
        }
    }

    std::optional<double> execute(const TrackingOperation& operation) {
        validate_operation(operation);
        const std::size_t m = candidates_.size();
        for (std::size_t index = 0; index < m; ++index) {
            service_scratch_[index] = service_cost(candidates_[index], operation);
            work_scratch_[index] = std::numeric_limits<double>::infinity();
        }
        for (std::size_t target = 0; target < m; ++target) {
            for (std::size_t prior = 0; prior < m; ++prior) {
                work_scratch_[target] = std::min(
                    work_scratch_[target], work_[prior] + distance(prior, target));
            }
            work_scratch_[target] += service_scratch_[target];
        }
        std::size_t next_selected = 0;
        for (std::size_t index = 1; index < m; ++index) {
            const double score = work_scratch_[index] + distance(selected_index_, index);
            const double best = work_scratch_[next_selected]
                + distance(selected_index_, next_selected);
            if (score < best - epsilon_) next_selected = index;
        }
        const std::size_t previous = selected_index_;
        const double migration = distance(previous, next_selected);
        if (next_selected != previous) rebuild_runtime(candidates_[next_selected]);
        selected_index_ = next_selected;
        std::optional<double> result;
        if (operation.kind == TrackingOperationKind::Get) {
            result = std::visit(
                [&operation](const auto& runtime) { return runtime.get(operation.left); },
                runtime_);
        } else if (operation.kind == TrackingOperationKind::Range) {
            result = std::visit(
                [&operation](const auto& runtime) {
                    return runtime.range_query(operation.left, operation.right);
                }, runtime_);
        } else {
            std::visit(
                [&operation](auto& runtime) {
                    runtime.point_update(operation.left, operation.value);
                }, runtime_);
            values_[operation.left - 1] = operation.value;
        }
        cumulative_cost_ += migration + service_scratch_[next_selected];
        ++operations_;
        if (previous != next_selected) ++switches_;
        if (policy_.record_history) {
            history_.push_back({
                operation, service_scratch_, work_scratch_, candidates_[previous],
                candidates_[next_selected], previous != next_selected,
                migration, service_scratch_[next_selected], cumulative_cost_,
            });
        }
        work_.swap(work_scratch_);
        return result;
    }
};

using TrackingPolicy = TrackingPolicyCpp;
using TrackingStep = TrackingStepCpp;
using TrackingOracle = TrackingOracleCpp;
using TrackingExplanation = TrackingExplanationCpp;
using TrackingAutoIndex = TrackingAutoIndexCpp;

}  // namespace certigap
