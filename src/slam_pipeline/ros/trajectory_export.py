"""Export optimized camera poses from an RTAB-Map SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np

from ..evaluation.trajectory import poses_to_tum


def read_rtabmap_trajectory(database: str | Path) -> tuple[np.ndarray, list[np.ndarray]]:
    connection = sqlite3.connect(str(database))
    rows = connection.execute("SELECT stamp, pose FROM Node WHERE pose IS NOT NULL ORDER BY stamp, id").fetchall()
    connection.close()
    if not rows:
        raise ValueError(f"RTAB-Map database contains no node poses: {database}")
    timestamps = np.asarray([float(row[0]) for row in rows], dtype=np.float64)
    poses = []
    for _, blob in rows:
        values = np.frombuffer(blob, dtype=np.float32)
        if values.size != 12:
            raise ValueError(f"Unexpected RTAB-Map pose blob size: {values.size}")
        pose = np.eye(4, dtype=np.float64)
        pose[:3, :] = values.reshape(3, 4)
        poses.append(pose)
    return timestamps, poses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    timestamps, poses = read_rtabmap_trajectory(args.database)
    poses_to_tum(timestamps, poses, args.output)
    print(f"Exported {len(poses)} poses to {args.output}")


if __name__ == "__main__":
    main()
