#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <set>
#include <vector>

struct Node {
    int l = 0;
    int r = 0;
    int threshold = -1;
    bool is_leaf = true;
    std::shared_ptr<Node> left;
    std::shared_ptr<Node> right;
};

struct State {
    double avg_cost = 0.0;
    int max_cost = 0;
    std::shared_ptr<Node> tree;
};

static constexpr double EPS = 1e-12;

static int interval_cost(int size) {
    if (size <= 1) return 0;
    int p = 0;
    int x = 1;
    while (x < size) {
        x <<= 1;
        ++p;
    }
    return p;
}

class Solver {
public:
    Solver(std::vector<double> weights, int budget, double eta)
        : n_(static_cast<int>(weights.size()) - 1), budget_(budget), eta_(eta), p_(std::move(weights)) {
        pref_.assign(n_ + 1, 0.0);
        for (int i = 1; i <= n_; ++i) pref_[i] = pref_[i - 1] + p_[i];
        memo_.assign(
            n_ + 2,
            std::vector<std::vector<std::vector<State>>>(
                n_ + 2,
                std::vector<std::vector<State>>(budget_ + 1)
            )
        );
        vis_.assign(
            n_ + 2,
            std::vector<std::vector<bool>>(n_ + 2, std::vector<bool>(budget_ + 1, false))
        );
    }

    State best_root() {
        auto &frontier = solve(1, n_, budget_);
        auto best = frontier.front();
        double best_value = objective(best);
        for (const auto &state : frontier) {
            double cur = objective(state);
            if (cur + EPS < best_value || (std::abs(cur - best_value) <= EPS && state.max_cost < best.max_cost)) {
                best = state;
                best_value = cur;
            }
        }
        return best;
    }

    std::vector<int> per_key_costs(const std::shared_ptr<Node>& tree) const {
        std::vector<int> costs(n_ + 1, 0);
        fill_costs(tree, 0, costs);
        return costs;
    }

    double eta() const { return eta_; }
    int n() const { return n_; }

private:
    int n_;
    int budget_;
    double eta_;
    std::vector<double> p_;
    std::vector<double> pref_;
    std::vector<std::vector<std::vector<std::vector<State>>>> memo_;
    std::vector<std::vector<std::vector<bool>>> vis_;

    double mass(int l, int r) const { return pref_[r] - pref_[l - 1]; }

    double objective(const State& s) const {
        return (1.0 - eta_) * s.avg_cost + eta_ * s.max_cost;
    }

    static std::shared_ptr<Node> make_leaf(int l, int r) {
        auto node = std::make_shared<Node>();
        node->l = l;
        node->r = r;
        node->is_leaf = true;
        return node;
    }

    static std::shared_ptr<Node> make_split(int l, int r, int k, std::shared_ptr<Node> left, std::shared_ptr<Node> right) {
        auto node = std::make_shared<Node>();
        node->l = l;
        node->r = r;
        node->threshold = k;
        node->is_leaf = false;
        node->left = std::move(left);
        node->right = std::move(right);
        return node;
    }

    static std::vector<State> compress(std::vector<State> states) {
        std::map<int, State> best_by_max;
        for (auto &st : states) {
            auto it = best_by_max.find(st.max_cost);
            if (it == best_by_max.end() || st.avg_cost + EPS < it->second.avg_cost) {
                best_by_max[st.max_cost] = st;
            }
        }
        std::vector<State> ordered;
        for (auto &item : best_by_max) ordered.push_back(item.second);
        std::vector<State> res;
        double best_avg = 1e100;
        for (auto &st : ordered) {
            if (st.avg_cost + EPS < best_avg) {
                res.push_back(st);
                best_avg = st.avg_cost;
            }
        }
        return res;
    }

    std::vector<State>& solve(int l, int r, int b) {
        if (vis_[l][r][b]) return memo_[l][r][b];
        vis_[l][r][b] = true;

        std::vector<State> states;
        int sz = r - l + 1;
        int leaf_cost = interval_cost(sz);
        states.push_back({mass(l, r) * leaf_cost, leaf_cost, make_leaf(l, r)});

        if (b > 0 && l < r) {
            double total_mass = mass(l, r);
            for (int k = l; k < r; ++k) {
                for (int bl = 0; bl <= b - 1; ++bl) {
                    int br = b - 1 - bl;
                    auto &left_states = solve(l, k, bl);
                    auto &right_states = solve(k + 1, r, br);
                    for (const auto &ls : left_states) {
                        for (const auto &rs : right_states) {
                            states.push_back({
                                total_mass + ls.avg_cost + rs.avg_cost,
                                1 + std::max(ls.max_cost, rs.max_cost),
                                make_split(l, r, k, ls.tree, rs.tree)
                            });
                        }
                    }
                }
            }
        }

        memo_[l][r][b] = compress(std::move(states));
        return memo_[l][r][b];
    }

