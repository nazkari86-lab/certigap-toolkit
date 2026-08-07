import tempfile
import unittest
import zipfile
from pathlib import Path

from certigap.benchmark_datasets import (
    _hetrec_delicious,
    _hetrec_lastfm,
    _movielens_100k_temporal_trace,
    _movielens_32m,
)


class BenchmarkDatasetParserTests(unittest.TestCase):
    def archive(self, members: dict[str, str]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "source.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return path

    def test_movielens_uses_only_observed_ids_in_numeric_order(self) -> None:
        path = self.archive(
            {
                "ml-32m/ratings.csv": (
                    "userId,movieId,rating,timestamp\n"
                    "1,10,4.0,1\n2,2,3.0,2\n3,10,5.0,3\n"
                )
            }
        )
        self.assertEqual(_movielens_32m(path), [1 / 3, 2 / 3])

    def test_movielens_temporal_trace_preserves_source_tie_order(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "u.data"
        path.write_text(
            "1\t9\t4\t20\n2\t3\t5\t10\n3\t7\t4\t10\n",
            encoding="latin-1",
        )
        self.assertEqual(
            _movielens_100k_temporal_trace(path),
            [(10, 3), (10, 7), (20, 9)],
        )

    def test_lastfm_aggregates_reported_play_weights(self) -> None:
        path = self.archive(
            {"user_artists.dat": "userID\tartistID\tweight\n1\t8\t3\n2\t8\t2\n1\t3\t5\n"}
        )
        self.assertEqual(_hetrec_lastfm(path), [0.5, 0.5])

    def test_delicious_deduplicates_multi_tag_user_bookmark_events(self) -> None:
        path = self.archive(
            {
                "user_taggedbookmarks.dat": (
                    "userID\tbookmarkID\ttagID\tday\tmonth\tyear\thour\tminute\tsecond\n"
                    "1\t10\t2\t1\t1\t2025\t0\t0\t0\n"
                    "1\t10\t3\t1\t1\t2025\t0\t0\t0\n"
                    "2\t10\t2\t1\t1\t2025\t0\t0\t0\n"
                    "1\t20\t2\t1\t1\t2025\t0\t0\t0\n"
                )
            }
        )
        self.assertEqual(_hetrec_delicious(path), [2 / 3, 1 / 3])


if __name__ == "__main__":
    unittest.main()
