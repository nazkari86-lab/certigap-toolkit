from __future__ import annotations

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
