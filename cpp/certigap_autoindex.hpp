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
    Fenwick,
    SegmentTree,
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
        if constexpr (Config::kBackend == Backend::Fenwick) {
            static_assert(
                Config::kAggregate == Aggregate::Sum,
                "Fenwick generated backend supports sum only"
            );
            fenwick_.assign(values_.size() + 1, 0.0);
            for (int key = 1; key <= static_cast<int>(values_.size()); ++key) {
                fenwick_add(key, values_[key - 1]);
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
        } else if constexpr (Config::kBackend == Backend::Fenwick) {
            return fenwick_prefix(right) - fenwick_prefix(left - 1);
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
        } else {
            return certi_range(0, left, right);
        }
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("value must be finite");
        }
        if constexpr (Config::kBackend == Backend::Fenwick) {
            double delta = value - values_[key - 1];
            values_[key - 1] = value;
            fenwick_add(key, delta);
        } else if constexpr (Config::kBackend == Backend::SegmentTree) {
            values_[key - 1] = value;
            int index = segment_size_ + key - 1;
            segment_[index] = value;
            for (index >>= 1; index > 0; index >>= 1) {
                segment_[index] = combine(
                    segment_[2 * index], segment_[2 * index + 1]
                );
            }
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
    std::vector<double> fenwick_;
    std::vector<double> segment_;
    std::vector<double> certi_aggregate_;
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
