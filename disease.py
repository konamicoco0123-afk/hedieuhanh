from pathlib import Path
import json
import streamlit as st


@st.cache_data
def load_diseases():

    file_path = Path(__file__).parent / "diseases.json"

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)



def get_priority_by_disease(disease_name):

    diseases = load_diseases()

    for item in diseases:

        if item["disease"] == disease_name:

            return item["priority"]

    return 5