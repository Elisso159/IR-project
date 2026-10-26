import math
import re
from collections import defaultdict
from elasticsearch import Elasticsearch, helpers

class InvIndexing:
    def __init__(self, fields=[]):
        self.fields = fields
        self.index = defaultdict(dict)  
        self.docs_length = {}
        self.total_docs = 1239
        self.avg_doc_length = 0.0
        self.index_name = "my_inverted_index"
  
    def build_indexing(self, docs):
        self.index.clear()
        self.docs_length.clear()
        total_length = 0

        for d in docs:
            doc_id = d.get("rn")

            if doc_id is None:
                continue

            information = [str(d.get(field, '')) for field in self.fields]
            text = " ".join(information)

            tokens = re.findall(r'\b\w+\b', text.lower())

            doc_len = len(tokens)
            self.docs_length[doc_id] = doc_len
            total_length += doc_len

            # Term frequency 
            term_freqs = {}
            for token in tokens:
                term_freqs[token] = term_freqs.get(token, 0) + 1

            for token, freq in term_freqs.items():
                self.index[token][doc_id] = freq

        # Υπολογισμός μέσου όρου
        if self.total_docs > 0:
            self.avg_doc_length = total_length / self.total_docs


    def save_index_to_elastic_search(self):
        es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", "******"))
        try:
            if es.indices.exists(index=self.index_name):
                es.indices.delete(index=self.index_name)

            es.indices.create(
                index=self.index_name,
                body={
                "settings":{"index.mapping.total_fields.limit": 5000},
                "mappings": {
                        "properties": {
                            "term": {"type": "keyword"},
                            "df": {"type": "integer"},
                            "postings": {"type": "nested"}
                        }
                    }
                }
            )

            index_actions = []
            for term, postings_dict in self.index.items():
                postings_list = [{"doc_id": doc_id, "freq": freq} for doc_id, freq in postings_dict.items()]
                term_document = {
                    "term": term,
                    "df": len(postings_dict),
                    "postings": postings_list
                }
                index_actions.append({
                    "_index": self.index_name,
                    "_id": term,
                    "_source": term_document
                })

            if index_actions:
                success, _ = helpers.bulk(es, index_actions)
                print("Επιτυχής εισαγωγή του Inverted Index")

            metadata_doc = {
                "total_docs": self.total_docs,
                "avg_doc_length": self.avg_doc_length,
                "doc_length": self.docs_length
            }

            es.index(index=self.index_name, id="collection_metadata", body=metadata_doc)
            

        finally:
            es.close()

    def search_word_in_docs(self, word):
        word = word.lower()
        return self.index.get(word, {})
