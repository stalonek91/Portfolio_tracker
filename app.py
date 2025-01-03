import json
from pathlib import Path
from datetime import date, datetime
import base64
from getpass import getpass
import mimetypes

import streamlit as st
from IPython.display import Image
import instructor
from pydantic import BaseModel
from openai import OpenAI
import pandas as pd
from dotenv import dotenv_values

st.set_page_config(page_title="Portfolio_tracker", layout="centered")

# Debugging: Print all session state keys and values at the start of each run
st.write("Session State at Start:")
for key in st.session_state.keys():
    st.write(f"{key}: {st.session_state[key]}")


env = dotenv_values(".env")
screen_to_json_path = Path("Images/Processed")
response_df = pd.DataFrame(columns=["Wallet", "Value", "Profit"])

# API key protection



if not st.session_state.get("openai_api_key"):
    if "OPENAI_KEY" in env:
        st.session_state["openai_api_key"] = env["OPENAI_KEY"]


    else:
        
        st.info("Please provide Your OPENAI API KEY")
        st.session_state["openai_api_key"] = st.text_input("OPENAI API KEY:", type="password")
        if st.session_state["openai_api_key"]:
            st.rerun()

    if not st.session_state.get("openai_api_key"):
        st.stop()

openai_client = OpenAI(api_key=st.session_state.get("openai_api_key"))

# Prompt definition
CUMMULATED_PROMPT ="""
Twoim zadaniem bedzie rozpoznanie obrazu na podstawie slowa kluczowego. Na tej podstawie wykonasz odpowiednia instrukcje. Zaczynamy:

Jesli na obrazie zobaczysz napis 'Obligacje' wykonasz nastepujace polecenie: Na podstawie screenu pobierz dane na temat zainwestowanych obligacji. Kolumna odsteki pokazuje wypracowany zysk.
Kolumna liczba przedstawia zakupione obligacje. 1 obligacja to 100zl.
Dane przedstaw w formacie JSON w nastepujacym formacie
{
    "Obligacje": {
        "Wartosc": "30000PLN",
        "Zysk": "400PLN"
    }
}
 {"Wartosc": 30000PLN, "Zysk": 400PLN (zysk musi byc zsumowany z kazdej emisji)}

Jesli na obrazie bedzie napis Generali Investments wykonaj nastepujace polecenie:
Na podstawie screenu pobierz dane na temat ogolnej wartosci rachunku oraz bilansu.
Dane przedstaw w formacie JSON - bez komentarzy same dane w nastepujacym formacie:
{
    "Generali": {
        "Wartosc": "30000PLN",
        "Zysk": "400PLN"
    }
}

Jesli na obrazie zobaczysz nazwe BITCOIN wykonasz nastepujace polecenie:
Na podstawie screenu pobierzesz 2 wartosci liczbowe. 
Pierwsza widoczna i najwieksza zapisana bedzie jako wartosc - znajdziesz ja na gorze obrazu pogrubiona czacionka pod paskiem 'Szukaj'. 
Druga jako zysk (bedzie miala znaczek + z przodu).
Dane zapiszesz w formacie JSON: 
{
    "Kryptowaluty": {
        "Wartosc": "30000PLN", (- znajdziesz ja na gorze obrazu pogrubiona czacionka pod paskiem 'Szukaj')
        "Zysk": "400PLN" (nie dodawaj znaku + lub - tylko sama liczbe)
    }
}

Jesli na obrazie zobaczysz nazwe IKE (PLN) wykonasz nastepujace polecenie:
Na podstawie screenu pobierzesz 2 wartosci liczbowe. 
Pierwsza wartosc bedzie pod tekstem "Wartosc IKE (PLN) i bedzie reprezentowac klucz  "Wartosc".
Druga wartosc bedzie pod tekstem "Zysk/strata" i bedzie reprezentowac klicz "Zysk"
Dane zapiszesz w formacie JSON: 
{
    "XTB_IKE": {
        "Wartosc": "30000PLN", 
        "Zysk": "400PLN"
    }
}

Jesli na obrazie zobaczysz nazwe "Total Portfolio Value" wykonasz nastepujace polecenie:
Na podstawie screenu pobierzesz jedna wartosc liczbowa znajdujaca sie pod tekstem "Total Portfolio value"
i bedzie reprezentowac klucz wartosc i zysk.


Dane zapiszesz w formacie JSON: 
{
    "Nokia_Akcje": {
        "Wartosc": "30000PLN", 
        "Zysk": "(tu wklej te sama liczbe co w kluczu wartosc)"
    }
}

"""


# Prepreration file for openai

