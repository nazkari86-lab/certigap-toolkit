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

class PrefixBlockIndex {
public:
    PrefixBlockIndex(
        std::vector<double> values,
        std::vector<int> boundaries
    )
        : values_(std::move(values)),
          boundaries_(std::move(boundaries)) {
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
        block_for_key_.assign(values_.size(), 0);
        local_prefix_.assign(values_.size(), 0.0);
        block_prefix_.assign(boundaries_.size(), 0.0);
        int left = 1;
        double blocks_total = 0.0;
        for (
            int block = 0;
            block < static_cast<int>(boundaries_.size());
            ++block
        ) {
            double local_total = 0.0;
            for (int key = left; key <= boundaries_[block]; ++key) {
                const double value = values_[key - 1];
                if (!std::isfinite(value)) {
                    throw std::invalid_argument("values must be finite");
                }
                block_for_key_[key - 1] = block;
                local_total += value;
                local_prefix_[key - 1] = local_total;
            }
            blocks_total += local_total;
            block_prefix_[block] = blocks_total;
            left = boundaries_[block] + 1;
        }
    }

    double get(int key) const {
        validate_key(key);
        return values_[key - 1];
    }

    double range_query(int left, int right) const {
        validate_range(left, right);
        const int left_block = block_for_key_[left - 1];
        const int right_block = block_for_key_[right - 1];
        if (left_block == right_block) {
            return local_range(left_block, left, right);
        }
        double result = local_range(
            left_block, left, boundaries_[left_block]
        );
        if (right_block > left_block + 1) {
            result += block_prefix_[right_block - 1]
                - block_prefix_[left_block];
        }
        const int right_start =
            right_block == 0 ? 1 : boundaries_[right_block - 1] + 1;
        return result + local_range(right_block, right_start, right);
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("value must be finite");
        }
        const double delta = value - values_[key - 1];
        if (delta == 0.0) return;
        values_[key - 1] = value;
        const int block = block_for_key_[key - 1];
        for (int index = key - 1; index < boundaries_[block]; ++index) {
            local_prefix_[index] += delta;
        }
        for (
            int index = block;
            index < static_cast<int>(block_prefix_.size());
            ++index
        ) {
            block_prefix_[index] += delta;
        }
    }

    const std::vector<int>& boundaries() const { return boundaries_; }
    std::size_t memory_slots() const {
        return 3 * values_.size() + 2 * boundaries_.size();
    }

private:
    std::vector<double> values_;
    std::vector<int> boundaries_;
    std::vector<int> block_for_key_;
    std::vector<double> local_prefix_;
    std::vector<double> block_prefix_;

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

    double local_range(int block, int left, int right) const {
        const int block_start =
            block == 0 ? 1 : boundaries_[block - 1] + 1;
        const double before =
            left == block_start ? 0.0 : local_prefix_[left - 2];
        return local_prefix_[right - 1] - before;
    }
};

}  // namespace certigap
