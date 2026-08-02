#pragma once

#include "certigap_adaptive.hpp"

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
