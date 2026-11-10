"""Các lệnh thường dùng khi làm việc từ gốc repository."""
import argparse
import os
import runpy
import sys

from bongda.paths import ROOT

COMMANDS = {
    "verify": ("bongda.evaluate.overall.kiem_tra_cong_khai", "Tái lập precision từ mẫu 300 cạnh công khai"),
    "bundle": ("bongda.core.ban_giao", "Đóng gói hoặc kiểm tra một snapshot"),
    "restore": ("bongda.data.khoi_phuc_goi", "Khôi phục dữ liệu từ các ZIP bàn giao"),
    "verify-a7": ("bongda.a7.verify_public", "Kiểm tra kết quả nghiệm thu và biên bản Neo4j A7"),
    "score-a7": ("bongda.a7.duyet", "Chấm bốn loại quan hệ trên các lô báo đã khóa"),
    "build-a7": ("bongda.a7.release", "Dựng A7 từ A6.3 và các sự kiện đã đối chiếu"),
    "import-a7": ("bongda.a7.import_graph", "Nhập và đối chiếu A7 hai lượt trên Neo4j"),
    "extract-a7": ("nlp_bao/bao_su_kien.py", "Trích sự kiện từ báo qua Gemini"),
    "build-a3": ("bongda.graph.tao_a3", "Dựng một snapshot A3 từ A2"),
    "import-a3": ("bongda.storage.nhap_neo4j_a3", "Nhập A3 hai lượt và đối chiếu Neo4j"),
    "build-a5": ("bongda.graph.tao_a5", "Rà thẻ của cán bộ và dựng A5 từ A4"),
    "import-a5": ("bongda.storage.nhap_neo4j_a5", "Nhập A5 hai lượt vào Neo4j riêng"),
    "extract-news": ("nlp_bao/trich_xuat.py", "Kiểm tra và bổ sung quan hệ từ báo qua Gemini"),
    "score-news": ("nlp_bao/danh_gia.py", "Chấm các quan hệ từ báo trên bộ nhãn"),
    "replay-news": ("nlp_bao/chuan_hoa_lai.py", "Chuẩn hóa lại các phản hồi đã lưu"),
    "compare-callups": ("nlp_bao/so_sanh_trieu_tap.py", "So sánh trước/sau trên cùng phản hồi Gemini"),
    "inspect-db": ("bongda.storage.kiem_tra_neo4j_a3", "Đọc thống kê và dấu kiểm của Neo4j"),
}


def main():
    parser = argparse.ArgumentParser(
        prog="python -m bongda",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {name:<12} {help_text}" for name, (_, help_text) in COMMANDS.items()),
    )
    parser.add_argument("command", choices=COMMANDS, metavar="LỆNH")
    command = parser.parse_args(sys.argv[1:2]).command
    target = COMMANDS[command][0]
    if target.endswith(".py"):
        # Giữ môi trường import và checksum của các chương trình Gemini đã khóa.
        os.execv(sys.executable, [sys.executable, str(ROOT / target), *sys.argv[2:]])
    # Mô-đun đích tự xử lý đối số và mã thoát như khi chạy trực tiếp bằng python -m.
    sys.argv = [f"{parser.prog} {command}", *sys.argv[2:]]
    runpy.run_module(target, run_name="__main__")


if __name__ == "__main__":
    main()
