from pathlib import Path
import json, re
from rank_bm25 import BM25Okapi

class LocalRAG:
    """BM25 retriever over pre-built data/index/chunks.jsonl with citation tags."""
    def __init__(self, index_path="backend/data/index/chunks.jsonl"):
        path = Path(index_path)
        if not path.exists():
            # Fallback mini-guides if no index yet
            self.recs = [
                {"id":"guide-001","domain":"ics","source_title":"ics_201_intro","chunk":"ICS-201 brief: Situation, Objectives, Org, Resources, Safety, Comms."},
                {"id":"guide-002","domain":"sphere","source_title":"wash_minimums","chunk":"Safe water point; handwashing at critical points; sanitation distance; queue management; chlorine guidance."},
            ]
        else:
            self.recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        docs = [r["chunk"] for r in self.recs]
        self.tok = [re.findall(r"[a-z0-9]+", d.lower()) for d in docs]
        self.bm25 = BM25Okapi(self.tok)

    def _tok(self, s): 
        return re.findall(r"[a-z0-9]+", s.lower())

    def topk(self, query: str, k=5, prefer=("sphere","ics","who","fema","ifrc")):
        scores = self.bm25.get_scores(self._tok(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        cand = [self.recs[i] for i in order[:k*2]]
        cand.sort(key=lambda r: 0 if r["domain"] in prefer else 1)
        return cand[:k]

    def blurbs(self, recs):
        lines=[]
        for r in recs:
            tag = f"[{r['domain'].upper()} | {r['source_title']} | {r['id']}]"
            lines.append(f"{tag} {r['chunk']}")
        return "\n\n".join(lines)

    def cite_ids(self, recs):
        return [f"{r['domain']}:{r['source_title']}#{r['id']}" for r in recs]
