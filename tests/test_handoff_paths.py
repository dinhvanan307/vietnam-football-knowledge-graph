"""Đảm bảo một ZIP bàn giao cũ vẫn đi tới đúng thư mục mà bộ chấm sẽ đọc."""
import tempfile
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from bongda import paths
from bongda.data import khoi_phuc_goi as handoff


class RestoreEvaluationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.archive = self.root / "labels.zip"
        name = "danh_gia_precision_a3/phieu_cham.tsv"
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr(name, b"locked labels\n")
            archive.writestr("danh_gia_precision_a3/private_notes.tsv", b"other\n")
        package = (sha256(self.archive.read_bytes()).hexdigest(), "", (name,))
        self.enterContext(patch.multiple(paths, ROOT=self.root, WORK=self.root / "work"))
        self.enterContext(patch.object(handoff, "ROOT", self.root))
        self.enterContext(patch.dict(handoff.PACKAGES, {self.archive.name: package}))

    def test_restore_to_work_and_repeat(self):
        handoff.restore(self.archive)
        handoff.restore(self.archive)
        output = paths.evaluation_dir("a3")
        self.assertEqual(output, self.root / "work/evaluation/a3")
        self.assertEqual([file.name for file in output.iterdir()], ["phieu_cham.tsv"])
        self.assertEqual((output / "phieu_cham.tsv").read_bytes(), b"locked labels\n")
        self.assertFalse((self.root / "danh_gia_precision_a3").exists())

    def test_prior_layout_reuses_labels_and_protects_local_edits(self):
        previous = self.root / "danh_gia_precision_a3"
        previous.mkdir()
        labels = previous / "phieu_cham.tsv"
        labels.write_bytes(b"local review\n")
        self.assertEqual(paths.evaluation_dir("a3"), previous)
        with self.assertRaises(FileExistsError):
            handoff.restore(self.archive)
        self.assertEqual(labels.read_bytes(), b"local review\n")
        self.assertFalse((self.root / "work/evaluation/a3").exists())
