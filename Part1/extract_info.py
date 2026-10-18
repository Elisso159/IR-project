import os
import re
from elasticsearch import Elasticsearch, helpers

# Συνάρτηση που φορτώνουμε τα αρχεία και τα κάνουμε map κάθε πεδίο 
def get_cf(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as cff:
        content = cff.read()

    raw_data = re.split(r'\n(?=PN)', content)

    field_map = {
        'PN': 'pn',
        'RN': 'rn',
        'AN': 'an',
        'AU': 'au',
        'TI': 'ti',
        'SO': 'so',
        'MJ': 'mj',
        'MN': 'mn',
        'AB': 'ab_ex',
        'RF': 'rf',
        'CT': 'ct'
    }

    data = []

    for raw in raw_data:
        if not raw.strip():
            continue
        d = {}

        lines = raw.split('\n')
        current_tag = None
        current_val = []

        for line in lines:
            tag_match = re.match(r'^([A-Z]{2}|AB/EX)\s+(.*)', line)
            if tag_match:
                if current_tag and current_tag in field_map:
                    field_name = field_map[current_tag]
                    d[field_name] = " ".join(current_val).strip()

                tag, val = tag_match.groups()
                current_tag = tag if tag != 'AB/EX' else 'AB'
                current_val = [val]
            else:
                if current_tag:
                    current_val.append(line.strip())

        if current_tag and current_tag in field_map:
            d[field_map[current_tag]] = " ".join(current_val).strip()

        if 'rn' in d:
            try:
                d['rn'] = int(d['rn'])
            except ValueError:
                pass

        if d:
            data.append(d)

    return data

try:
    es = Elasticsearch("http://localhost:9200")
    info = es.info()
    print("Success!")
    
    index_name = "cystic_fibrosis"

    mapping = {
        "mappings": {
            "properties": {
                "pn": {"type": "keyword"},
                "rn": {"type": "integer"},
                "an": {"type": "keyword"},
                "au": {"type": "text"},
                "ti": {"type": "text"},
                "so": {"type": "text"},
                "mj": {"type": "text"},
                "mn": {"type": "text"},
                "ab_ex": {"type": "text"},
                "rf": {"type": "text"},
                "ct": {"type": "text"}
            }
        }
    }

    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=mapping)
        print(f"Το index '{index_name}' δημιουργήθηκε")

    base_dir = "/home/totoro/Έγγραφα/University/Seventh_Semester/Ανάκτηση_Πληροφορίας/Project/cfc"
    
    file_names = ['cf74', 'cf75', 'cf76', 'cf77', 'cf78', 'cf79']
    file_paths = [os.path.join(base_dir, f) for f in file_names]

    documents = []

    for file in file_paths:
        print(f"Διαβάζεται το αρχείο: {file}")
        documents.extend(get_cf(file))

    #Φόρτωση αρχείων στην elastic search 
    actions = [
        {
            "_index": index_name,
            "_id": doc.get("rn"),  
            "_source": doc
        }
        for doc in documents
    ]

    success, _ = helpers.bulk(es, actions)
    print(f"Επιτυχής εισαγωγή {success} εγγράφων στο Elasticsearch!")

except Exception as e:
    print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)