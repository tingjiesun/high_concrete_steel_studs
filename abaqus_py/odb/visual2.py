import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_curve(csv_path: Path):
    u3_values = []
    rf3_values = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(row for row in f if row.strip())
        for row in reader:
            u3_values.append(abs(float(row["U3_raw"])))
            rf3_values.append(abs(float(row["RF3_raw"])) / 1000.0)

    return u3_values, rf3_values


def plot_curve(csv_path: Path, output_path: Path):
    u3_values, rf3_values = read_curve(csv_path)

    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=150)
    ax.plot(u3_values, rf3_values, color="#1f4e8c", linewidth=2.0)

    ax.set_xlabel("|U3|")
    ax.set_ylabel("|RF3| / 1000")
    ax.set_title("U3-RF3 Curve")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.45)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot abs(U3) versus abs(RF3)/1000 from CSV.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=r"D:\temp\U3_RF3_curve.csv",
        help="Path to the CSV file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=r"D:\temp\U3_RF3_curve.png",
        help="Output image path.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    output_path = Path(args.output)
    plot_curve(csv_path, output_path)
    print(f"Saved figure to: {output_path}")


if __name__ == "__main__":
    main()
