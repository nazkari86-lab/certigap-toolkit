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
