import math
from elasticsearch import Elasticsearch, helpers
from text_proc import TextProcessing

class BM25:
	def __init__(self, k1, b):
		self.index = "my_inverted_index"
		self.doc_id = "collection_metadata"
		self.total_docs = 0
		self.avg_doc_length = 0.0
		self.doc_length = {}
		self.k1 = k1
		self.b = b
		self.idf = {}
		self.doc_scores ={}
		
  

	def get_statistics(self):
		es=None
		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", "*******"))
			res = es.get(index=self.index, id=self.doc_id)
			metadata_doc = res["_source"]

			self.total_docs = metadata_doc.get("total_docs")
			self.avg_doc_length=round(metadata_doc.get("avg_doc_length"),1)
			self.doc_length = metadata_doc.get("doc_length")

			'''print("Συνολικά έγγραφα:", self.total_docs)
			print("Μέσο μήκος εγγράφου:", self.avg_doc_length)
			print("Μήκος ανά έγγραφο (dict):", self.doc_length)'''
	
		except Exception as e:
			print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)
		
		finally:
			if es:
				es.close()

	def calc_tf(self, freq, d):
		if self.avg_doc_length == 0:
			return 0.0

		numerator =  freq
		denominator = freq + self.k1 *(1-self.b+self.b*(d/self.avg_doc_length))

		tf = numerator/denominator
		#print(f"Tf του εγγράφου {d}:{tf}")

		return tf



	def calc_idf(self, df):
		if df == 0:
			return 0.0

		idf = max(math.log((self.total_docs-df+0.5)/(df+0.5)),0.0)
		#print("IDF:",idf)

		return idf 


	def search(self, query_tokens):
		es = None
		doc_scores = {}
		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", "******"))
			
			res = es.mget(index=self.index, body={"ids": query_tokens})

			for doc in res.get("docs", []):
				if not doc.get("found"):
					continue

				source = doc["_source"]
				df = source["df"]
				postings = source["postings"]

				# Υπολογισμός IDF για τον όρο
				idf = self.calc_idf(df)

				for posting in postings:
					doc_id = str(posting["doc_id"])
					freq = posting["freq"]

					d = self.doc_length.get(doc_id, self.avg_doc_length)
					
					# Υπολογισμός TF
					tf = self.calc_tf(freq, d)

					score_part = idf * tf
					doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score_part

			# Ταξινόμηση αποτελεσμάτων κατά φθίνουσα σειρά score
			ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
			return ranked_docs[:10]

		except Exception as e:
			print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)
			return []
		
		finally:
			if es:
				es.close()
			

if __name__=="__main__":

	q = TextProcessing()
	query_tokens = q.get_query_user()

	bm25 = BM25(1.25, 0.75)
	bm25.get_statistics()

	results = bm25.search(query_tokens)
	print("Scores: ")
	for doc_id, score in results:
		print(f"Document ID: {doc_id} | Score: {score:.4f}")
