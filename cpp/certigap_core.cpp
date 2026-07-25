#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <sstream>
#include <string>
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
