from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from generate_single_header import generated_text


ROOT = Path(__file__).resolve().parents[1]


class AdaptiveHeaderTests(unittest.TestCase):
    def test_single_header_is_current(self) -> None:
        observed = (ROOT / "cpp" / "certigap.hpp").read_text(
            encoding="utf-8"
        )
        self.assertEqual(observed, generated_text())

    def test_online_example_compiles_without_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "online_example"
            result = subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(ROOT / "cpp"),
                    str(ROOT / "examples" / "online_single_file.cpp"),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run(
                [str(executable)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("selected=fenwick", run.stdout)
            self.assertIn("sum=434", run.stdout)
            self.assertIn("old=1 current=100", run.stdout)

    def test_adaptive_portfolio_and_rebuild_policy(self) -> None:
        source = r"""
#include <cmath>
#include <stdexcept>
#include <vector>
#include "certigap.hpp"

std::vector<double> values() {
    std::vector<double> result(32);
    for (int index = 0; index < 32; ++index) result[index] = index;
    return result;
}

int main() {
    certigap::AdaptiveIndex array(values());
    for (int i = 0; i < 100; ++i) array.observe_get(1);
    if (array.optimize() != certigap::Backend::SortedArray) return 2;
    if (array.leaderboard().size() != 5) return 3;

    certigap::AdaptiveIndex fenwick(values());
    for (int i = 0; i < 100; ++i) fenwick.observe_range(3, 30);
    if (fenwick.optimize() != certigap::Backend::Fenwick) return 4;
    if (std::abs(fenwick.range_query(3, 30) - 434.0) > 1e-12) return 5;

    certigap::AdaptiveIndex segment(values());
    for (int i = 0; i < 100; ++i) segment.observe_range(3, 30);
    certigap::OptimizeOptions segment_options;
    segment_options.segment_tree_unit_cost = 0.1;
    if (segment.optimize(segment_options) != certigap::Backend::SegmentTree) {
        return 6;
    }

    certigap::AdaptiveIndex certirange(values());
    for (int i = 0; i < 100; ++i) certirange.observe_range(1, 8);
    certigap::OptimizeOptions certi_options;
    certi_options.require_certirange = true;
    const auto certi_backend = certirange.optimize(certi_options);
    if (
        certi_backend != certigap::Backend::CertiRangePoint
        && certi_backend != certigap::Backend::CertiRangeRange
    ) return 7;
    auto snapshot = certirange.snapshot();
    certirange.point_update(2, 100.0);
    if (snapshot.get(2) != 1.0 || certirange.get(2) != 100.0) return 8;

    certigap::AdaptiveIndex minimum(values(), certigap::Aggregate::Min);
    for (int i = 0; i < 100; ++i) minimum.observe_range(2, 30);
    certigap::OptimizeOptions min_options;
    min_options.aggregate = certigap::Aggregate::Min;
    min_options.segment_tree_unit_cost = 0.1;
    if (minimum.optimize(min_options) != certigap::Backend::SegmentTree) {
        return 9;
    }
    if (minimum.range_query(2, 30) != 1.0) return 10;

    certigap::AdaptiveIndex implicit_min(values(), certigap::Aggregate::Min);
    for (int i = 0; i < 100; ++i) implicit_min.observe_range(2, 30);
    implicit_min.optimize();
    if (implicit_min.range_query(2, 30) != 1.0) return 15;

    certigap::AdaptiveIndex maximum(values(), certigap::Aggregate::Max);
    for (int i = 0; i < 100; ++i) maximum.observe_range(2, 30);
    certigap::OptimizeOptions max_options;
    max_options.aggregate = certigap::Aggregate::Max;
    max_options.segment_tree_unit_cost = 0.1;
    maximum.optimize(max_options);
    if (maximum.range_query(2, 30) != 29.0) return 11;

    certigap::AdaptiveIndex drift(values());
    for (int i = 0; i < 1000; ++i) drift.observe_get(1);
    drift.optimize();
    for (int i = 0; i < 1000; ++i) drift.observe_range(1, 32);
    certigap::RebuildPolicy policy;
    policy.minimum_new_operations = 100;
    policy.minimum_tv_drift = 0.05;
    if (!drift.maybe_reoptimize(policy)) return 12;

    bool empty_rejected = false;
    try {
        certigap::AdaptiveIndex empty(values());
        empty.optimize();
    } catch (const std::logic_error&) {
        empty_rejected = true;
    }
    if (!empty_rejected) return 13;

    bool memory_rejected = false;
    try {
        certigap::AdaptiveIndex limited(values());
        limited.observe_get(1);
        certigap::OptimizeOptions options;
        options.memory_limit_slots = 1;
        limited.optimize(options);
    } catch (const std::invalid_argument&) {
        memory_rejected = true;
    }
    if (!memory_rejected) return 14;
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "adaptive_test.cpp"
            executable = root / "adaptive_test"
            source_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(ROOT / "cpp"),
                    str(source_path),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([str(executable)], check=False)
            self.assertEqual(run.returncode, 0)

    def test_adaptive_array_auto_tuning_and_profile_persistence(self) -> None:
        source = r"""
#include <cmath>
#include <fstream>
#include <string>
#include <vector>
#include "certigap.hpp"

std::vector<double> values() {
    std::vector<double> result(32);
    for (int index = 0; index < 32; ++index) result[index] = index;
    return result;
}

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    certigap::AutoTunePolicy policy;
    policy.warmup_operations = 32;
    policy.check_interval = 32;
    policy.minimum_relative_improvement = 0.01;
    policy.profile_path = argv[1];
    {
        certigap::adaptive_array<double> data(values(), policy);
        for (int index = 0; index < 32; ++index) {
            if (std::abs(data.range_sum(2, 30) - 434.0) > 1e-9) return 2;
        }
        if (!data.optimized()) return 3;
        if (data.selected_name() != "fenwick") return 4;
        if (!data.decision().switched) return 5;
        if (data.explain().find("deployment threshold") == std::string::npos) {
            return 6;
        }
    }
    {
        certigap::adaptive_array<double> restored(values(), policy);
        if (restored.observed_operations() != 32.0) return 7;
        if (restored.selected_name() != "fenwick") return 8;
        if (restored.size() != 32) return 9;
    }

    certigap::AutoTunePolicy guarded = policy;
    guarded.profile_path.clear();
    guarded.minimum_relative_improvement = 2.0;
    certigap::adaptive_array<double> rejected(values(), guarded);
    for (int index = 0; index < 32; ++index) rejected.range_sum(2, 30);
    if (rejected.optimized()) return 10;
    if (rejected.selected_name() != "sorted_array") return 11;
    if (rejected.decision().reason.find("below") == std::string::npos) return 12;

    certigap::AutoTunePolicy explicit_policy = policy;
    explicit_policy.profile_path.clear();
    explicit_policy.automatic_maintenance = false;
    certigap::adaptive_array<double> explicit_data(values(), explicit_policy);
    for (int index = 0; index < 32; ++index) explicit_data.range_sum(2, 30);
    if (explicit_data.optimized()) return 13;
    if (!explicit_data.maintenance()) return 14;
    if (explicit_data.selected_name() != "fenwick") return 15;

    std::ofstream malformed(std::string(argv[1]) + ".bad");
    malformed << "CERTIGAP_PROFILE_V1\nsize 31\naggregate sum\nend\n";
    malformed.close();
    certigap::Index strict(values());
    try {
        strict.load_profile(std::string(argv[1]) + ".bad");
        return 16;
    } catch (const std::invalid_argument&) {
    }
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "adaptive_array.cpp"
            executable = root / "adaptive_array"
            profile = root / "workload.profile"
            source_path.write_text(source, encoding="utf-8")
            compile_result = subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(ROOT / "cpp"),
                    str(source_path),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                compile_result.returncode, 0, compile_result.stderr
            )
            run = subprocess.run(
                [str(executable), str(profile)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(profile.is_file())
            self.assertIn(
                "CERTIGAP_PROFILE_V1",
                profile.read_text(encoding="utf-8"),
            )

    def test_cmake_install_and_find_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            install = root / "install"
            subprocess.run(
                [
                    "cmake",
                    "-S",
                    str(ROOT),
                    "-B",
                    str(build),
                    "-DCERTIGAP_BUILD_EXAMPLES=ON",
                    f"-DCMAKE_INSTALL_PREFIX={install}",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["cmake", "--build", str(build), "--parallel", "2"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["cmake", "--install", str(build)],
                check=True,
                capture_output=True,
            )
            if shutil.which("pkg-config"):
                pkg_source = root / "pkg-consumer.cpp"
                pkg_source.write_text(
                    """
#include <certigap.hpp>
#include <vector>
int main() {
    certigap::adaptive_array<double> data({1, 2, 3, 4});
    return data.range_sum(0, 4) == 10 ? 0 : 1;
}
""",
                    encoding="utf-8",
                )
                flags = subprocess.run(
                    ["pkg-config", "--cflags", "certigap"],
                    check=True,
                    capture_output=True,
                    text=True,
                    env={
                        **os.environ,
                        "PKG_CONFIG_PATH": str(
                            next(install.glob("lib*/pkgconfig"))
                        ),
                    },
                ).stdout.split()
                pkg_executable = root / "pkg-consumer"
                subprocess.run(
                    [
                        "c++",
                        "-std=c++17",
                        *flags,
                        str(pkg_source),
                        "-o",
                        str(pkg_executable),
                    ],
                    check=True,
                    capture_output=True,
                )
                subprocess.run([str(pkg_executable)], check=True)
            downstream = root / "downstream"
            downstream.mkdir()
            (downstream / "CMakeLists.txt").write_text(
                "\n".join(
                    [
                        "cmake_minimum_required(VERSION 3.16)",
                        "project(consumer LANGUAGES CXX)",
                        "find_package(CertiGap 1.6 REQUIRED)",
                        "add_executable(app main.cpp)",
                        "target_link_libraries(app PRIVATE CertiGap::certigap)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (downstream / "main.cpp").write_text(
                """
#include <certigap.hpp>
#include <vector>
int main() {
    certigap::Index index(std::vector<double>{1, 2, 3});
    index.observe_range(1, 3);
    index.optimize();
    return index.peek_range(1, 3) == 6 ? 0 : 1;
}
""",
                encoding="utf-8",
            )
            consumer_build = root / "consumer-build"
            subprocess.run(
                [
                    "cmake",
                    "-S",
                    str(downstream),
                    "-B",
                    str(consumer_build),
                    f"-DCMAKE_PREFIX_PATH={install}",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "cmake",
                    "--build",
                    str(consumer_build),
                    "--parallel",
                    "2",
                ],
                check=True,
                capture_output=True,
            )
            result = subprocess.run(
                [str(consumer_build / "app")], check=False
            )
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
