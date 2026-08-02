#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <string>
#include <vector>

#include "certigap_core.cpp"

#ifdef CERTIGAP_HAVE_RADIX_SPLINE
#include <rs/builder.h>
#endif

using Clock = std::chrono::steady_clock;

static std::vector<std::uint64_t> load_keys(const char* path) {
    std::ifstream input(path, std::ios::binary);
    std::uint64_t count = 0;
    input.read(reinterpret_cast<char*>(&count), sizeof(count));
    std::vector<std::uint64_t> keys(count);
    input.read(reinterpret_cast<char*>(keys.data()), count * sizeof(keys[0]));
    if (!input || keys.empty() || !std::is_sorted(keys.begin(), keys.end())) {
        throw std::runtime_error("sample file is truncated, empty, or unsorted");
    }
    return keys;
}

static std::uint64_t next_u64(std::uint64_t& state) {
    state ^= state << 7;
    state ^= state >> 9;
    return state;
}

static std::vector<double> workload_weights(std::size_t n, const std::string& name) {
    std::vector<double> weights(n + 1, 0.0);
    for (std::size_t i = 1; i <= n; ++i) {
        if (name == "uniform") weights[i] = 1.0;
        else if (name == "zipf_1_15") weights[i] = 1.0 / std::pow(i, 1.15);
        else if (name == "hotspot_80_20") {
            const std::size_t hot = std::max<std::size_t>(1, n / 5);
            weights[i] = i <= hot ? 0.8 / hot : 0.2 / std::max<std::size_t>(1, n - hot);
        } else {
            weights[i] = std::exp(8.0 * (static_cast<double>(i) / n - 1.0));
        }
    }
    const double total = std::accumulate(weights.begin() + 1, weights.end(), 0.0);
    for (std::size_t i = 1; i <= n; ++i) weights[i] /= total;
    return weights;
}

static std::vector<std::uint64_t> make_queries(
    const std::vector<std::uint64_t>& keys,
    const std::vector<double>& weights,
    std::size_t count
) {
    std::vector<double> prefix(weights.size(), 0.0);
    for (std::size_t i = 1; i < weights.size(); ++i) prefix[i] = prefix[i - 1] + weights[i];
    prefix.back() = 1.0;
    std::vector<std::uint64_t> queries;
    queries.reserve(count);
    std::uint64_t state = 0xC37A9A20260803ULL;
    for (std::size_t i = 0; i < count; ++i) {
        const double unit = static_cast<double>(next_u64(state) >> 11)
            * (1.0 / 9007199254740992.0);
        const auto rank = std::lower_bound(prefix.begin() + 1, prefix.end(), unit)
            - prefix.begin();
        queries.push_back(keys[static_cast<std::size_t>(rank) - 1]);
    }
    return queries;
}

static std::vector<std::uint64_t> build_eytzinger(const std::vector<std::uint64_t>& keys) {
    std::vector<std::uint64_t> tree(keys.size() + 1);
    std::size_t cursor = 0;
    const auto fill = [&](const auto& self, std::size_t node) -> void {
        if (node > keys.size()) return;
        self(self, node * 2);
        tree[node] = keys[cursor++];
        self(self, node * 2 + 1);
    };
    fill(fill, 1);
    return tree;
}

static std::uint64_t eytzinger_lookup(
    const std::vector<std::uint64_t>& tree, std::uint64_t key
) {
    std::size_t node = 1, candidate = 0;
    while (node < tree.size()) {
        if (tree[node] < key) node = node * 2 + 1;
        else { candidate = node; node *= 2; }
    }
    return candidate == 0 ? 0 : tree[candidate];
}

static std::uint64_t interpolation_lookup(
    const std::vector<std::uint64_t>& keys, std::uint64_t key
) {
    std::size_t low = 0, high = keys.size();
    int probes = 0;
    while (low < high && keys[low] < key && probes++ < 32) {
        if (keys[high - 1] == keys[low]) break;
        const long double fraction = static_cast<long double>(key - keys[low])
            / static_cast<long double>(keys[high - 1] - keys[low]);
        std::size_t probe = low + static_cast<std::size_t>(
            fraction * static_cast<long double>(high - low - 1));
        probe = std::max(low, std::min(probe, high - 1));
        if (keys[probe] < key) low = probe + 1;
        else high = probe;
    }
    const auto found = std::lower_bound(keys.begin() + low, keys.begin() + high, key);
    return found == keys.end() ? 0 : *found;
}

static std::uint64_t certigap_lookup(
    const std::shared_ptr<Node>& root,
    const std::vector<std::uint64_t>& keys,
    std::uint64_t key
) {
    const Node* node = root.get();
    while (!node->is_leaf) {
        node = key <= keys[static_cast<std::size_t>(node->threshold) - 1]
            ? node->left.get() : node->right.get();
    }
    const auto begin = keys.begin() + node->l - 1;
    const auto end = keys.begin() + node->r;
    const auto found = std::lower_bound(begin, end, key);
    return found == end ? 0 : *found;
}

static std::size_t node_count(const std::shared_ptr<Node>& node) {
    return node->is_leaf ? 1 : 1 + node_count(node->left) + node_count(node->right);
}

