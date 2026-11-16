import re
import nltk
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.util import ngrams
from nltk.corpus import stopwords

class TextProcessing:
	def __init__(self):
		self.stemmer = PorterStemmer()
		self.lemmatizer = WordNetLemmatizer()
		self.n = 3
		nltk.download('stopwords', quiet=True)
		self.stop_words = set(stopwords.words('english'))

	def remove_punct(self, text):
		text =re.sub(r'[^\w\s]', '', text)
		text = re.sub(r'\s+', ' ', text)
		text = text.lower()

		return text

	def get_query_user(self):
		query = input("Give a question:")
		raw = self.remove_punct(query)
		tokens_query = raw.split()
		tokens_query = [t for t in tokens_query if t not in self.stop_words]
		tokens_query = self.stemming(tokens_query)
		tokens_query = self.lemmatization(tokens_query)
		tokens_query = self.generate_ngrams(tokens_query)
		print(tokens_query)

		return tokens_query

	def stemming(self, tokens):
		return [self.stemmer.stem(token) for token in tokens]

	def lemmatization(self, tokens):
		return [self.lemmatizer.lemmatize(token) for token in tokens]

	def generate_ngrams(self, tokens):
		ngrams_list = []

		for i in range(1, self.n +1):
			if i==1:
				terms = tokens
			else:
				terms = [" ".join(gram) for gram in ngrams(tokens, i)]

			ngrams_list.extend(terms)

		return ngrams_list
