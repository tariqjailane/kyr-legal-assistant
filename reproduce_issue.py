import sys
import os

# Ensure we can import from local directory
sys.path.append(os.getcwd())

from legal_db import search_db, init_db, get_answer_by_intent

def test_search():
    print("Initializing DB...")
    init_db()
    
    # Test Hindi Search
    query_hi = "मकान मालिक"
    try:
        print(f"\nTesting Hindi Search: '{query_hi}'".encode('utf-8', errors='ignore').decode('utf-8'))
    except:
        print("\nTesting Hindi Search (text hidden due to encoding)")
        
    results_hi = search_db(query_hi, 'hi')
    print(f"Results: {results_hi}")
    
    # Test Tamil Search
    query_ta = "நில உரிமையாளர்"
    try:
        print(f"\nTesting Tamil Search: '{query_ta}'".encode('utf-8', errors='ignore').decode('utf-8'))
    except:
        print("\nTesting Tamil Search (text hidden due to encoding)")

    results_ta = search_db(query_ta, 'ta')
    print(f"Results: {results_ta}")
    
    # Test Single Word Search (Hypothesis check)
    query_single = "मकान"
    try:
        print(f"\nTesting Single Word Search: '{query_single}'".encode('utf-8', errors='ignore').decode('utf-8'))
    except:
        print("\nTesting Single Word Search (text hidden)")
    
    results_single = search_db(query_single, 'hi')
    print(f"Results: {results_single}")


    
    # Test get_answer
    print("\nTesting get_answer_by_intent ('tenant_rights', 'hi')")
    ans, cit, case = get_answer_by_intent('tenant_rights', 'hi')
    if ans:
        print(f"Answer found (len={len(ans)})")
    else:
        print("Answer NOT found")

if __name__ == "__main__":
    test_search()
