"""Immutable font resolutions. Table metrics are estimates, not shaping."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import re
from types import MappingProxyType
from fontTools.ttLib import TTFont, TTCollection

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff]")


@dataclass(frozen=True)
class FontFace:
    requested: str
    family: str
    path: str | None
    index: int
    bold: bool
    italic: bool
    substituted: bool
    style_missing: bool
    units: int
    ascent: int
    descent: int
    cmap: object
    advances: object

    def measure(self, text, size_pt):
        total = 0.0
        missing = []
        for character in text:
            if character in "\n\r\v":
                continue
            glyph = self.cmap.get(ord(character))
            if glyph is None:
                missing.append(character)
                total += (1.0 if CJK.search(character) else 0.55) * self.units
            else:
                total += self.advances.get(glyph, 0)
        return total * size_pt / self.units, tuple(sorted(set(missing)))

    @property
    def line_ratio(self):
        return (self.ascent+self.descent)/self.units


def font_directories():
    if os.name == "nt":
        return [Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts",
                Path(os.environ.get("LOCALAPPDATA",""))/"Microsoft/Windows/Fonts"]
    return [Path("/usr/share/fonts"),Path("/usr/local/share/fonts"),Path.home()/".local/share/fonts",
            Path("/System/Library/Fonts"),Path("/Library/Fonts")]


def names_for(font):
    names = set()
    preferred = []
    for record in font["name"].names:
        if record.nameID not in {1,16}:
            continue
        try:
            value = record.toUnicode().strip()
        except Exception:
            continue
        if value:
            names.add(value)
            if record.nameID == 16 or record.langID == 0x409:
                preferred.append(value)
    return names, (preferred[0] if preferred else sorted(names)[0] if names else "Unknown")


class FontResolver:
    def __init__(self, directories=None):
        self.directories = tuple(str(p) for p in (directories if directories is not None else font_directories()))
        self._index = None

    def index(self):
        if self._index is None:
            index = {}
            for folder in self.directories:
                path = Path(folder)
                if not path.is_dir():
                    continue
                for filename in sorted(path.rglob("*")):
                    if filename.suffix.lower() not in {".ttf",".otf",".ttc",".otc"}:
                        continue
                    collection = None
                    try:
                        if filename.suffix.lower() in {".ttc",".otc"}:
                            collection = TTCollection(str(filename),lazy=True)
                            faces = collection.fonts
                        else:
                            faces = [TTFont(str(filename),lazy=True)]
                        for number,font in enumerate(faces):
                            aliases,family = names_for(font)
                            os2 = font.get("OS/2")
                            flags = int(os2.fsSelection) if os2 else 0
                            bold = bool(flags & 32) or (bool(os2) and os2.usWeightClass >= 600)
                            italic = bool(flags & 1)
                            for alias in aliases:
                                index.setdefault(alias.casefold(),[]).append((str(filename),number,family,bold,italic))
                        if collection:
                            collection.close()
                        else:
                            faces[0].close()
                    except Exception:
                        continue
            self._index = index
        return self._index

    @lru_cache(maxsize=512)
    def resolve(self, family, bold=False, italic=False, cjk=False):
        requested = family or ("Microsoft YaHei" if cjk else "Calibri")
        index = self.index()
        choices = index.get(requested.casefold())
        substituted = not bool(choices)
        if not choices:
            fallbacks = ["Microsoft YaHei","Noto Sans CJK SC","SimSun"] if cjk else ["Calibri","Arial","Liberation Sans","DejaVu Sans"]
            choices = next((index[n.casefold()] for n in fallbacks if n.casefold() in index), [])
        if not choices:
            return FontFace(requested,"synthetic",None,0,bold,italic,True,True,1000,950,270,MappingProxyType({}),MappingProxyType({}))
        path,number,resolved,actual_bold,actual_italic = min(choices,key=lambda row: 2*(row[3]!=bold)+(row[4]!=italic))
        metrics = load_metrics(path,number)
        return FontFace(requested,resolved,path,number,actual_bold,actual_italic,substituted,
                        actual_bold!=bold or actual_italic!=italic,*metrics)


@lru_cache(maxsize=512)
def load_metrics(path, number):
    font = TTFont(path,fontNumber=number,lazy=False)
    try:
        units = int(font["head"].unitsPerEm)
        os2 = font.get("OS/2")
        ascent = int(os2.usWinAscent) if os2 else int(font["hhea"].ascent)
        descent = int(os2.usWinDescent) if os2 else abs(int(font["hhea"].descent))
        cmap = MappingProxyType(dict(font.getBestCmap() or {}))
        advance = MappingProxyType({key:value[0] for key,value in font["hmtx"].metrics.items()})
        return units,ascent,descent,cmap,advance
    finally:
        font.close()


DEFAULT_RESOLVER = FontResolver()