template <class Lookup>
static std::vector<double> measure(
    const std::vector<std::uint64_t>& queries, int repeats, Lookup lookup
) {
    std::vector<double> samples;
    volatile std::uint64_t checksum = 0;
    for (int repeat = -1; repeat < repeats; ++repeat) {
        const auto start = Clock::now();
        for (const auto key : queries) checksum ^= lookup(key) + 0x9e3779b97f4a7c15ULL;
        const auto stop = Clock::now();
        if (repeat >= 0) samples.push_back(
            std::chrono::duration<double, std::nano>(stop - start).count() / queries.size()
        );
    }
    if (checksum == 0xFFFFFFFFFFFFFFFFULL) std::abort();
    std::sort(samples.begin(), samples.end());
    return samples;
}

static double percentile(const std::vector<double>& values, double fraction) {
    const auto index = std::min(values.size() - 1,
        static_cast<std::size_t>(std::ceil(fraction * values.size())) - 1);
    return values[index];
}

int main(int argc, char** argv) {
    if (argc != 6) {
        std::cerr << "usage: benchmark SAMPLE DATASET QUERIES REPEATS BUDGET\n";
        return 2;
    }
    const auto keys = load_keys(argv[1]);
    const std::string dataset = argv[2];
    const std::size_t query_count = std::stoull(argv[3]);
    const int repeats = std::stoi(argv[4]);
    const int budget = std::min<int>(std::stoi(argv[5]), keys.size() - 1);
    if (query_count == 0 || repeats < 1 || budget < 0) return 2;
    const auto eytzinger = build_eytzinger(keys);

#ifdef CERTIGAP_HAVE_RADIX_SPLINE
    const auto rs_start = Clock::now();
    rs::Builder<std::uint64_t> builder(keys.front(), keys.back(), 18, 32);
    for (const auto key : keys) builder.AddKey(key);
    const auto radix_spline = builder.Finalize();
    const double rs_build_ms = std::chrono::duration<double, std::milli>(
        Clock::now() - rs_start).count();
#endif

    std::cout << "dataset,workload,method,sample_keys,source_keys,queries,repeats,budget,"
                 "median_ns_per_query,p95_batch_ns_per_query,build_ms,index_bytes,correct\n";
    for (const std::string workload : {
        "uniform", "zipf_1_15", "hotspot_80_20", "latest_biased"
    }) {
        const auto weights = workload_weights(keys.size(), workload);
        const auto queries = make_queries(keys, weights, query_count);
        const auto build_start = Clock::now();
        const auto certigap = pruned_beam_solve(weights, budget, 0.15, 32, 16).tree;
        const double build_ms = std::chrono::duration<double, std::milli>(
            Clock::now() - build_start).count();
        struct Result { std::string name; std::vector<double> samples; double build; std::size_t bytes; };
        std::vector<Result> results;
        results.push_back({"std_lower_bound", measure(queries, repeats, [&](auto key) {
            const auto it = std::lower_bound(keys.begin(), keys.end(), key);
            return it == keys.end() ? 0 : *it;
        }), 0.0, 0});
        results.push_back({"eytzinger", measure(queries, repeats, [&](auto key) {
            return eytzinger_lookup(eytzinger, key);
        }), 0.0, eytzinger.size() * sizeof(std::uint64_t)});
        results.push_back({"interpolation_guarded", measure(queries, repeats, [&](auto key) {
            return interpolation_lookup(keys, key);
        }), 0.0, 0});
        results.push_back({"certigap_partial", measure(queries, repeats, [&](auto key) {
            return certigap_lookup(certigap, keys, key);
        }), build_ms, node_count(certigap) * sizeof(Node)});
#ifdef CERTIGAP_HAVE_RADIX_SPLINE
        results.push_back({"sosd_radix_spline", measure(queries, repeats, [&](auto key) {
            const auto bound = radix_spline.GetSearchBound(key);
            const auto it = std::lower_bound(keys.begin() + bound.begin, keys.begin() + bound.end, key);
            return it == keys.end() ? 0 : *it;
        }), rs_build_ms, radix_spline.GetSize()});
#endif
        for (const auto& result : results) {
            bool correct = true;
            for (std::size_t i = 0; i < std::min<std::size_t>(queries.size(), 10000); ++i) {
                const auto expected = *std::lower_bound(keys.begin(), keys.end(), queries[i]);
                std::uint64_t actual = 0;
                if (result.name == "eytzinger") actual = eytzinger_lookup(eytzinger, queries[i]);
                else if (result.name == "interpolation_guarded") actual = interpolation_lookup(keys, queries[i]);
                else if (result.name == "certigap_partial") actual = certigap_lookup(certigap, keys, queries[i]);
                else actual = expected;
                correct = correct && actual == expected;
            }
            std::cout << dataset << ',' << workload << ',' << result.name << ','
                      << keys.size() << ",200000000," << query_count << ',' << repeats << ','
                      << (result.name == "certigap_partial" ? budget : 0) << ','
                      << std::fixed << std::setprecision(3)
                      << percentile(result.samples, 0.5) << ','
                      << percentile(result.samples, 0.95) << ',' << result.build << ','
                      << result.bytes << ',' << (correct ? "true" : "false") << '\n';
        }
    }
}
