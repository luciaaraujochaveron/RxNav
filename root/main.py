import requests
import pandas as pd
import os
import io

def get_drug_data(drug_name):
    # 1. Clean the input (remove accidental spaces)
    drug_name = drug_name.strip()
    
    # 2. Use the 'params' dictionary for safe URL encoding
    base_url = "https://rxnav.nlm.nih.gov/REST/drugs.json"
    params = {'name': drug_name}

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() # Check for HTTP errors (404, 500, etc.)
        
        # 3. Narrow Try/Except for JSON parsing only
        try:
            data = response.json()
        except ValueError:
            print("Error: The API did not return valid JSON.")
            return

    except requests.exceptions.RequestException as e:
        print(f"Error: Network or Request failed. {e}")
        return

    # Validate Data Structure
    if 'drugGroup' not in data or 'conceptGroup' not in data['drugGroup']:
        print("Not valid drug name or unexpected API response structure.")
        return

    print(f"JSON data for '{drug_name}' read successfully.")
    print("-" * 30)

    # Save RxNorm and drug name as a dictionary
    rxcui_dict = {}
    
    # Safety check: conceptGroup might be missing if no results
    if 'conceptGroup' in data['drugGroup']:
        for group in data['drugGroup']['conceptGroup']:
            if 'conceptProperties' in group:
                for prop in group['conceptProperties']:
                    # Filter out empty RxCUIs if necessary, though '0' checks are good
                    if prop.get('rxcui') != '0':
                        rxcui_dict[prop['rxcui']] = prop['name']
    
    if not rxcui_dict:
        print("No RxNorm(s) found.")
        return

    print(f"A total of {len(rxcui_dict)} RxNorm(s) - SBD type found.")

    # List to store dataframes before concatenating (More efficient than repeated concat)
    all_records = []

    for rxcui, rx_name in rxcui_dict.items():
        # --- Search for NDC codes ---
        ndc_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allhistoricalndcs.json"
        
        # We assume these internal API calls work if the main one did, but good to be safe
        ndc_resp = requests.get(ndc_url)
        if ndc_resp.status_code != 200:
            continue
            
        ndc_data = ndc_resp.json()

        if 'historicalNdcConcept' not in ndc_data:
            # print(f"No NDC code found for RxNorm: {rxcui}.") # Optional: Reduce noise
            continue

        # Extract NDC Data
        time_data = ndc_data['historicalNdcConcept']['historicalNdcTime']
        if not time_data: 
            continue
            
        df = pd.DataFrame(time_data[0]['ndcTime'])
        
        # Clean NDC column
        df['ndc'] = df['ndc'].astype(str).str.extract(r'(\d+)')
        df['rxnorm_sbd'] = rxcui # Renamed to match merge key later
        df['drug_name'] = rx_name

        # --- Search for SCD (Generic Info) ---
        scd_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/generic.json"
        scd_resp = requests.get(scd_url)
        
        if scd_resp.status_code == 200:
            scd_json = scd_resp.json()
            if 'minConceptGroup' in scd_json and 'minConcept' in scd_json['minConceptGroup']:
                df_scd = pd.DataFrame(scd_json['minConceptGroup']['minConcept'])
                
                # Rename for clarity
                df_scd.rename(columns={
                    "rxcui": "rxnorm_scd", 
                    "name": "generic_name",
                    "tty": "rxnorm_type"
                }, inplace=True)
                
                # Add columns to the main df (Broadcasting the generic info to all NDCs of this RxNorm)
                # Since an SBD usually maps to specific generics, we take the first match or merge
                # Simplified approach: Just take the first generic associated (often just one)
                if not df_scd.empty:
                    df['rxnorm_scd'] = df_scd.iloc[0]['rxnorm_scd']
                    df['generic_name'] = df_scd.iloc[0]['generic_name']
                    df['rxnorm_type'] = df_scd.iloc[0]['rxnorm_type']
            else:
                 # Fill with NaN if no generic info found
                 df['rxnorm_scd'] = None
                 df['generic_name'] = None
                 df['rxnorm_type'] = None

        all_records.append(df)

    print("-" * 30)

    # Concatenate all at once
    if all_records:
        final_df = pd.concat(all_records, ignore_index=True)
        
        current_directory = os.getcwd()
        save_path = os.path.join(current_directory, 'drug_codes')
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        file_name = f'{drug_name}_NDC_Code_list.csv'
        full_path = os.path.join(save_path, file_name)
        
        final_df.to_csv(full_path, index=False)
        print(f"Success! A total of {len(final_df)} NDC codes for '{drug_name}' were found.")
        print(f"File saved to: {full_path}")
    else:
        print(f"No NDC records could be compiled for {drug_name}.")

# --- Test ---
# This will now work even with the space
get_drug_data(' prednisone  ')