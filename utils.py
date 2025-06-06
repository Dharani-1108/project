# -*- coding: utf-8 -*-
"""utils.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1_G9L6Vl3UfSZkwGH2Gqx5er0nyv5pTyF
"""

import requests
from config import OPENAI_API_KEY, GOOGLE_MAPS_API_KEY, WEATHER_API_KEY, AMADEUS_API_KEY, AMADEUS_API_SECRET, llm
from amadeus import Client, ResponseError
import os
from langchain_openai.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain_openai import OpenAIEmbeddings
import re
import faiss
import numpy as np
from langchain.vectorstores import FAISS
from langchain.docstore.in_memory import InMemoryDocstore  # ✅ Required for FAISS Storage
from langchain.schema import Document

amadeus = Client(client_id=AMADEUS_API_KEY, client_secret=AMADEUS_API_SECRET)

# ✅ Initialize OpenAI Embedding Model
embedding_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# ✅ FAISS Setup
dimension = 1536  # Ensure embedding dimensions match OpenAI embeddings
faiss_index = faiss.IndexFlatL2(dimension)
docstore = InMemoryDocstore({})
index_to_docstore_id = {}

vector_store = FAISS(embedding_model, faiss_index, docstore, index_to_docstore_id)

# ✅ Fetch Travel Data
def fetch_travel_data(destination):
    """Retrieve real-time travel-related information from APIs."""

    print(f"Fetching travel data for {destination}...")

    # ✅ Wikipedia Data
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{destination.replace(' ', '_')}"
    wiki_response = requests.get(wiki_url)
    wiki_data = wiki_response.json().get("extract", "No data available.") if wiki_response.status_code == 200 else "No data available."

    # ✅ Google Places Data
    google_places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"top attractions in {destination}", "key": GOOGLE_MAPS_API_KEY}
    google_response = requests.get(google_places_url, params=params)

    places_info = "No places found."
    if google_response.status_code == 200:
        places = google_response.json().get("results", [])
        places_info = "\n".join([f"{p['name']} - {p.get('formatted_address', 'No address')}" for p in places[:5]])

    return f"{wiki_data}\n\nTop Attractions:\n{places_info}"

# ✅ Update FAISS Index
def update_faiss_index(destination):
    """Dynamically update FAISS index and store documents properly."""

    print(f"🔄 Updating FAISS index for {destination}...")
    travel_data = fetch_travel_data(destination)

    # ✅ Generate embeddings dynamically
    doc_embedding = embedding_model.embed_documents([travel_data])
    embedding_dim = len(doc_embedding[0])  # ✅ Detect embedding dimension dynamically

    global faiss_index, vector_store, docstore, index_to_docstore_id

    if faiss_index.is_trained and faiss_index.ntotal > 0:
        existing_dim = faiss_index.d
        if existing_dim != embedding_dim:
            print(f"⚠️ FAISS dimension mismatch! Reinitializing FAISS to {embedding_dim} dimensions.")
            faiss_index = faiss.IndexFlatL2(embedding_dim)
            docstore = InMemoryDocstore({})
            index_to_docstore_id = {}

    else:
        print(f"✅ Initializing FAISS with {embedding_dim} dimensions.")
        faiss_index = faiss.IndexFlatL2(embedding_dim)
        docstore = InMemoryDocstore({})
        index_to_docstore_id = {}

    # ✅ Add new embeddings to FAISS
    faiss_index.add(np.array(doc_embedding))

    # ✅ Store document properly in docstore
    doc_id = str(faiss_index.ntotal - 1)
    index_to_docstore_id[faiss_index.ntotal - 1] = doc_id
    docstore._dict[doc_id] = Document(page_content=travel_data, metadata={"doc_id": doc_id})

    # ✅ Save FAISS Index
    vector_store = FAISS(embedding_model, faiss_index, docstore, index_to_docstore_id)
    vector_store.save_local("faiss_travel_index")

    print(f"✅ FAISS Index successfully updated with travel data for {destination}")