    static void fill_costs(const std::shared_ptr<Node>& node, int depth, std::vector<int>& out) {
        if (node->is_leaf) {
            int cost = depth + interval_cost(node->r - node->l + 1);
            for (int i = node->l; i <= node->r; ++i) out[i] = cost;
            return;
        }
        fill_costs(node->left, depth + 1, out);
        fill_costs(node->right, depth + 1, out);
    }
};

struct FastLeaf { int l; int r; int depth; };
struct FastCandidate {
    std::vector<FastLeaf> leaves;
    double average;
    int maximum;
    std::shared_ptr<Node> tree;
};

static void dump_tree(const std::shared_ptr<Node>& node, std::ostringstream& out);

// Return a fresh immutable path from root to the leaf being split.  Keeping
// this tree alongside the beam state makes the heuristic result executable.
static std::shared_ptr<Node> replace_leaf_with_split(
    const std::shared_ptr<Node>& node, int l, int r, int threshold
) {
    if (node->is_leaf) {
        if (node->l != l || node->r != r) return node;
        auto left = std::make_shared<Node>();
        left->l = l; left->r = threshold;
        auto right = std::make_shared<Node>();
        right->l = threshold + 1; right->r = r;
        auto split = std::make_shared<Node>();
        split->l = l; split->r = r; split->threshold = threshold; split->is_leaf = false;
        split->left = std::move(left); split->right = std::move(right);
        return split;
    }
    auto left = replace_leaf_with_split(node->left, l, r, threshold);
    auto right = replace_leaf_with_split(node->right, l, r, threshold);
    if (left == node->left && right == node->right) return node;
    auto copy = std::make_shared<Node>();
    copy->l = node->l; copy->r = node->r; copy->threshold = node->threshold; copy->is_leaf = false;
    copy->left = std::move(left); copy->right = std::move(right);
    return copy;
}

static std::vector<int> pruned_thresholds(const std::vector<double>& pref, const FastLeaf& leaf, int limit) {
    std::set<int> points;
    int count = leaf.r - leaf.l;
    if (count <= limit) for (int k = leaf.l; k < leaf.r; ++k) points.insert(k);
    else {
        points.insert(leaf.l); points.insert(leaf.r - 1); points.insert((leaf.l + leaf.r - 1) / 2);
        for (int q = 1; q < limit - 2; ++q) points.insert(leaf.l + (q * count) / (limit - 1));
        double total = pref[leaf.r] - pref[leaf.l - 1];
        for (int q = 1; q < 8; ++q) {
            double target = pref[leaf.l - 1] + total * q / 8.0;
            auto it = std::lower_bound(pref.begin() + leaf.l, pref.begin() + leaf.r, target);
            if (it != pref.begin() + leaf.r) points.insert(static_cast<int>(it - pref.begin()));
        }
    }
    std::vector<int> out;
    for (int k : points) if (k >= leaf.l && k < leaf.r) out.push_back(k);
    return out;
}

static FastCandidate pruned_beam_solve(
    const std::vector<double>& normalized, int budget, double eta, int beam_width, int candidate_limit
) {
    int n = static_cast<int>(normalized.size()) - 1;
    std::vector<double> pref(n + 1, 0.0);
    for (int i = 1; i <= n; ++i) pref[i] = pref[i - 1] + normalized[i];
    auto cost = [](const FastLeaf& leaf) { return leaf.depth + interval_cost(leaf.r - leaf.l + 1); };
    auto root = std::make_shared<Node>(); root->l = 1; root->r = n;
    FastCandidate start{{{1, n, 0}}, static_cast<double>(interval_cost(n)), interval_cost(n), root};
    std::vector<FastCandidate> beam{start}; FastCandidate best = start;
    auto objective = [eta](const FastCandidate& c) { return (1.0 - eta) * c.average + eta * c.maximum; };
    for (int used = 0; used < budget; ++used) {
        std::vector<FastCandidate> next;
        for (const auto& candidate : beam) for (size_t index = 0; index < candidate.leaves.size(); ++index) {
            const auto& leaf = candidate.leaves[index];
            double old_mass = pref[leaf.r] - pref[leaf.l - 1]; int old_cost = cost(leaf);
            for (int k : pruned_thresholds(pref, leaf, candidate_limit)) {
                FastLeaf left{leaf.l, k, leaf.depth + 1}, right{k + 1, leaf.r, leaf.depth + 1};
                FastCandidate child = candidate; child.leaves[index] = left; child.leaves.insert(child.leaves.begin() + index + 1, right);
                child.tree = replace_leaf_with_split(candidate.tree, leaf.l, leaf.r, k);
                child.average += (pref[k] - pref[leaf.l - 1]) * cost(left) + (pref[leaf.r] - pref[k]) * cost(right) - old_mass * old_cost;
                child.maximum = 0; for (const auto& item : child.leaves) child.maximum = std::max(child.maximum, cost(item));
                next.push_back(std::move(child));
            }
        }
        if (next.empty()) break;
        std::sort(next.begin(), next.end(), [&](const FastCandidate& a, const FastCandidate& b) { return objective(a) < objective(b); });
        if (static_cast<int>(next.size()) > beam_width) next.resize(beam_width);
        beam = std::move(next); if (objective(beam.front()) + EPS < objective(best)) best = beam.front();
    }
    return best;
}

