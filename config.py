# -*- coding: utf-8 -*-
"""config.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1KOSnvRZmVieK-NUTAKmNFl4-oehB-waC
"""

import streamlit as st
from amadeus import Client
import os
from langchain_openai.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# ✅ Fetch API keys securely from environment variables
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
AMADEUS_API_KEY = st.secrets["AMADEUS_API_KEY"]
AMADEUS_API_SECRET = st.secrets["AMADEUS_API_SECRET"]
GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
HUGGINGFACE_TOKEN = st.secrets["HUGGINGFACE_TOKEN"]

# ✅ Initialize Amadeus Client

amadeus = Client(client_id=AMADEUS_API_KEY, client_secret=AMADEUS_API_SECRET)

llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=OPENAI_API_KEY)