import json
from pathlib import Path
from datetime import date
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
env = dotenv_values(".env")

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


# Openai Function
def generate_ai_response(file_name, file_bytes):

    encoded_image = prep_file_for_openai(file_name, file_bytes)

    response = openai_client.chat.completions.create(
        
        model="gpt-4o-mini",
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


    return (response.choices[0].message.content)

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
                st.write(f"Processing file: **{uploaded_file.name}**")

                file_bytes = uploaded_file.read()
                

                with st.spinner("Generatin AI response..."):
                    try:
                        ai_response = generate_ai_response(uploaded_file.name, file_bytes)
                        st.success("Response generated!")
                        st.write("**AI Response:**")
                        st.write(ai_response)
                    except Exception as e:
                        st.error(f"Error: {e}")