def prep_file_for_openai(file_name, file_bytes):
    # Sprawdzenie MIME typu na podstawie rozszerzenia pliku
    mime_type, _ = mimetypes.guess_type(file_name)
    
    # Obsługiwane typy obrazów
    supported_types = ["image/png", "image/jpeg"]
    
    # Sprawdzenie, czy typ MIME jest obsługiwany
    if mime_type not in supported_types:
        raise ValueError(f"Nieobsługiwany format obrazu: {mime_type}. Obsługiwane formaty to: {', '.join(supported_types)}")
    
    # Wczytanie obrazu i zakodowanie go w Base64

    image_data = base64.b64encode(file_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{image_data}"


# New function to save AI response to a JSON file
def save_response_to_json(response, filename):
    with open(filename, 'w') as json_file:
        json.dump(response, json_file, ensure_ascii=False, indent=4)

# Modify the existing function to save the response
def generate_ai_response(file_name, file_bytes):
    encoded_image = prep_file_for_openai(file_name, file_bytes)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": CUMMULATED_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": encoded_image,
                            "detail": "high"
                        },
                    },
                ],
            }
        ],
    )

    # Extract the content and clean it up
    content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()  # Clean leading/trailing whitespace



    # Fix the incorrect period to a comma between key-value pairs
    content = content.replace("PLN.", "PLN,")  # Replace the incorrect period after PLN with a comma

    # Print cleaned content for debugging
    print("Cleaned AI Response:", content)  # Debugging line

    try:
        # Attempt to parse the cleaned content to ensure it's valid JSON
        json_response = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Response is not valid JSON.")

    return json_response

# First form for generating AI response
with st.form("File_uploader_form"):
    uploaded_files = st.file_uploader(
        label="Upload Portfolio screens", 
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg"]
    )
    submitted = st.form_submit_button("Generate AI response")
    if submitted:
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_bytes = uploaded_file.read()

                with st.spinner("Generating AI response..."):
                    try:
                        ai_response = generate_ai_response(uploaded_file.name, file_bytes)

                        # Extract data from the AI response and create a temporary DataFrame
                        temp_df = pd.DataFrame([
                            {
                                "Wallet": wallet,
                                "Value": data.get("Wartosc"),
                                "Profit": data.get("Zysk")
                            }
                            for wallet, data in ai_response.items()
                        ])

                        # Concatenate the temporary DataFrame with the main response DataFrame
                        response_df = pd.concat([response_df, temp_df], ignore_index=True)

                    except Exception as e:
                        st.error(f"Error during AI response generation: {e}")
                        continue  # Skip to the next file

                # Attempt to save the AI response to a JSON file
                try:
                    save_response_to_json(ai_response, f"{screen_to_json_path}/{uploaded_file.name}_response.json")
                except Exception as e:
                    st.error(f"Error saving response to JSON: {e}")

        # Update the session state with the populated response_df
        st.session_state.response_df = response_df  # Ensure this line is executed after processing all files

# Initialize a final DataFrame to store validated responses
if 'response_df' not in st.session_state:
    st.session_state.response_df = pd.DataFrame(columns=["Wallet", "Value", "Profit", "Date Added"])

# Second form for user validation
if 'corrected_data' not in st.session_state:
    st.session_state.corrected_data = []  # Initialize corrected_data in session state

with st.form("Validation_form"):
    st.write("**Please validate the retrieved data:**")
    
    # Access the response_df from session state
    response_df = st.session_state.response_df

    # Display each row for validation
    for index, row in response_df.iterrows():
        wallet = row['Wallet']
        value = st.text_input(f"Value for {wallet}:", value=row['Value'], key=f"value_{index}")  # Added key for uniqueness
        profit = st.text_input(f"Profit for {wallet}:", value=row['Profit'], key=f"profit_{index}")  # Added key for uniqueness
        date_added = st.text_input(f"Date Added for {wallet}:", value=datetime.now().strftime("%Y-%m-%d"), key=f"date_{index}")  # Added date input
        st.write("---")  # Separator for clarity

    # Submit button for validation
    validate = st.form_submit_button("Validate and Save Data")
    
    if validate:
        # Collect data after form submission
        for index, row in response_df.iterrows():
            wallet = row['Wallet']
            value = st.session_state[f"value_{index}"]  # Get the value from session state
            profit = st.session_state[f"profit_{index}"]  # Get the profit from session state
            date_added = st.session_state[f"date_{index}"]  # Get the date from session state
            
            # Check if the values are being retrieved correctly
            if value and profit and date_added:
                data_to_append = {
                    "Wallet": wallet,
                    "Value": value,
                    "Profit": profit,
                    "Date Added": date_added,
                }

                st.session_state.corrected_data.append(data_to_append)

        # Create a DataFrame from the corrected data
        final_response_df = pd.DataFrame(st.session_state.corrected_data)
        if final_response_df.empty:
            st.warning("No data to save. Please check your inputs.")
        else:
            st.success("Data has been validated and saved.")
            st.dataframe(final_response_df)  # Display the final DataFrame

         