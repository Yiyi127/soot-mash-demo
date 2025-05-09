from fastapi import APIRouter, HTTPException, Body, Request, Response
from typing import Dict, Any
import requests
import os
from dotenv import load_dotenv
import json
import time
from datetime import datetime, timedelta

load_dotenv()


router = APIRouter()  

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback.html")
SOOT_API_URL = os.getenv("SOOT_API_URL", "https://api.soot.com/graphql")

# Token cache - in a production app, use a proper database
token_cache = {}

@router.post("/google")
async def google_auth(request_data: Dict[str, Any] = Body(...)):
    """Exchange Google authorization code for access token"""
    code = request_data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")
    
    try:
        print(f"[🔄] Exchanging authorization code for token...")
        
        # Exchange code for Google token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        
        google_tokens = token_response.json()
        
        # Get user info from Google
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        user_info_response = requests.get(
            user_info_url,
            headers={"Authorization": f"Bearer {google_tokens['access_token']}"}
        )
        user_info_response.raise_for_status()
        
        user_info = user_info_response.json()
        print(f"[✅] Got user info: {user_info['email']}")
        
        # Try to connect Google account to SOOT
        try:
            await connect_google_to_soot(google_tokens, user_info)
            print(f"[✅] Successfully connected Google account to SOOT")
        except Exception as e:
            print(f"[⚠️] Failed to connect Google to SOOT: {str(e)}")
            # Continue anyway, we'll use Google token directly
        
        # Store the Google token in our cache
        google_token = google_tokens["access_token"]
        expires_in = google_tokens.get("expires_in", 3600)  # Default 1 hour
        
        token_cache[google_token] = {
            "expiry": datetime.now() + timedelta(seconds=expires_in),
            "user": {
                "id": user_info["id"],
                "displayName": user_info["name"],
                "email": user_info["email"]
            }
        }
        
        # Return Google token to the client
        return {
            "access_token": google_token,
            "expires_in": expires_in,
            "token_type": "Bearer",
            "refresh_token": google_tokens.get("refresh_token"),
            "user_info": {
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info["picture"]
            }
        }
        
    except Exception as e:
        print(f"[❌] Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/refresh")
async def refresh_token(request_data: Dict[str, Any] = Body(...)):
    """Refresh access token using Google refresh token"""
    refresh_token = request_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")
    
    try:
        print(f"[🔄] Refreshing token...")
        
        # Refresh Google token
        token_url = "https://oauth2.googleapis.com/token"
        refresh_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        token_response = requests.post(token_url, data=refresh_data)
        token_response.raise_for_status()
        
        new_google_tokens = token_response.json()
        
        # Get user info from Google
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        user_info_response = requests.get(
            user_info_url,
            headers={"Authorization": f"Bearer {new_google_tokens['access_token']}"}
        )
        user_info_response.raise_for_status()
        
        user_info = user_info_response.json()
        
        # Store the Google token in our cache
        google_token = new_google_tokens["access_token"]
        expires_in = new_google_tokens.get("expires_in", 3600)  # Default 1 hour
        
        token_cache[google_token] = {
            "expiry": datetime.now() + timedelta(seconds=expires_in),
            "user": {
                "id": user_info["id"],
                "displayName": user_info["name"],
                "email": user_info["email"]
            }
        }
        
        # Return Google token to the client
        return {
            "access_token": google_token,
            "expires_in": expires_in,
            "token_type": "Bearer"
        }
        
    except Exception as e:
        print(f"[❌] Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.post("/verify")
async def verify_token(request_data: Dict[str, Any] = Body(...)):
    """Verify if token is valid and not expired"""
    token = request_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    # Check cache for token info
    token_info = token_cache.get(token)
    if token_info:
        current_time = datetime.now()
        expiry_time = token_info.get("expiry")
        
        if expiry_time and current_time < expiry_time:
            return {"valid": True, "expires_in": int((expiry_time - current_time).total_seconds())}
    
    # If not in cache or expired, check if it's valid with Google
    try:
        # Verify token with Google
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        user_info_response = requests.get(
            user_info_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if user_info_response.status_code == 200:
            user_info = user_info_response.json()
            
            # Valid Google token, cache it for future checks
            token_cache[token] = {
                "expiry": datetime.now() + timedelta(hours=1),  # Estimate 1 hour expiry for Google token
                "user": {
                    "id": user_info["id"],
                    "displayName": user_info["name"],
                    "email": user_info["email"]
                }
            }
            return {"valid": True, "expires_in": 3600}  # 1 hour
        
        return {"valid": False}
        
    except Exception:
        # If check fails, token is invalid
        return {"valid": False}

async def connect_google_to_soot(google_tokens: Dict[str, Any], user_info: Dict[str, Any]) -> None:
    """
    Connect Google account to SOOT by making the connectGoogleOAuth mutation
    This doesn't return a token - it just establishes the connection in SOOT
    """
    print(f"[🔄] Connecting Google account to SOOT for user: {user_info['email']}")
    
    try:
        # Use Google token in Authorization header
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {google_tokens['access_token']}"
        }
        
        # Make the connectGoogleOAuth mutation
        mutation = """
        mutation ConnectGoogleOAuth($request: ConnectGoogleOAuthRequest!) {
          connectGoogleOAuth(request: $request) {
            ... on ConnectGoogleOAuthResult {
              viewer {
                id
                displayName
                isGoogleConnected
              }
            }
            ... on PermissionDeniedError {
              reason
            }
            ... on ValidationError {
              field
              reason
            }
          }
        }
        """
        
        # Different SOOT implementations might use different parameters
        variables = {
            "request": {
                "code": google_tokens.get("id_token", google_tokens.get("access_token"))
            }
        }
        
        response = requests.post(
            SOOT_API_URL,
            headers=headers,
            json={"query": mutation, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"[❌] SOOT API error: {response.text}")
            raise Exception(f"Failed to connect Google to SOOT: HTTP {response.status_code}")
        
        result = response.json()
        if "errors" in result:
            print(f"[❌] GraphQL errors: {json.dumps(result['errors'])}")
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        # Check if connection was successful
        connect_result = result.get("data", {}).get("connectGoogleOAuth", {})
        if "viewer" in connect_result:
            is_connected = connect_result["viewer"].get("isGoogleConnected", False)
            if is_connected:
                print(f"[✅] Successfully connected Google account to SOOT")
            else:
                print(f"[⚠️] Connection to SOOT completed but isGoogleConnected is False")
        else:
            # Check for error types
            if "reason" in connect_result:
                print(f"[❌] SOOT connection failed: {connect_result['reason']}")
                raise Exception(f"SOOT connection failed: {connect_result['reason']}")
        
    except Exception as e:
        print(f"[❌] Error connecting Google to SOOT: {str(e)}")
        raise