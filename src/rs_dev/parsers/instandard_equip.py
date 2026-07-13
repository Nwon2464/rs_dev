"""Pure MessagePack parser for InstandardEquip.dat."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from rs_dev.models.instandard_equipment import ParsedInstandardEquip


class MessagePackDecoder:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise ValueError(f"truncated MessagePack value at {self.offset:#x}")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def uint(self, size: int) -> int:
        return int.from_bytes(self.read(size), "big")

    @staticmethod
    def decode_text(raw: bytes) -> str:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("cp949")

    def value(self) -> Any:
        code = self.uint(1)
        if code <= 0x7F: return code
        if code >= 0xE0: return code - 0x100
        if 0xA0 <= code <= 0xBF: return self.decode_text(self.read(code & 0x1F))
        if 0x90 <= code <= 0x9F: return [self.value() for _ in range(code & 0x0F)]
        if 0x80 <= code <= 0x8F: return {self.value(): self.value() for _ in range(code & 0x0F)}
        if code == 0xC0: return None
        if code == 0xC2: return False
        if code == 0xC3: return True
        if code == 0xCA: return struct.unpack(">f", self.read(4))[0]
        if code == 0xCB: return struct.unpack(">d", self.read(8))[0]
        if 0xCC <= code <= 0xCF: return self.uint((1, 2, 4, 8)[code - 0xCC])
        if 0xD0 <= code <= 0xD3:
            size = (1, 2, 4, 8)[code - 0xD0]
            return int.from_bytes(self.read(size), "big", signed=True)
        if 0xD9 <= code <= 0xDB:
            return self.decode_text(self.read(self.uint((1, 2, 4)[code - 0xD9])))
        if code in (0xDC, 0xDD):
            return [self.value() for _ in range(self.uint((2, 4)[code - 0xDC]))]
        if code in (0xDE, 0xDF):
            return {self.value(): self.value() for _ in range(self.uint((2, 4)[code - 0xDE]))}
        if 0xC4 <= code <= 0xC6:
            return self.read(self.uint((1, 2, 4)[code - 0xC4]))
        raise ValueError(f"unsupported MessagePack code {code:#x} at {self.offset - 1:#x}")

    def unpack(self) -> Any:
        result = self.value()
        if self.offset != len(self.data):
            raise ValueError(f"trailing MessagePack bytes: decoded={self.offset}, size={len(self.data)}")
        return result


def parse_instandard_equip(path: Path) -> ParsedInstandardEquip:
    decoded = MessagePackDecoder(path.read_bytes()).unpack()
    expected = {"DisJointData", "MaterialData", "OptionData", "OptionsByItemType", "PrefixTagName"}
    if set(decoded) != expected:
        raise ValueError(f"unexpected top-level fields: {sorted(decoded)}")
    return ParsedInstandardEquip.model_validate(decoded)
