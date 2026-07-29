#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <vector>

#include "certigap_core.cpp"

static std::shared_ptr<Node> leaf_node(int l, int r) {
    auto node = std::make_shared<Node>(); node->l = l; node->r = r; return node;
}

static std::shared_ptr<Node> split_node(int l, int r, int k, std::shared_ptr<Node> left, std::shared_ptr<Node> right) {
    auto node = std::make_shared<Node>();
    node->l = l; node->r = r; node->threshold = k; node->is_leaf = false;
    node->left = std::move(left); node->right = std::move(right);
    return node;
}

static std::shared_ptr<Node> balanced_tree(int l, int r, int budget) {
    if (l == r || budget <= 0) return leaf_node(l, r);
    int k = l + (r - l) / 2;
    int left_budget = (budget - 1) / 2;
    int right_budget = budget - 1 - left_budget;
    return split_node(l, r, k, balanced_tree(l, k, left_budget), balanced_tree(k + 1, r, right_budget));
}

static std::shared_ptr<Node> balanced_full_tree(int l, int r) {
    if (l == r) return leaf_node(l, r);
    int k = l + (r - l) / 2;
    return split_node(l, r, k, balanced_full_tree(l, k), balanced_full_tree(k + 1, r));
}

static std::shared_ptr<Node> weighted_tree(const std::vector<double>& prefix, int l, int r, int budget) {
    if (l == r || budget <= 0) return leaf_node(l, r);
    double half = (prefix[l - 1] + prefix[r]) / 2.0;
    int k = static_cast<int>(std::lower_bound(prefix.begin() + l, prefix.begin() + r, half) - prefix.begin());
    k = std::max(l, std::min(k, r - 1));
    double left_mass = prefix[k] - prefix[l - 1];
    double total_mass = prefix[r] - prefix[l - 1];
    int left_budget = std::min(budget - 1, static_cast<int>(std::llround((budget - 1) * left_mass / total_mass)));
    int right_budget = budget - 1 - left_budget;
    return split_node(
        l, r, k,
        weighted_tree(prefix, l, k, left_budget),
        weighted_tree(prefix, k + 1, r, right_budget)
    );
}

static int route_fixed_rounds(const std::shared_ptr<Node>& root, int key) {
    const Node* node = root.get();
    while (!node->is_leaf) node = key <= node->threshold ? node->left.get() : node->right.get();
    int size = node->r - node->l + 1;
    int rounds = interval_cost(size);
    std::uint64_t low = 0, high = (std::uint64_t{1} << rounds) - 1;
    for (int step = 0; step < rounds; ++step) {
        std::uint64_t middle = low + (high - low) / 2;
        int pivot = std::min(node->l + static_cast<int>(middle), node->r);
        if (key <= pivot) high = middle;
        else low = middle + 1;
    }
    return std::min(node->l + static_cast<int>(low), node->r);
}

static size_t count_nodes(const std::shared_ptr<Node>& node) {
    return node->is_leaf ? 1 : 1 + count_nodes(node->left) + count_nodes(node->right);
}

static uint64_t next_u64(uint64_t& state) {
    state ^= state << 7; state ^= state >> 9; return state;
}

static std::vector<int> make_queries(const std::vector<double>& prefix, int count) {
    std::vector<int> queries; queries.reserve(count); uint64_t state = 20260725;
    for (int i = 0; i < count; ++i) {
        double u = static_cast<double>(next_u64(state) >> 11) * (1.0 / 9007199254740992.0);
        queries.push_back(static_cast<int>(std::lower_bound(prefix.begin() + 1, prefix.end(), u) - prefix.begin()));
    }
    return queries;
}

template <class Lookup>
static double ns_per_query(const std::vector<int>& queries, Lookup lookup) {
    volatile uint64_t checksum = 0;
    auto start = std::chrono::steady_clock::now();
    for (int key : queries) checksum += static_cast<uint64_t>(lookup(key));
    auto end = std::chrono::steady_clock::now();
    if (checksum == 0) std::abort();
    return std::chrono::duration<double, std::nano>(end - start).count() / queries.size();
}

