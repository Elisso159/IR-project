import math
from elasticsearch import Elasticsearch, helpers
from text_proc import TextProcessing

class VSM:
	def __init__(self):
		self.index = "my_inverted_index"
		self.password = "********"
		self.doc_id = "collection_metadata"
		self.total_docs = 0
		self.avg_doc_length = 0.0
		self.doc_length = {}
		self.doc_max_freq = {}

	def get_statistics(self):
		es = None
		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", self.password))
			res = es.get(index=self.index, id=self.doc_id)
			metadata_doc = res["_source"]

			self.total_docs = metadata_doc.get("total_docs")
			self.avg_doc_length = round(metadata_doc.get("avg_doc_length"), 1)
			self.doc_length = metadata_doc.get("doc_length")
			self.doc_max_freq = metadata_doc.get("doc_max_freq", {})
	
		except Exception as e:
			print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)
		
		finally:
			if es:
				es.close()


	def calc_tf(self, freq, doc_id):
		#Normalized tf 
		return float(freq)/ float(self.doc_max_freq.get(str(doc_id),1))

	def calc_idf(self, df):
		if df == 0 or self.total_docs == 0:
			return 0.0
		return math.log(self.total_docs / df)

	def search(self, query_tokens):
		es = None
		doc_vector = {}
		query_vector = {}
		query_token_counts = {}

		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", self.password))
			
			# Μέτρηση συχνοτήτων των όρων του query
			for token in query_tokens:
				query_token_counts[token] = query_token_counts.get(token, 0) + 1

			unique_query_tokens = list(set(query_tokens))

			
			res = es.mget(index=self.index, body={"ids": unique_query_tokens})

			for doc in res.get("docs", []):
				# Αν δεν βρει αρχείο
				if not doc.get("found"):
					continue

				source = doc["_source"]
				token = source.get("term")
				df = source.get("df")
				postings = source.get("postings", [])

				idf = self.calc_idf(df)

				if token in query_token_counts:
					query_tf = query_token_counts[token]
					query_vector[token] = query_tf * idf 

				for posting in postings:
					doc_id = str(posting["doc_id"])
					freq = posting["freq"]

					tf = self.calc_tf(freq, doc_id)
					weight = tf * idf

					if doc_id not in doc_vector:
						doc_vector[doc_id] = {}
					doc_vector[doc_id][token] = weight

			# Υπολογισμός Cosine 
			query_magnitude = math.sqrt(sum(w ** 2 for w in query_vector.values()))
			if query_magnitude == 0:
				return []

			doc_scores = {}
			for doc_id, terms_weights in doc_vector.items():
				dot_product = sum(query_vector.get(t, 0) * w for t, w in terms_weights.items())
				doc_magnitude = math.sqrt(sum(w ** 2 for w in terms_weights.values()))

				if doc_magnitude > 0:
					score = dot_product / (query_magnitude * doc_magnitude)
				else:
					score = 0.0
				
				doc_scores[doc_id] = score

			# Ταξινόμηση και επιστροφή των top 10
			ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
			return ranked_docs[:10]

		except Exception as e:
			print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)
			return []
		
		finally:
			if es:
				es.close()

if __name__ == "__main__":
	q = TextProcessing()
	query_tokens = q.get_query_user()

	my_vsm = VSM()
	my_vsm.get_statistics()
	
	results = my_vsm.search(query_tokens)
	print("VSM Scores:")
	for doc_id, score in results:
		print(f"Document ID: {doc_id} Score: {score:.1f}")
