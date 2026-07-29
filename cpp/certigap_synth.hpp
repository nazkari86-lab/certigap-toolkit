#pragma once

#include "certigap_autoindex.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>
#include <vector>

namespace certigap {

class VariableBlockIndex {
public:
    VariableBlockIndex(
        std::vector<double> values,
        std::vector<int> boundaries,
        Aggregate aggregate = Aggregate::Sum
    )
        : values_(std::move(values)),
          boundaries_(std::move(boundaries)),
          aggregate_(aggregate) {
        if (
            values_.empty()
            || boundaries_.empty()
            || boundaries_.front() < 1
            || boundaries_.back() != static_cast<int>(values_.size())
            || !std::is_sorted(boundaries_.begin(), boundaries_.end())
            || std::adjacent_find(
                boundaries_.begin(), boundaries_.end()
            ) != boundaries_.end()
        ) {
            throw std::invalid_argument(
                "boundaries must strictly partition all values"
            );
        }
        for (double value : values_) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument("values must be finite");
            }
        }
        block_for_key_.assign(values_.size(), 0);
        aggregates_.reserve(boundaries_.size());
        int left = 1;
        for (
            int block = 0;
            block < static_cast<int>(boundaries_.size());
            ++block
        ) {
            const int right = boundaries_[block];
            for (int key = left; key <= right; ++key) {
                block_for_key_[key - 1] = block;
            }
            aggregates_.push_back(aggregate_range(left, right));
            left = right + 1;
        }
    }

    double get(int key) const {
        validate_key(key);
        return values_[key - 1];
    }

    double range_query(int left, int right) const {
        validate_range(left, right);
        double result = identity();
        int block = block_for_key_[left - 1];
        int block_left =
            block == 0 ? 1 : boundaries_[block - 1] + 1;
        while (
            block < static_cast<int>(boundaries_.size())
            && block_left <= right
        ) {
            const int block_right = boundaries_[block];
            if (left <= block_left && block_right <= right) {
                result = combine(result, aggregates_[block]);
            } else {
                for (
                    int key = std::max(left, block_left);
                    key <= std::min(right, block_right);
                    ++key
                ) {
                    result = combine(result, values_[key - 1]);
                }
            }
            ++block;
            block_left = block_right + 1;
        }
        return result;
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("value must be finite");
        }
        const int block = block_for_key_[key - 1];
        const double old = values_[key - 1];
        values_[key - 1] = value;
        if (aggregate_ == Aggregate::Sum) {
            aggregates_[block] += value - old;
        } else {
            const int left =
                block == 0 ? 1 : boundaries_[block - 1] + 1;
            aggregates_[block] = aggregate_range(
                left, boundaries_[block]
            );
        }
    }

    const std::vector<int>& boundaries() const { return boundaries_; }
    std::size_t memory_slots() const {
        return 2 * values_.size()
            + aggregates_.size()
            + boundaries_.size();
    }

private:
    std::vector<double> values_;
    std::vector<int> boundaries_;
    Aggregate aggregate_;
    std::vector<int> block_for_key_;
    std::vector<double> aggregates_;

    void validate_key(int key) const {
        if (key < 1 || key > static_cast<int>(values_.size())) {
            throw std::out_of_range("key out of range");
        }
    }

    void validate_range(int left, int right) const {
        if (
            left < 1
            || right < left
            || right > static_cast<int>(values_.size())
        ) {
            throw std::out_of_range("invalid range");
        }
    }

    double identity() const {
        if (aggregate_ == Aggregate::Sum) return 0.0;
        if (aggregate_ == Aggregate::Min) {
            return std::numeric_limits<double>::infinity();
        }
        return -std::numeric_limits<double>::infinity();
    }

    double combine(double left, double right) const {
        if (aggregate_ == Aggregate::Sum) return left + right;
        if (aggregate_ == Aggregate::Min) return std::min(left, right);
        return std::max(left, right);
    }

    double aggregate_range(int left, int right) const {
        double result = identity();
        for (int key = left; key <= right; ++key) {
            result = combine(result, values_[key - 1]);
        }
        return result;
    }
};

}  // namespace certigap
