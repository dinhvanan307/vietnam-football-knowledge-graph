"""Các lệnh thường dùng khi làm việc từ gốc repository."""
import argparse
import runpy
import sys

COMMANDS = {
    "verify": ("bongda.evaluate.overall.kiem_tra_cong_khai", "Tái lập precision từ mẫu 300 cạnh công khai"),
    "bundle": ("bongda.core.ban_giao", "Đóng gói hoặc kiểm tra một snapshot"),
    "restore": ("bongda.data.khoi_phuc_goi", "Khôi phục dữ liệu từ các ZIP bàn giao"),
    "build-a3": ("bongda.graph.tao_a3", "Dựng một snapshot A3 từ A2"),
    "import-a3": ("bongda.storage.nhap_neo4j_a3", "Nhập A3 hai lượt và đối chiếu Neo4j"),
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
    # Mô-đun đích tự xử lý đối số và mã thoát như khi chạy trực tiếp bằng python -m.
    sys.argv = [f"{parser.prog} {command}", *sys.argv[2:]]
    runpy.run_module(COMMANDS[command][0], run_name="__main__")


if __name__ == "__main__":
    main()
