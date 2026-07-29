#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

volatile double sink = 0.0;

template <class Operation>
double median_nanoseconds(Operation operation, std::size_t iterations) {
    std::vector<double> samples;
    samples.reserve(9);
    for (int sample = 0; sample < 9; ++sample) {
        const auto start = std::chrono::steady_clock::now();
        operation(iterations);
        const auto stop = std::chrono::steady_clock::now();
        const auto elapsed =
            std::chrono::duration<double, std::nano>(stop - start).count();
        samples.push_back(elapsed / static_cast<double>(iterations));
    }
    std::sort(samples.begin(), samples.end());
    return std::max(0.001, samples[samples.size() / 2]);
}

}  // namespace

int main() {
    constexpr std::size_t size = 1U << 18U;
    constexpr std::size_t iterations = 1U << 22U;
    std::vector<double> values(size, 1.0);
    std::vector<double> aggregates(size / 64, 2.0);

    const auto value_read = median_nanoseconds(
        [&](std::size_t count) {
            double total = 0.0;
            for (std::size_t index = 0; index < count; ++index) {
                total += values[(index * 1315423911ULL) & (size - 1)];
            }
            sink = total;
        },
        iterations
    );
    const auto aggregate_read = median_nanoseconds(
        [&](std::size_t count) {
            double total = 0.0;
            const std::size_t mask = aggregates.size() - 1;
            for (std::size_t index = 0; index < count; ++index) {
                total += aggregates[(index * 2654435761ULL) & mask];
            }
            sink = total;
        },
        iterations
    );
    const auto combine = median_nanoseconds(
        [&](std::size_t count) {
            double total = 1.0;
            for (std::size_t index = 0; index < count; ++index) {
                total += static_cast<double>(index & 7U);
            }
            sink = total;
        },
        iterations
    );
    const auto value_write = median_nanoseconds(
        [&](std::size_t count) {
            for (std::size_t index = 0; index < count; ++index) {
                values[(index * 1315423911ULL) & (size - 1)] += 1.0;
            }
            sink = values[0];
        },
        iterations
    );
    const auto aggregate_write = median_nanoseconds(
        [&](std::size_t count) {
            const std::size_t mask = aggregates.size() - 1;
            for (std::size_t index = 0; index < count; ++index) {
                aggregates[(index * 2654435761ULL) & mask] += 1.0;
            }
            sink = aggregates[0];
        },
        iterations
    );

    std::cout << std::setprecision(17)
              << "{\n"
              << "  \"name\": \"native-median-v1\",\n"
              << "  \"value_read_ns\": " << value_read << ",\n"
              << "  \"aggregate_read_ns\": " << aggregate_read << ",\n"
              << "  \"combine_ns\": " << combine << ",\n"
              << "  \"value_write_ns\": " << value_write << ",\n"
              << "  \"aggregate_write_ns\": " << aggregate_write << ",\n"
              << "  \"sample_count\": 9\n"
              << "}\n";
    return sink < 0.0 ? 1 : 0;
}
