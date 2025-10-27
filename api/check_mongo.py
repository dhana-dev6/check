import os
import json
from http.server import BaseHTTPRequestHandler
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Get the URI from Vercel Environment Variables
MONGODB_URI = os.environ.get('MONGODB_URI')

# This client variable is cached in the global scope.
# It will persist between "warm" invocations of the serverless function.
client = None

def get_mongo_client():
    """
    Initializes and returns a cached MongoDB client.
    If the connection fails, it raises an exception.
    """
    global client
    
    # Check if client is already connected
    if client:
        try:
            # Ping to check if the cached connection is still valid
            client.admin.command('ping')
            return client
        except ConnectionFailure:
            print("Cached connection lost. Reconnecting...")
            client = None # Force re-connection

    # If client is None or connection was lost, create a new one
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI environment variable is not set.")

    try:
        # Set a short timeout for server selection
        # This prevents the function from hanging for a long time
        new_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        
        # Ping the database on first connect to ensure it's valid
        new_client.admin.command('ping')
        print("New MongoDB connection established.")
        
        client = new_client # Cache the new client
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        client = None # Ensure client is not cached if connection failed
        raise e

class handler(BaseHTTPRequestHandler):
    """
    This is the Vercel Serverless Function handler.
    It responds to GET requests.
    """
    
    def do_GET(self):
        try:
            # 1. Get the MongoDB client (either cached or new)
            mongo_client = get_mongo_client()
            
            # 2. Send a success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response_body = json.dumps({
                'message': '✅ MongoDB connection successful (cached)!'
            })
            self.wfile.write(response_body.encode('utf-8'))

        except Exception as e:
            # 4. If any error occurs, send a 500 response
            print(f"Error during MongoDB connection test: {e}")
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response_body = json.dumps({
                'error': 'Failed to connect to MongoDB',
                'details': str(e)
            })
            self.wfile.write(response_body.encode('utf-8'))
        
        # We do not call client.close() here to allow Vercel
        # to reuse the connection in warm functions.
        return
