from RxNav.root.Archive.get_drug_data_backup import get_drug_data
import sys

def main():
    if len(sys.argv) > 1:
        drug_name = sys.argv[1]
    else:
        print("Usage: python automated_script.py <drug_name>")
        sys.exit(1)

    print("-" * 30)
    print(f"Drug data retrieval in progress for: {drug_name}")
    print("-" * 30)
    get_drug_data(drug_name)
    print("-" * 30)
    print("**Drug data retrieval completed!**")