# ✅ Retrieve Data using FAISS
def retrieve_relevant_docs(query):
    """Retrieve relevant travel data from FAISS dynamically."""

    print(f"🔍 Retrieving relevant documents for query: {query}")

    # ✅ Load FAISS index safely
    vector_store = FAISS.load_local(
        "faiss_travel_index",
        OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        allow_dangerous_deserialization=True
    )

    retrieved_docs = vector_store.similarity_search_with_score(query, k=2)

    if not retrieved_docs:
        print("❌ No relevant documents found.")
        return "No relevant documents found for your query."

    print(f"✅ Relevant Documents Found: {retrieved_docs}")
    return " ".join([doc.page_content for doc, _ in retrieved_docs])

# ✅ Generate AI Travel Plan using RAG
def generate_travel_plan_rag(origin, destination, start_date, end_date, purpose):
    """Use RAG to generate a detailed travel plan dynamically."""

    print("🔄 Generating AI Travel Plan using RAG...")

    # ✅ Retrieve Travel Information from FAISS
    context_info = retrieve_relevant_docs(f"Best travel itinerary for {destination}")

    prompt = f"""
    Create a detailed travel itinerary for {destination} from {origin} ({start_date} - {end_date}).
    Purpose: {purpose}

    Additional Travel Information:
    {context_info}
    """

    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else str(response)

# ✅ Generate AI Travel Story using RAG
def generate_travel_story_rag(origin, destination, start_date, end_date, purpose):
    """Use RAG to generate a travel story dynamically."""

    print("🔄 Generating AI Travel Story using RAG...")

    # ✅ Retrieve Travel Information from FAISS
    context_info = retrieve_relevant_docs(f"Best places to visit in {destination} for {purpose}")

    prompt = f"""
    Create a compelling travel story about visiting {destination} from {origin} ({start_date} - {end_date}).
    Purpose: {purpose}

    Additional Travel Information:
    {context_info}
    """

    response = llm.invoke(prompt)
    return response.content if hasattr(response, 'content') else str(response)


# ✅ Function to fetch latitude & longitude
def get_lat_lng(location):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": GOOGLE_MAPS_API_KEY}
    response = requests.get(url, params=params).json()
    if "results" in response and response["results"]:
        location_data = response["results"][0]["geometry"]["location"]
        return location_data["lat"], location_data["lng"]
    return None, None

# ✅ Function to fetch tourist attractions
def fetch_tourist_attractions(location, top_n=5):
    lat, lng = get_lat_lng(location)
    if not lat or not lng:
        return "Could not determine the exact location."

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {"location": f"{lat},{lng}", "radius": 10000, "type": "tourist_attraction", "key": GOOGLE_MAPS_API_KEY}

    response = requests.get(url, params=params).json()
    if "results" in response:
        return [f"{t['name']} ({t.get('rating', 'No rating')}⭐)" for t in response["results"][:top_n]]
    return "No tourist attractions found."

# ✅ Function to fetch restaurants
def fetch_restaurants(location, purpose, top_n=5):
    lat, lng = get_lat_lng(location)
    if not lat or not lng:
        return "Could not determine the exact location."

    keyword = {
        "Leisure": "casual dining",
        "Business": "fine dining",
        "Family": "family-friendly",
        "Adventure": "unique cuisine",
        "Romantic": "romantic restaurant"
    }.get(purpose, "restaurant")

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {"location": f"{lat},{lng}", "radius": 5000, "type": "restaurant", "keyword": keyword, "key": GOOGLE_MAPS_API_KEY}

    response = requests.get(url, params=params).json()
    if "results" in response:
        return [f"{r['name']} ({r.get('rating', 'No rating')}⭐)" for r in response["results"][:top_n]]
    return "No restaurants found."

# ✅ Function to fetch real-time weather details
def fetch_weather(city):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    response = requests.get(url, params=params).json()
    if "weather" in response and "main" in response:
        return f"{response['weather'][0]['description'].capitalize()}, {response['main']['temp']}°C"
    return "Weather data not available."