int main(int argc, char** argv) {
    int n = argc > 1 ? std::atoi(argv[1]) : 10000;
    int queries_count = argc > 2 ? std::atoi(argv[2]) : 1000000;
    int repeats = argc > 3 ? std::atoi(argv[3]) : 7;
    if (n < 2 || queries_count < 1 || repeats < 1) return 2;
    for (int size = 2; size <= 257; ++size) {
        auto leaf = leaf_node(1, size);
        for (int key = 1; key <= size; ++key) {
            int observed = route_fixed_rounds(leaf, key);
            if (observed != key) {
                std::cerr << "fixed-round fallback self-check failed: size=" << size
                          << " key=" << key << " observed=" << observed << '\n';
                return 3;
            }
        }
    }
    std::cout << "workload,solver,n,budget,queries,repeats,fallback,median_batch_ns_per_query,p95_batch_ns_per_query,routing_nodes,auxiliary_bytes,total_index_bytes\n";
    for (const std::string workload : {
        "uniform",
        "zipf",
        "hot_tail",
        "ycsb_hotspot_80_20",
        "ycsb_latest_biased",
    }) {
        std::vector<double> p(n + 1, 0.0);
        for (int i = 1; i <= n; ++i) {
            if (workload == "uniform") p[i] = 1.0;
            else if (workload == "zipf") p[i] = 1.0 / std::pow(i, 1.15);
            else if (workload == "hot_tail") p[i] = i > n * 9 / 10 ? 30.0 : 1.0;
            else if (workload == "ycsb_hotspot_80_20") {
                int hot_keys = std::max(1, n / 5);
                p[i] = i <= hot_keys ? 0.8 / hot_keys : 0.2 / std::max(1, n - hot_keys);
            } else {
                p[i] = std::exp(6.0 * (static_cast<double>(i) / n - 1.0));
            }
        }
        double sum = std::accumulate(p.begin() + 1, p.end(), 0.0);
        for (int i = 1; i <= n; ++i) p[i] /= sum;
        std::vector<double> prefix(n + 1, 0.0);
        for (int i = 1; i <= n; ++i) prefix[i] = prefix[i - 1] + p[i];
        prefix[n] = 1.0;
        auto queries = make_queries(prefix, queries_count);
        std::vector<int> keys(n); std::iota(keys.begin(), keys.end(), 1);
        int budget = std::min(6, n - 1);
        auto certigap = pruned_beam_solve(p, budget, 0.15, 32, 16).tree;
        auto balanced = balanced_tree(1, n, budget);
        auto weighted = weighted_tree(prefix, 1, n, budget);
        auto balanced_full = balanced_full_tree(1, n);
        struct Entry { const char* name; std::shared_ptr<Node> tree; int declared_budget; };
        for (const auto& entry : std::vector<Entry>{
            {"certigap_pruned", certigap, budget},
            {"balanced_budgeted", balanced, budget},
            {"weighted_budgeted", weighted, budget},
            {"balanced_full_reference", balanced_full, n - 1},
        }) {
            std::vector<double> samples; samples.reserve(repeats);
            ns_per_query(queries, [&](int key) { return route_fixed_rounds(entry.tree, key); });
            for (int run = 0; run < repeats; ++run) samples.push_back(ns_per_query(queries, [&](int key) { return route_fixed_rounds(entry.tree, key); }));
            std::sort(samples.begin(), samples.end()); size_t nodes = count_nodes(entry.tree);
            size_t auxiliary_bytes = nodes * sizeof(Node);
            size_t total_bytes = auxiliary_bytes + keys.size() * sizeof(int);
            std::cout << workload << ',' << entry.name << ',' << n << ',' << entry.declared_budget << ',' << queries_count << ',' << repeats << ",fixed_rounds,"
                      << std::fixed << std::setprecision(3) << samples[samples.size() / 2] << ','
                      << samples[std::min(samples.size() - 1, (samples.size() * 95 + 99) / 100 - 1)] << ','
                      << nodes << ',' << auxiliary_bytes << ',' << total_bytes << '\n';
        }
        std::vector<double> samples; samples.reserve(repeats);
        ns_per_query(queries, [&](int key) { return *std::lower_bound(keys.begin(), keys.end(), key); });
        for (int run = 0; run < repeats; ++run) samples.push_back(ns_per_query(queries, [&](int key) { return *std::lower_bound(keys.begin(), keys.end(), key); }));
        std::sort(samples.begin(), samples.end());
        std::cout << workload << ",std_lower_bound," << n << ",0," << queries_count << ',' << repeats << ",variable_rounds,"
                  << std::fixed << std::setprecision(3) << samples[samples.size() / 2] << ','
                  << samples[std::min(samples.size() - 1, (samples.size() * 95 + 99) / 100 - 1)]
                  << ",0,0," << keys.size() * sizeof(int) << '\n';
    }
}
