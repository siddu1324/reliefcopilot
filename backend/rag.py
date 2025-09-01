from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

class LocalRAG:
    def __init__(self, folder: str):
        self.paths = list(Path(folder).glob("*.txt"))
        self.docs = [p.read_text(encoding="utf-8")[:8000] for p in self.paths] or \
                    ["ICS quickstart.", "Sphere WASH basics."]
        self.vec = TfidfVectorizer(stop_words="english").fit(self.docs)
        self.mat = self.vec.transform(self.docs)

    def topk(self, query: str, k: int = 3) -> list[str]:
        qv = self.vec.transform([query])
        sims = cosine_similarity(qv, self.mat)[0]
        order = sims.argsort()[::-1][:k]
        outs = []
        for i in order:
            title = self.paths[i].stem.replace("_", " ") if self.paths else f"doc{i}"
            snippet = self.docs[i][:700]
            outs.append(f"[{title}] {snippet}")
        return outs
