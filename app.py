from cachetools import cached
from cachetools import TTLCache
from concurrent.futures import ThreadPoolExecutor
from google.api_core.exceptions import GoogleAPIError
from google.cloud.secretmanager import SecretManagerServiceClient
from flask import abort
from flask import Flask
from flask import make_response
from flask import render_template
from flask import redirect
from flask import request
from flask import send_from_directory
from flask import url_for
from flask_minify import decorators
from flask_minify import minify
from google.cloud import firestore
from google.cloud import storage
from google.cloud.firestore_v1.field_path import FieldPath
import numpy as np
import openai
import os
import random
import re
from threading import Lock
from urllib.parse import quote
from urllib.parse import unquote
import os
import pinecone
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util


app = Flask(__name__)
minify(app=app, caching_limit=0, passive=True)

# helper class to connect to pinecone before querying
class PineconeConnector:
    def __init__(self):
        self.PINECONE_KEY = os.getenv("PINECONE_KEY")
        self.PINECONE_ENV = os.getenv("PINECONE_ENV")
        pinecone.init(
            api_key=self.PINECONE_KEY,
            environment=self.PINECONE_ENV
        )
        self.index_name = 'semantic-search'
        # now connect to the index
        self.index = pinecone.GRPCIndex(self.index_name)

    def query(self, query_embedding):
        return self.index.query(query_embedding, top_k=5, include_metadata=True)

# helper clsas to load the encoder model
class Encoder:
    def __init__(self):
        # Preload encoder model
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        

pinecone_connector = PineconeConnector()
encoder = Encoder()

def _render_page(top_k, response):
    return render_template('index.html',
                           top_k=top_k,
                           response=response)


def _render_static(filename, mimetype):
    return send_from_directory('static', filename, mimetype=mimetype)


# currently just using environment variables to store secrets. fix!

@cached(cache=TTLCache(maxsize=10, ttl=24*60*60))  # Cache 10 for 1 day.
def _secret(key):
    # Retrieve a value from the Google Cloud Secret Manager.
    try:
        google_cloud_project = os.environ['GOOGLE_CLOUD_PROJECT']
        secretmanager_client = SecretManagerServiceClient()
        secret_path = SecretManagerServiceClient.secret_version_path(
            project=google_cloud_project, secret=key, secret_version='latest')
        return secretmanager_client.access_secret_version(
            name=secret_path).payload.data.decode('UTF-8')
    except (KeyError, GoogleAPIError) as e:
        raise ValueError(f'Failed to retrieve secret: {e}')


# @app.route('/')
# @decorators.minify(html=True, js=True, cssless=True)
# def main_page():
    
#     return _render_page({}, {})


@app.route('/api/<prompt>')
@decorators.minify(html=True, js=True, cssless=True)
def prompt_page(prompt):
    # given a user prompt as a parameter, encode the prompt using bert, query pinecone for the top 5 results,     

    # query openai API to generate a response
    OPENAI_KEY = os.getenv("OPENAI_KEY")
    openai.api_key = OPENAI_KEY
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.7,
        max_tokens=300,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=0.5
    )
    #get the response text
    response_text = response['choices'][0]['text']
    # query OpenAI to generate a response, and return the response along with the top 5 results from pinecone.

    response_embedding = encoder.model.encode(response_text).tolist()

    # query the index
    top_k = pinecone_connector.query(response_embedding).to_dict()["matches"]

    return {"top_k":top_k, "response_text":response_text, "response_embedding":response_embedding}


@app.route('/style.css')
def style_css():
    return _render_static(filename='style.css', mimetype='text/css')

@app.route('/')
def index_html():
    return _render_static(filename='index.html', mimetype='text/html')

@app.route('/script.js')
def script_js():
    return _render_static(filename='script.js', mimetype='text/javascript')

def _render_static(filename, mimetype):
    return send_from_directory('static', filename, mimetype=mimetype)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)