def get_airport_code(city_name):
    """
    Convert a city name to an airport code using the Amadeus API.
    """
    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType='AIRPORT'
        )
        # Extract the airport code from the response
        for location in response.data:
            if location['subType'] == 'AIRPORT':
                return location['iataCode']
        return None
    except ResponseError as error:
        print(f"Error fetching airport code for {city_name}: {error}")
        return None


# Helper Function to get full airline names from its codes using OpenAI
def get_airline_full_name(airline_code):
    prompt = f"Please provide only the full name for the airline '{airline_code}'."
    response = llm([HumanMessage(content=prompt)])
    return response.content.strip() if response else airline_code  # Return the code if response is empty

def format_duration(iso_duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso_duration)
    hours = match.group(1) if match.group(1) else "0"
    minutes = match.group(2) if match.group(2) else "0"
    return f"{int(hours)} hours {int(minutes)} minutes"

# Function to fetch Flights information
def fetch_flight_details(origin, destination, start_data, return_date=None, max_price=None, airline_name =None):
    try:
        origin_code = get_airport_code(origin)
        destination_code = get_airport_code(destination)
        # Set a high default max_price if not provided
        max_price = max_price if max_price else 20000
        params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": destination_code,
            "departureDate": start_data,
            "adults": 1,
            "maxPrice": max_price
        }

        if return_date:
            params["returnDate"] = return_date  # Include return date for round-trip flights

        # Fetch flights from Amadeus API
        response = amadeus.shopping.flight_offers_search.get(**params)
        flights = response.data

        if flights:
            result = []
            for flight in flights[:5]:  # Limit to top 5 results
                if float(flight['price']['total']) <= max_price:
                    # Outbound flight details
                    segments = flight['itineraries'][0]['segments']
                    airline_code = segments[0]['carrierCode']
                    airline = get_airline_full_name(airline_code)  # Get full airline name
                    # Only add flights that match the specified airline, if provided
                    if airline_name and airline and airline.lower() not in airline_name.lower():
                        continue
                    departure_time = segments[0]['departure']['at']
                    arrival_time = segments[-1]['arrival']['at']
                    flight_duration = format_duration(flight['itineraries'][0]['duration'])

                    # Only include return details if a return date is provided
                    if return_date and len(flight['itineraries']) > 1:
                        return_segments = flight['itineraries'][1]['segments']
                        return_departure_time = return_segments[0]['departure']['at']
                        return_arrival_time = return_segments[-1]['arrival']['at']
                        return_duration = format_duration(flight['itineraries'][1]['duration'])
                        return_info = (
                            f"\nReturn Departure: {return_departure_time}\n"
                            f"Return Arrival: {return_arrival_time}\n"
                            f"Return Duration: {return_duration}\n"
                        )
                    else:
                        return_info = ""

                    # Append both outbound and return information (if available) to results
                    result.append(
                        f"Airline: {airline}\nPrice: ${flight['price']['total']}\n"
                        f"Departure: {departure_time}\nArrival: {arrival_time}\n"
                        f"Duration: {flight_duration}{return_info}"
                        "\n----------------------------------------"
                    )
            return "\n\n".join(result) if result else "No flights found within the budget."
        return "No flights found."
    except ResponseError as error:
        return f"An error occurred: {error.response.result}"

# ✅ Function to fetch hotels
def fetch_hotels(location, top_n=5):
    lat, lng = get_lat_lng(location)
    if not lat or not lng:
        return "Could not determine the exact location."

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {"location": f"{lat},{lng}", "radius": 5000, "type": "lodging", "key": GOOGLE_MAPS_API_KEY}

    response = requests.get(url, params=params).json()
    if "results" in response:
        return [f"{h['name']} ({h.get('rating', 'No rating')}⭐)" for h in response["results"][:top_n]]
    return "No hotels found."