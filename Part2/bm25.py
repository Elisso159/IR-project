import math
from elasticsearch import Elasticsearch, helpers
from text_proc import TextProcessing

class OkapiBM25:
	def __init__(self, k1, b, epsilon):
		self.index = "my_inverted_index"
		self.doc_id = "collection_metadata"
		self.password = "********"
		self.total_docs = 0
		self.avg_doc_length = 0.0
		self.doc_length = {}
		self.k1 = k1
		self.b = b
		self.epsilon = epsilon
		self.idf = {}
		self.doc_scores ={}
		
  

	def get_statistics(self):
		es=None
		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", self.password))
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

		numerator =  freq *(self.k1+1)
		denominator = freq + self.k1 *(1-self.b+self.b*(d/self.avg_doc_length))

		tf = numerator/denominator
		#print(f"Tf του εγγράφου {d}:{tf}")

		return tf



	def calc_idf(self, df):
		if df == 0:
			return 0.0

		idf = math.log((self.total_docs-df+0.5)/(df+0.5))
		#print("IDF:",idf)

		return idf 


	def search(self, query_tokens):
		es = None
		doc_scores = {}
		try: 
			es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", self.password))

			res = es.mget(index=self.index, body={"ids": query_tokens})

			idf_sum = 0.0
			neg_idfs=[]
			postings_data = []

			for doc in res.get("docs", []):
				if not doc.get("found"):
					continue

				term_id=doc["_id"]
				source = doc["_source"]
				df = source["df"]
				postings = source["postings"]

				# Υπολογισμός idf για τον όρο
				idf = self.calc_idf(df)
				self.idf[term_id]=idf
				idf_sum += idf

				if idf<0:
					neg_idfs.append(term_id)

				postings_data.append((term_id, postings))

				if len(self.idf)>0:
					average_idf = idf_sum/len(self.idf)
					eps = self.epsilon * average_idf

					for word in neg_idfs:
						self.idf[word] = eps

				for term_id, postings in postings_data:
					idf = self.idf.get(term_id,0.0)

					for posting in postings:
						doc_id = str(posting["doc_id"])
						freq = posting["freq"]

						d = self.doc_length.get(doc_id, self.avg_doc_length)
						
						# Υπολογισμός tf
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


	def normalize_result(self, results):
		if not results:
			return []

		scores = [score for doc_id, score in results]
		min_score = min(scores)
		max_score = max(scores)

		if max_score == min_score:
			return [(doc_id, 1.0) for doc_id, score in results]

		normalized_results = []
		for doc_id, score in results:
			norm_score = (score - min_score)/(max_score - min_score)
			normalized_results.append((doc_id, norm_score))

		return normalized_results

			

if __name__=="__main__":

	q = TextProcessing()
	query_tokens = q.get_query_user()

	my_bm25 = OkapiBM25(1.2, 0.85, 0.01)
	my_bm25.get_statistics()

	results = my_bm25.search(query_tokens)
	normalized_results = my_bm25.normalize_result(results)
	print("Scores: ")
	for doc_id, score in normalized_results:
		print(f"Document ID: {doc_id} Score: {score:.4f}")
