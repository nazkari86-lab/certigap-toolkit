#pragma once

#include <algorithm>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <vector>


class CertiRangeSum {
public:
    template <class RoutingNode>
    CertiRangeSum(
        const std::shared_ptr<RoutingNode>& routing,
        const std::vector<double>& values,
        int max_depth
    ) : values_(values), max_depth_(max_depth) {
        if (!routing || values_.empty()) throw std::invalid_argument("non-empty routing tree and values required");
        int minimum = minimum_height(static_cast<int>(values_.size()));
        if (max_depth_ < minimum) throw std::invalid_argument("max_depth is infeasible");
        nodes_.reserve(2 * values_.size() - 1);
        root_ = build(routing, 1, static_cast<int>(values_.size()), max_depth_);
    }

    double get(int key) const {
        validate_key(key);
        int index = root_;
        while (!nodes_[index].leaf()) {
            index = key <= nodes_[index].threshold ? nodes_[index].left_child : nodes_[index].right_child;
        }
        return nodes_[index].aggregate;
    }

    double range_sum(int left, int right) const {
        if (left < 1 || right < left || right > static_cast<int>(values_.size())) {
            throw std::out_of_range("invalid range");
        }
        return range_sum(root_, left, right);
    }

    void point_update(int key, double value) {
        validate_key(key);
        if (!std::isfinite(value)) throw std::invalid_argument("value must be finite");
        values_[key - 1] = value;
        point_update(root_, key, value);
    }

    int height() const { return height(root_); }
    int node_count() const { return static_cast<int>(nodes_.size()); }
    int query_depth(int key) const {
        validate_key(key);
        int index = root_;
        int depth = 0;
        while (!nodes_[index].leaf()) {
            index = key <= nodes_[index].threshold ? nodes_[index].left_child : nodes_[index].right_child;
            ++depth;
        }
        return depth;
    }

private:
    struct RangeNode {
        int left = 0;
        int right = 0;
        int threshold = 0;
        int left_child = -1;
        int right_child = -1;
        double aggregate = 0.0;
        bool leaf() const { return left == right; }
    };

    std::vector<RangeNode> nodes_;
    std::vector<double> values_;
    int root_ = -1;
    int max_depth_ = 0;

    static int minimum_height(int size) {
        int height = 0;
        int capacity = 1;
        while (capacity < size) {
            capacity <<= 1;
            ++height;
        }
        return height;
    }

    void validate_key(int key) const {
        if (key < 1 || key > static_cast<int>(values_.size())) throw std::out_of_range("key out of range");
    }

    int append(RangeNode node) {
        nodes_.push_back(node);
        return static_cast<int>(nodes_.size()) - 1;
    }

    int build_balanced(int left, int right) {
        if (left == right) {
            return append({left, right, left, -1, -1, values_[left - 1]});
        }
        int threshold = left + (right - left) / 2;
        int index = append({left, right, threshold, -1, -1, 0.0});
        int left_child = build_balanced(left, threshold);
        int right_child = build_balanced(threshold + 1, right);
        nodes_[index].left_child = left_child;
        nodes_[index].right_child = right_child;
        nodes_[index].aggregate = nodes_[left_child].aggregate + nodes_[right_child].aggregate;
        return index;
    }

    template <class RoutingNode>
    int build(const std::shared_ptr<RoutingNode>& routing, int left, int right, int remaining_depth) {
        if (!routing || routing->l != left || routing->r != right) {
            throw std::invalid_argument("routing interval mismatch");
        }
        if (left == right) {
            return append({left, right, left, -1, -1, values_[left - 1]});
        }
        if (routing->is_leaf) return build_balanced(left, right);
        int threshold = routing->threshold;
        if (threshold < left || threshold >= right) throw std::invalid_argument("invalid routing threshold");
        bool fits = remaining_depth > 0
            && minimum_height(threshold - left + 1) <= remaining_depth - 1
            && minimum_height(right - threshold) <= remaining_depth - 1;
        if (!fits) return build_balanced(left, right);
        int index = append({left, right, threshold, -1, -1, 0.0});
        int left_child = build(routing->left, left, threshold, remaining_depth - 1);
        int right_child = build(routing->right, threshold + 1, right, remaining_depth - 1);
        nodes_[index].left_child = left_child;
        nodes_[index].right_child = right_child;
        nodes_[index].aggregate = nodes_[left_child].aggregate + nodes_[right_child].aggregate;
        return index;
    }

    double range_sum(int index, int query_left, int query_right) const {
        const auto& node = nodes_[index];
        if (query_right < node.left || node.right < query_left) return 0.0;
        if (query_left <= node.left && node.right <= query_right) return node.aggregate;
        return range_sum(node.left_child, query_left, query_right)
            + range_sum(node.right_child, query_left, query_right);
    }

    double point_update(int index, int key, double value) {
        auto& node = nodes_[index];
        if (node.leaf()) {
            node.aggregate = value;
            return value;
        }
        if (key <= node.threshold) point_update(node.left_child, key, value);
        else point_update(node.right_child, key, value);
        node.aggregate = nodes_[node.left_child].aggregate + nodes_[node.right_child].aggregate;
        return node.aggregate;
    }

    int height(int index) const {
        const auto& node = nodes_[index];
        if (node.leaf()) return 0;
        return 1 + std::max(height(node.left_child), height(node.right_child));
    }
};
