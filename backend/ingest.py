import json, hashlib
from pathlib import Path

ROOT = Path("backend/corpus")
OUT  = Path("backend/data/index")
OUT.mkdir(parents=True, exist_ok=True)

def chunk_text(t, max_chars=700, overlap=80):
    t = " ".join(t.split()); out=[]; i=0
    while i < len(t):
        j = min(i+max_chars, len(t))
        k = t.rfind(". ", i, j); k = j if k == -1 or (j-k)>200 else k+1
        out.append(t[i:k].strip()); i = max(k-overlap, k)
    return [c for c in out if c]

def fid(p: Path):
    return hashlib.sha1(str(p).encode()).hexdigest()[:8]

recs=[]
for p in sorted(ROOT.rglob("*.txt")):
    if not p.is_file(): 
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    for n,ch in enumerate(chunk_text(text)):
        recs.append({
          "id": f"{fid(p)}-{n:03d}",
          "domain": p.parts[-2],
          "source_title": p.stem.replace("_"," "),
          "source_path": str(p),
          "chunk": ch
        })

outp = OUT/"chunks.jsonl"
outp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
print(f"wrote {len(recs)} chunks -> {outp}")