extern "C" void* certigap_pruned_beam_json(const double* weights, int n, int budget, double eta, int beam_width, int candidate_limit) {
    if (weights == nullptr || n <= 0 || budget < 0 || beam_width <= 0 || candidate_limit < 4 || !std::isfinite(eta) || eta < 0.0 || eta > 1.0) return nullptr;
    int requested_budget = budget;
    budget = std::min(budget, n - 1);
    std::vector<double> normalized(n + 1, 0.0);
    for (int i = 1; i <= n; ++i) { if (!std::isfinite(weights[i - 1]) || weights[i - 1] < 0.0) return nullptr; normalized[i] = normalized[i - 1] + weights[i - 1]; }
    if (normalized[n] <= 0.0) return nullptr;
    double total = normalized[n];
    for (int i = n; i >= 1; --i) normalized[i] = weights[i - 1] / total;
    auto cost = [](const FastLeaf& leaf) { return leaf.depth + interval_cost(leaf.r - leaf.l + 1); };
    FastCandidate best = pruned_beam_solve(normalized, budget, eta, beam_width, candidate_limit);
    auto objective = [eta](const FastCandidate& c) { return (1.0 - eta) * c.average + eta * c.maximum; };
    std::vector<int> per_key(n + 1, 0); for (const auto& leaf : best.leaves) for (int i = leaf.l; i <= leaf.r; ++i) per_key[i] = cost(leaf);
    std::ostringstream out; out.setf(std::ios::fixed); out.precision(6);
    out << "{\"n\":" << n << ",\"budget\":" << budget << ",\"requested_budget\":" << requested_budget << ",\"eta\":" << eta << ",\"average_cost\":" << best.average << ",\"max_cost\":" << best.maximum << ",\"objective\":" << objective(best) << ",\"beam_width\":" << beam_width << ",\"candidate_limit\":" << candidate_limit << ",\"per_key_costs\":[";
    for (int i = 1; i <= n; ++i) { if (i > 1) out << ","; out << per_key[i]; }
    out << "],\"tree\":"; dump_tree(best.tree, out); out << "}";
    std::string payload = out.str(); char* raw = static_cast<char*>(std::malloc(payload.size() + 1)); if (!raw) return nullptr; std::memcpy(raw, payload.c_str(), payload.size() + 1); return raw;
}

static void dump_tree(const std::shared_ptr<Node>& node, std::ostringstream& out) {
    if (node->is_leaf) {
        out << "{\"type\":\"leaf\",\"interval\":[" << node->l << "," << node->r << "]}";
        return;
    }
    out << "{\"type\":\"split\",\"interval\":[" << node->l << "," << node->r << "],";
    out << "\"threshold\":" << node->threshold << ",";
    out << "\"left\":";
    dump_tree(node->left, out);
    out << ",\"right\":";
    dump_tree(node->right, out);
    out << "}";
}

extern "C" void certigap_free_string(void* ptr) {
    std::free(ptr);
}

extern "C" void* certigap_fit_json(const double* weights, int n, int budget, double eta) {
    if (weights == nullptr || n <= 0 || budget < 0 || !std::isfinite(eta) || eta < 0.0 || eta > 1.0) return nullptr;
    int requested_budget = budget;
    budget = std::min(budget, n - 1);
    std::vector<double> p(n + 1, 0.0);
    double total = 0.0;
    for (int i = 0; i < n; ++i) {
        if (!std::isfinite(weights[i]) || weights[i] < 0.0) return nullptr;
        total += weights[i];
    }
    if (total <= 0.0) return nullptr;
    for (int i = 1; i <= n; ++i) p[i] = weights[i - 1] / total;

    Solver solver(p, budget, eta);
    State best = solver.best_root();
    auto costs = solver.per_key_costs(best.tree);

    std::ostringstream out;
    out.setf(std::ios::fixed);
    out.precision(6);
    out << "{";
    out << "\"n\":" << n << ",";
    out << "\"budget\":" << budget << ",";
    out << "\"requested_budget\":" << requested_budget << ",";
    out << "\"eta\":" << eta << ",";
    out << "\"average_cost\":" << best.avg_cost << ",";
    out << "\"max_cost\":" << best.max_cost << ",";
    out << "\"objective\":" << ((1.0 - eta) * best.avg_cost + eta * best.max_cost) << ",";
    out << "\"per_key_costs\":[";
    for (int i = 1; i <= n; ++i) {
        if (i > 1) out << ",";
        out << costs[i];
    }
    out << "],";
    out << "\"tree\":";
    dump_tree(best.tree, out);
    out << "}";

    std::string payload = out.str();
    char* raw = static_cast<char*>(std::malloc(payload.size() + 1));
    if (!raw) return nullptr;
    std::memcpy(raw, payload.c_str(), payload.size() + 1);
    return raw;
}
