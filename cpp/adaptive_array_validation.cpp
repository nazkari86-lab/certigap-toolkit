#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include "certigap.hpp"


std::vector<double> values() {
    std::vector<double> result(64);
    for (int index = 0; index < 64; ++index) result[index] = index;
    return result;
}

void row(
    const std::string& scenario,
    const certigap::adaptive_array<double>& data,
    bool passed
) {
    std::cout << scenario << ',' << data.selected_name() << ','
              << std::boolalpha << data.optimized() << ','
              << data.decision().attempted << ','
              << data.decision().switched << ','
              << data.observed_operations() << ',' << passed << ','
              << '"' << data.decision().reason << '"' << '\n';
}

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    std::cout << "scenario,selected,optimized,attempted,switched,"
                 "observed_operations,passed,reason\n";

    certigap::AutoTunePolicy automatic;
    automatic.warmup_operations = 64;
    automatic.check_interval = 64;
    automatic.minimum_relative_improvement = 0.01;
    certigap::adaptive_array<double> ranges(values(), automatic);
    double checksum = 0.0;
    for (int index = 0; index < 64; ++index) {
        checksum += ranges.range_sum(3, 60);
    }
    row(
        "automatic_range_warmup",
        ranges,
        ranges.selected_name() == "prefix_sum"
            && std::abs(checksum - 64.0 * 1767.0) < 1e-9
    );

    certigap::adaptive_array<double> points(values(), automatic);
    for (int index = 0; index < 64; ++index) points.get(1);
    row(
        "automatic_point_warmup",
        points,
        points.selected_name() == "sorted_array" && points.optimized()
    );

    certigap::AutoTunePolicy guarded = automatic;
    guarded.minimum_relative_improvement = 2.0;
    certigap::adaptive_array<double> rejected(values(), guarded);
    for (int index = 0; index < 64; ++index) rejected.range_sum(3, 60);
    row(
        "deployment_threshold_rejection",
        rejected,
        rejected.selected_name() == "sorted_array" && !rejected.optimized()
    );

    certigap::AutoTunePolicy explicit_policy = automatic;
    explicit_policy.automatic_maintenance = false;
    certigap::adaptive_array<double> explicit_data(values(), explicit_policy);
    for (int index = 0; index < 64; ++index) explicit_data.range_sum(3, 60);
    const bool explicit_before = !explicit_data.optimized();
    const bool explicit_switch = explicit_data.maintenance();
    row(
        "explicit_maintenance",
        explicit_data,
        explicit_before && explicit_switch
            && explicit_data.selected_name() == "prefix_sum"
    );

    certigap::AutoTunePolicy persistent = automatic;
    persistent.profile_path = argv[1];
    {
        certigap::adaptive_array<double> writer(values(), persistent);
        for (int index = 0; index < 64; ++index) writer.range_sum(3, 60);
        row("profile_writer", writer, writer.selected_name() == "prefix_sum");
    }
    certigap::adaptive_array<double> reader(values(), persistent);
    row(
        "profile_reader",
        reader,
        reader.selected_name() == "prefix_sum"
            && reader.observed_operations() == 64.0
    );
    std::remove(argv[1]);
    return 0;
}
