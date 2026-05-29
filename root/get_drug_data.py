import requests
import pandas as pd
import os

def get_drug_data(drug_name):
    # The API endpoint of finding RxNorm code based on drug name
    url = f"https://rxnav.nlm.nih.gov/REST/drugs.json?name={drug_name}"
    # A GET request to the API
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type')
        if 'application/json' in content_type:
            try:
                # Read the JSON file
                data = response.json()
                if 'conceptGroup' not in data['drugGroup']:
                    print("Not valid drug name")
                else:
                    print(f"JSON data for {drug_name} read successfully.")
                print("-" * 30)
                # Save RxNorm and drug name as a dictionary
                try:
                    rxcui_dict = {}
                    for group in data['drugGroup']['conceptGroup']:
                        if 'conceptProperties' not in group:
                            continue
                        for prop in group['conceptProperties']:
                            if prop['rxcui'] == '0':
                                print('No RxNorm(s) found.')
                            else:
                                rxcui_dict[prop['rxcui']] = prop['name']
                    print(f"A total of {len(rxcui_dict)} RxNorm(s) - SBD type found.")
                    # Loop through the Rxcui code of the dictionary and generate the URL of each RxNorm code
                    NDC_data_interim = pd.DataFrame()
                    NDC_data = pd.DataFrame()
                    for key, value in rxcui_dict.items():
                        # Add the search for NDC codes
                        url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{key}/allhistoricalndcs.json"
                        response = requests.get(url)
                        ndc_data = response.json()
                        if 'historicalNdcConcept' not in ndc_data:
                            print(f"No NDC code found for RxNorm: {key}.")
                            continue
                        df = pd.DataFrame(ndc_data['historicalNdcConcept']['historicalNdcTime'][0]['ndcTime'])
                        # Only keep numeral values in the ndc column
                        df['ndc'] = df['ndc'].astype(str).str.extract('(\d+)')
                        # Add two columns to the dataframe based on the rxcui_dict first item
                        df['rxnorm'] = key
                        df['drug_name'] = value
                        # Add the dataframe to the NDC_data_interim dataframe
                        NDC_data_interim = pd.concat([NDC_data, df], ignore_index=True)
                        # Add the search for SCD: Generic RxNorm search [might need to be added as a trigger]
                        url_scd = f"https://rxnav.nlm.nih.gov/REST/rxcui/{key}/generic.json"
                        response_scd = requests.get(url_scd)
                        scd_data = response_scd.json()
                        if 'minConceptGroup' not in scd_data:
                            print(f"No Generic SCD found for RxNorm: {key}.")
                            continue
                        df_scd = pd.DataFrame(scd_data['minConceptGroup']['minConcept'])
                        df_scd['rxnorm_sbd']= key
                        df_scd['rxcui'].astype(str)
                        df_scd.rename(columns={"rxcui": "rxnorm_scd", 
                                                "name": "generic_name",
                                                "tty": "rxnorm_type"}, inplace=True)
                        # Merge the two dataframes based on the rxnorm code
                        NDC_data = pd.merge(NDC_data_interim, df_scd[['rxnorm_sbd','rxnorm_scd', 'generic_name', 'rxnorm_type']], 
                                            left_on='rxnorm', right_on='rxnorm_sbd', how='left')
                    # Save the dataframe to a csv file
                    print("-" * 30)
                    current_directory = os.getcwd()
                    # Create a directory to save the csv file if it doesn't exist
                    if not os.path.exists(f'{current_directory}/drug_codes'):
                        os.makedirs(f'{current_directory}/drug_codes')
                    # Save the dataframe to a csv file
                    NDC_data.to_csv(f'{current_directory}/drug_codes/{drug_name}_NDC_Code_list.csv', index=False)
                    print(f"A total of {len(NDC_data)} NDC codes for {drug_name} were found.")
                except KeyError:
                    print(f"Error: Invalid drug name is provided - {drug_name}.")
            except ValueError:
                print("Error: Response content is not in JSON format.")
        else:
            print("Error: Unsupported content type.")
    else:
        print(f"Error: Failed to retrieve data. Status code: {response.status_code}")
