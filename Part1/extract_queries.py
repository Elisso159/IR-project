import os
import re
from elasticsearch import Elasticsearch, helpers

def relevance_paper(text):
    relevance = []
    tokens = text.split()

    i = 0
    while i < len(tokens) - 1:
        doc_id = tokens[i]      
        temp = tokens[i+1]

        scores = [int(t) for t in temp]
        relevance.append({"doc_id": doc_id, "scores": scores}) 
        i += 2

    return relevance

def get_cf(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as cff:
        content = cff.read()

    # Χωρισμός αρχείου σε κάθε query
    raw_data = re.split(r'\n(?=QN)', content)

    # Map κάθε section
    field_map = {
        'QN': 'qn',
        'QU': 'qu',
        'NR': 'nr',
        'RD': 'rd',
    }

    data = []

    for raw in raw_data:
        if not raw.strip():
            continue

        d = {}
        lines = raw.split('\n')
        current_key = None
        current_val = []

        for line in lines:
            if len(line) >= 3 and line[:2] in field_map and line[2] == " ":
                if current_key:
                    val = " ".join(current_val).strip()
                    if current_key == "rd":
                        d[current_key] = relevance_paper(val)
                    else:
                        d[current_key] = val

                current_key = field_map[line[:2]]
                current_val = [line[3:].strip()]
            else:
                if current_key:
                    current_val.append(line.strip())

        # Επεξεργασία και για το τελευταίο πεδίο 
        if current_key:
            val = " ".join(current_val).strip()
            if current_key == "rd":
                d[current_key] = relevance_paper(val)
            else:
                d[current_key] = val

        if d and "qn" in d:
            data.append(d)

    return data

try:
    # Σύνδεση με Elasticsearch 
    es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", "*******"))
    info = es.info()
    print("Επιτυχής σύνδεση")
    
    index_name = "query_index"

    mapping = {
        "mappings": {
            "properties": {
                "qn": {"type": "keyword"},
                "qu": {"type": "text"},
                "nr": {"type": "keyword"},
                "rd": {
                    "type": "nested", 
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "scores": {"type": "integer"},  
                    },
                },
            }
        }
    }

    # Δημιουργία Index στη βάση
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, body=mapping)
    print(f"Το index '{index_name}' δημιουργήθηκε με επιτυχία.")

    # Ανάγνωση αρχείου
    base_dir = "/home/totoro/Έγγραφα/University/Seventh_Semester/Ανάκτηση_Πληροφορίας/Project/cfc"
    file_name = 'cfquery' 
    file_path = os.path.join(base_dir, file_name)

    # Ανάκτηση δεδομένων ερωτημάτων
    documents = get_cf(file_path)

    print(f"Συνολικά συλλέχθηκαν {len(documents)} queries από το αρχείο")


    queries = []
    for doc in documents:
        doc_id = doc.get("qn")
        if doc_id and not es.exists(index=index_name, id=doc_id):
            queries.append({
                "_index": index_name,
                "_id": doc_id,  
                "_source": doc
            })

    if queries:
        success, _ = helpers.bulk(es, queries)
        print(f"Επιτυχής εισαγωγή {success} ερωτημάτων")
    else:
        print("Όλα τα ερωτήματα υπάρχουν ήδη ή η λίστα είναι κενή")

except Exception as e:
    print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)

finally:
    es.close()
