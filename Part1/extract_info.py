import os
import re
from elasticsearch import Elasticsearch, helpers

#Ανάκτηση αρχείων και δημιουργία dictionaries
def get_cf(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as cff:
        content = cff.read()

    #Χωρισμός κάθε paper
    raw_data = re.split(r'\n(?=PN)', content)

    #Map κάθε section
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

    #Επεξεργασία κάθε paper
    for raw in raw_data:
        #Αν το αρχείο είναι κενό
        if not raw.strip():
            continue

        d = {}
        lines = raw.split('\n')
        current_tag = None
        current_val = []

        for line in lines:
            #Εντοπίζουμε αν η κάθε ξεκινάει με κάποια ετικέτα
            tag_match = re.match(r'^([A-Z]{2}|AB/EX)\s+(.*)', line)
            if tag_match:
                if current_tag and current_tag in field_map:
                    field_name = field_map[current_tag]
                    d[field_name] = " ".join(current_val).strip()

                #Παίρνουμε την καινούργια ετικέτα και την τιμή της
                tag, val = tag_match.groups()
                current_tag = tag if tag != 'AB/EX' else 'AB'
                current_val = [val]

            #Αν η γραμμή δεν έχει ετικέτα τότε είναι συνέχεια του προηγούμενου section
            else:
                if current_tag:
                    current_val.append(line.strip())

        if current_tag and current_tag in field_map:
            d[field_map[current_tag]] = " ".join(current_val).strip()

        #Μετατροπή του RN σε integer
        if 'rn' in d:
            try:
                d['rn'] = int(d['rn'])
            except ValueError:
                pass

        # Αν το έγγραφο δεν είναι κενό, το προσθέτουμε στη λίστα                
        if d:
            data.append(d)

    return data

try:
    # Δημιουργία σύνδεσης με Elasticsearch
    es = Elasticsearch("http://localhost:9200")
    info = es.info()
    print("Success! Επιτυχής σύνδεση.")
    
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

    # Δημιουργία Index αν δεν υπάρχει
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=mapping)
        print(f"Το index '{index_name}' δημιουργήθηκε")
    else:
        print(f"Το index '{index_name}' υπάρχει ήδη.")

    # Ανάγνωση αρχείων
    base_dir = "../data"
    #base_dir = "/home/totoro/Έγγραφα/University/Seventh_Semester/Ανάκτηση_Πληροφορίας/Project/cfc"
    file_names = ['cf74', 'cf75', 'cf76', 'cf77', 'cf78', 'cf79']
    file_paths = [os.path.join(base_dir, f) for f in file_names]

    documents = []

    for file in file_paths:
        print(f"Διαβάζεται το αρχείο: {file}")
        documents.extend(get_cf(file))

    print(f"Συνολικά συλλέχθηκαν {len(documents)} έγγραφα από τα αρχεία.")

    # Έλεγχος αν το έγγραφο υπάρχει ήδη στην Elasticsearch
    papers = []
    for doc in documents:
        doc_id = doc.get("rn")
        # Αν δεν υπάρχει ήδη στη βάση, το προσθέτουμε προς ανέβασμα
        if not es.exists(index=index_name, id=doc_id):
            papers.append({
                "index": index_name,
                "id": doc_id,  
                "source": doc
            })

    # Μαζική εισαγωγή μόνο των νέων εγγράφων
    if papers:
        success, _ = helpers.bulk(es, papers)
        print(f"Επιτυχής εισαγωγή {success} νέων εγγράφων στο Elasticsearch!")
    else:
        print("Όλα τα έγγραφα υπάρχουν ήδη στη βάση. Δεν έγινε καμία νέα εισαγωγή.")

except Exception as e:
    print("Αποτυχία σύνδεσης ή εκτέλεσης με σφάλμα:", e)