import re
from collections import defaultdict

class InvIndexing:
    def __init__(self, fields=[]):
        self.fields = fields
        self.index = defaultdict(dict)  

    def build_indexing(self, docs):
        self.index.clear()

        for d in docs:
            doc_id = d.get("rn")

            if doc_id is None:
                continue

            information = [str(d.get(field, '')) for field in self.fields]
            text = " ".join(information)

            tokens = re.findall(r'\b\w+\b', text.lower())

            term_freqs = {}
            for token in tokens:
                term_freqs[token] = term_freqs.get(token, 0) + 1

            for token, freq in term_freqs.items():
                self.index[token][doc_id] = freq

    def search(self, word):
        word = word.lower()
        return self.index.get(word, {})
