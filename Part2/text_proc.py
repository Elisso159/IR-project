import re

class TextProcessing:
	def __init__(self):
		pass

	def normalization(self, text):
		text =re.sub(r'[^\w\s]', '', text)
		text = re.sub(r'\s+', ' ', text)
		text = text.lower()

		return text

	def get_query_user(self):
		query = input("Give a question:")
		normalized = self.normalization(query)
		tokens_query = normalized.split()
		print(tokens_query)

		return tokens_query


