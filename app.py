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
        st.session_state["openai_api_key"] = st.text_input("OPENAI API KEY:")
        if st.session_state["openai_api_key"]:
            st.rerun()

    if not st.session_state.get("openai_api_key"):
        st.stop()

st.file_uploader(label="Upload Portfolio screens", accept_multiple_files=True)
