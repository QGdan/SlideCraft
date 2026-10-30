"""Local raster asset registration: origin and declared license are explicit."""
import hashlib
from pathlib import Path
from PIL import Image
from .qa.common import CheckResult


def register_asset(path, *, asset_id, source_id, license_note):
    path=Path(path).resolve()
    if not license_note.strip():raise ValueError("Declared license/permission note required")
    with Image.open(path) as im:
        im.load();width,height=im.size
    return dict(id=asset_id,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_id=source_id,
                license_note=license_note,width_px=width,height_px=height)


def check_assets(deck):
    r=CheckResult(evaluated=["registered-raster-assets-integrity-and-origin"])
    assets={a["id"]:a for a in deck.get("assets",[])};sources={s["id"] for s in deck["sources"]}
    if len(assets)!=len(deck.get("assets",[])):r.add("duplicate-asset","Asset IDs must be unique")
    for asset in assets.values():
        try:
            actual=register_asset(asset["path"],asset_id=asset["id"],source_id=asset["source_id"],license_note=asset["license_note"])
            if actual!=asset:r.add("asset-integrity","Raster asset no longer matches registered metadata")
            if asset["source_id"] not in sources:r.add("asset-origin","Asset source ID is not registered")
        except Exception as exc:r.add("asset-unavailable",str(exc))
    for page in deck["slides"]:
        for e in page["elements"]:
            if e["type"]!="image":continue
            a=assets.get(e.get("asset_id"))
            if not a or Path(a["path"]).resolve()!=Path(e["asset_path"]).resolve():r.add("unregistered-raster-asset","Image requires a matching asset_id and path",slide_id=page["id"],element_id=e["id"])
            elif a["source_id"] not in page["source_refs"]:r.add("asset-source-not-cited","Image source absent from slide references",slide_id=page["id"],element_id=e["id"])
    return r
