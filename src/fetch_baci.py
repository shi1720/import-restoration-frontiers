"""Retrieve official BACI ZIP members using HTTP ranges; retain only research baskets."""

from pathlib import Path
import requests, struct, concurrent.futures as cf, zlib, io, csv, json, hashlib, time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
URL = "https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS17_V202601.zip"
PRODUCTS = {"100199", "100590", "100390", "120190", "151211", "310210"}


def get(a, b):
    for attempt in range(5):
        try:
            r = requests.get(URL, headers={"Range": f"bytes={a}-{b}"}, timeout=90)
            r.raise_for_status()
            if r.status_code != 206 or len(r.content) != b - a + 1:
                raise ValueError((r.status_code, len(r.content), b - a + 1))
            return r.content
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def main():
    total = int(requests.head(URL, timeout=30).headers["Content-Length"])
    start = total - 65536
    tail = get(start, total - 1)
    p = tail.rfind(b"PK\x05\x06")
    end = struct.unpack("<4s4H2LH", tail[p : p + 22])
    cd = tail[end[6] - start : p]
    members = {}
    i = 0
    while cd[i : i + 4] == b"PK\x01\x02":
        h = struct.unpack("<4s6H3L5H2L", cd[i : i + 46])
        n, x, c = h[10:13]
        name = cd[i + 46 : i + 46 + n].decode()
        members[name] = (h[8], h[-1], h[7])
        i += 46 + n + x + c
    manifest = {
        "url": URL,
        "size": total,
        "etag": requests.head(URL, timeout=30).headers.get("ETag"),
        "products": sorted(PRODUCTS),
        "members": {},
    }
    existing = DATA / "source_manifest.json"
    if existing.exists():
        prior = json.loads(existing.read_text())
        if prior.get("etag") != manifest.get("etag"):
            raise RuntimeError(
                "Official archive ETag changed; investigate the data revision before overwriting the snapshot."
            )
        manifest = prior
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2017, 2018]
    for year in years + ["country", "product"]:
        name = next(
            n
            for n in members
            if (
                f"Y{year}_" in n
                if isinstance(year, int)
                else n.startswith(year + "_codes")
            )
        )
        size, offset, crc = members[name]
        local = get(offset, offset + 29)
        h = struct.unpack("<4s5H3L2H", local)
        pos = offset + 30 + h[-2] + h[-1]
        target = DATA / (f"baci_selected_{year}.csv" if isinstance(year, int) else name)
        if target.exists():
            if (
                name not in manifest["members"]
                or hashlib.sha256(target.read_bytes()).hexdigest()
                != manifest["members"][name]["sha256_selected"]
            ):
                raise ValueError("Cached data checksum mismatch: " + target.name)
            print("verified cache", target.name, flush=True)
            continue
        step = 1024 * 1024
        ranges = [
            (a, min(a + step - 1, pos + size - 1)) for a in range(pos, pos + size, step)
        ]
        print("fetch", name, len(ranges), "chunks", flush=True)
        with cf.ThreadPoolExecutor(max_workers=24) as pool:
            chunks = list(pool.map(lambda ab: get(*ab), ranges))
        raw = zlib.decompress(b"".join(chunks), -15)
        if zlib.crc32(raw) != crc:
            raise ValueError("ZIP CRC failure")
        manifest["members"][name] = {
            "sha256_uncompressed": hashlib.sha256(raw).hexdigest(),
            "zip_crc32": crc,
        }
        if isinstance(year, int):
            inp = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            count = 0
            with target.open("w") as f:
                w = csv.DictWriter(f, fieldnames=inp.fieldnames)
                w.writeheader()
                for row in inp:
                    if row["k"].zfill(6) in PRODUCTS:
                        w.writerow(row)
                        count += 1
            print("saved", year, count, flush=True)
        else:
            target.write_bytes(raw)
        manifest["members"][name]["sha256_selected"] = hashlib.sha256(
            target.read_bytes()
        ).hexdigest()
        (DATA / "source_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("complete", flush=True)


if __name__ == "__main__":
    main()
