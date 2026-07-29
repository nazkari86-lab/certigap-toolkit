#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "certigap.hpp"


static void emit_case(int n, const std::string& scenario) {
    std::vector<double> values(n);
    for (int index = 0; index < n; ++index) {
        values[index] = static_cast<double>(index);
    }
    certigap::Aggregate aggregate = certigap::Aggregate::Sum;
    if (scenario == "minimum") aggregate = certigap::Aggregate::Min;
    if (scenario == "maximum") aggregate = certigap::Aggregate::Max;
    certigap::AdaptiveIndex index(values, aggregate);
    certigap::OptimizeOptions options;
    options.aggregate = aggregate;

    if (scenario == "point_hot") {
        for (int count = 0; count < 200; ++count) {
            index.observe_get(1 + count % std::max(2, n / 8));
        }
    } else {
        for (int count = 0; count < 200; ++count) {
            int left = 2 + count % std::max(1, n / 8);
            index.observe_range(left, n - 1);
        }
    }
    if (
        scenario == "segment_calibrated"
        || scenario == "minimum"
        || scenario == "maximum"
    ) {
        options.segment_tree_unit_cost = 0.1;
    }
    if (scenario == "certirange_required") {
        options.require_certirange = true;
    }

    const auto selected = index.optimize(options);
    const auto snapshot = index.snapshot();
    double expected = 0.0;
    if (aggregate == certigap::Aggregate::Sum) {
        expected = static_cast<double>(n - 1) * n / 2.0;
    } else if (aggregate == certigap::Aggregate::Min) {
        expected = 0.0;
    } else {
        expected = n - 1.0;
    }
    bool correct = std::abs(index.range_query(1, n) - expected) <= 1e-12;
    index.point_update(1, 1000.0);
    correct = correct
        && snapshot.peek(1) == 0.0
        && index.peek(1) == 1000.0;

    const auto& leaderboard = index.leaderboard();
    const auto selected_row = std::find_if(
        leaderboard.begin(),
        leaderboard.end(),
        [selected](const certigap::CandidateReport& row) {
            return row.backend == selected;
        }
    );
    if (selected_row == leaderboard.end()) throw std::runtime_error("missing winner");
    std::cout
        << n << ',' << scenario << ',' << certigap::backend_name(selected)
        << ',' << leaderboard.size() << ',' << std::boolalpha << correct
        << ',' << std::setprecision(12) << selected_row->score
        << ',' << selected_row->memory_slots << ',' << selected_row->height
        << '\n';
}

int main() {
    std::cout
        << "n,scenario,selected,candidate_count,correct,score,memory_slots,height\n";
    for (int n : {16, 32, 64, 128}) {
        for (const std::string scenario : {
            "point_hot",
            "range_hot",
            "segment_calibrated",
            "certirange_required",
            "minimum",
            "maximum",
        }) {
            emit_case(n, scenario);
        }
    }
}
