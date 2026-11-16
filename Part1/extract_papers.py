import os
import re
import unicodedata
import string
from elasticsearch import Elasticsearch, helpers
from inverted_index import InvIndexing
from text_proc import TextProcessing

password = "********"

def get_cf(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as cff:
        content = cff.read()

    # Χωρισμός αρχείου σε κάθε paper
    raw_data = re.split(r'\n(?=PN)', content)

    # Map κάθε section
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

    # Επεξεργασία κάθε paper
    for raw in raw_data:
        if not raw.strip():
            continue

        d = {}
        lines = raw.split('\n')
        current_tag = None
        current_val = []
        tp = TextProcessing()


        for line in lines:
            tag_match = re.match(r'^([A-Z]{2}|AB/EX)\s+(.*)', line)
            if tag_match:
                if current_tag and current_tag in field_map:
                    field_name = field_map[current_tag]
                    d[field_name] = tp.remove_punct(" ".join(current_val).strip())

                tag, val = tag_match.groups()
                current_tag = tag if tag != 'AB/EX' else 'AB'
                current_val = [val]
            else:
                if current_tag:
                    current_val.append(line.strip())

        if current_tag and current_tag in field_map:
            d[field_map[current_tag]] =  tp.remove_punct(" ".join(current_val).strip())

        if 'rn' in d:
            try:
                d['rn'] = int(d['rn'])
            except ValueError:
                pass

        if d:
            data.append(d)

    return data

try:
    #Σύνδεση με Elasticsearch 
    es = Elasticsearch("http://localhost:9200", basic_auth=("elastic", password))
    info = es.info()
    print("Επιτυχής σύνδεση")
    
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

    # Δημιουργία Index στη βάση
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, body=mapping)
    print(f"Το index '{index_name}' δημιουργήθηκε με επιτυχία.")

    # Ανάγνωση αρχείων
    # base_dir = ../data"
    base_dir = "/home/totoro/Έγγραφα/University/Seventh_Semester/Ανάκτηση_Πληροφορίας/Project/cfc"
    file_names = ['cf74', 'cf75', 'cf76', 'cf77', 'cf78', 'cf79']
    file_paths = [os.path.join(base_dir, f) for f in file_names]

    documents = []
    for file in file_paths:
        documents.extend(get_cf(file))

    print(f"Συνολικά συλλέχθηκαν {len(documents)} έγγραφα από τα αρχεία")

    papers = []
    for doc in documents:
        doc_id = doc.get("rn")
        if not es.exists(index=index_name, id=doc_id):
            papers.append({
                "_index": index_name,
                "_id": doc_id,  
                "_source": doc
            })

    if papers:
        success, _ = helpers.bulk(es, papers)
        print(f"Επιτυχής εισαγωγή {success} των εγγράφων")
    else:
        print("Όλα τα έγγραφα υπάρχουν ήδη")

    #Δημιουργία Inverted Index
    invIndex = InvIndexing(fields=('ti', 'ab_ex'))
    invIndex.build_indexing(documents)
    invIndex.save_index_to_elastic_search()

    es.indices.refresh(index="my_inverted_index")

except Exception as e:
    print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)

finally:
    es.close()
