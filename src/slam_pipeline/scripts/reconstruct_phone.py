"""Reconstruct an Android phone recording directly from ARCore poses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..dataset.phone_dataset import load_phone_dataset
from ..reconstruction.tsdf import reconstruct_tsdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/phone_default.yaml"))
    args = parser.parse_args()
    dataset = load_phone_dataset(args.recording)
    result = reconstruct_tsdf(dataset, args.output, voxel_length=0.02, sdf_trunc=0.04, output_prefix="phone")
    result["recording"] = str(args.recording)
    result["config"] = str(args.config)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "phone_tsdf_stats.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
