from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
from typing import Any


@dataclass(frozen=True)
class SensorPacket:
    """Transport-neutral timestamped sensor message used by the SIL/HIL layer.

    `timestamp_s` is simulation/sensor time, not wall-clock time.  The payload is
    intentionally JSON-friendly so hardware adapters can be implemented in other
    languages without importing the Python package.
    """

    sensor: str
    timestamp_s: float
    sequence: int
    values: dict[str, float]
    frame: str = "local_xy"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SensorPacket":
        required = {"sensor", "timestamp_s", "sequence", "values"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"missing packet fields: {sorted(missing)}")
        return cls(
            sensor=str(data["sensor"]),
            timestamp_s=float(data["timestamp_s"]),
            sequence=int(data["sequence"]),
            values={str(k): float(v) for k, v in dict(data["values"]).items()},
            frame=str(data.get("frame", "local_xy")),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> "SensorPacket":
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return cls.from_dict(json.loads(raw))
