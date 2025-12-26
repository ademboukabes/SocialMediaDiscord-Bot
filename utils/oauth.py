"""
OAuth handler for Facebook Pages
Manages Facebook authentication and token exchange
"""

import aiohttp
from urllib.parse import urlencode
from aiohttp import web
import asyncio
import config


class FacebookOAuth:
    """OAuth handler for Facebook Pages"""
    
    def __init__(self):
        self.app_id = config.FACEBOOK_APP_ID
        self.app_secret = config.FACEBOOK_APP_SECRET
        self.redirect_uri = config.REDIRECT_URI
        self.pending_auth = {}  # server_id -> Future
        self.server = None
        self.runner = None
    
    def get_auth_url(self, server_id):
        """Generate Facebook OAuth URL"""
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'pages_show_list,pages_read_engagement,pages_manage_posts,pages_read_user_content,read_insights',
            'response_type': 'code',
            'state': str(server_id)
        }
        return f"{config.FACEBOOK_OAUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(self, code):
        """Exchange authorization code for user access token"""
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(config.FACEBOOK_TOKEN_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('access_token')
                else:
                    error = await resp.text()
                    raise Exception(f"Token exchange failed: {error}")
    
    async def get_long_lived_token(self, short_token):
        """Get long-lived user token (60 days)"""
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(config.FACEBOOK_TOKEN_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('access_token')
                return short_token  # Return original if exchange fails
    
    async def get_user_pages(self, user_token):
        """Get list of pages user manages"""
        url = f"{config.FACEBOOK_GRAPH_URL}/me/accounts"
        params = {
            'access_token': user_token,
            'fields': 'id,name,access_token,tasks'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error = await resp.text()
                    raise Exception(f"Failed to get pages: {error}")
    
    async def handle_callback(self, request):
        """Handle OAuth callback from Facebook"""
        code = request.query.get('code')
        server_id = request.query.get('state')
        error = request.query.get('error')
        
        if error:
            error_desc = request.query.get('error_description', 'Unknown error')
            return web.Response(text=f'Authorization failed: {error_desc}')
        
        if code and server_id:
            try:
                # Exchange code for user token
                user_token = await self.exchange_code(code)
                
                # Get long-lived user token
                long_token = await self.get_long_lived_token(user_token)
                
                # Get user's pages
                pages_data = await self.get_user_pages(long_token)
                
                # Notify waiting command with pages
                if server_id in self.pending_auth:
                    self.pending_auth[server_id].set_result(pages_data)
                
                return web.Response(text='Facebook connected! You can close this window and return to Discord.')
            except Exception as e:
                print(f'OAuth error: {e}')
                if server_id in self.pending_auth:
                    self.pending_auth[server_id].set_exception(e)
                return web.Response(text=f'Error: {str(e)}')
        
        return web.Response(text='Invalid callback - missing code or state')
    
    async def start_server(self):
        """Start OAuth callback server"""
        if self.server:
            return  # Already running
        
        try:
            app = web.Application()
            app.router.add_get('/callback', self.handle_callback)
            
            self.runner = web.AppRunner(app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, 'localhost', config.OAUTH_PORT)
            await site.start()
            print(f'OAuth callback server started: http://localhost:{config.OAUTH_PORT}')
            self.server = site
        except Exception as e:
            print(f'Failed to start OAuth server: {e}')
            raise
    
    async def stop_server(self):
        """Stop OAuth callback server"""
        if self.runner:
            await self.runner.cleanup()
            self.server = None
            self.runner = None
            print('OAuth server stopped')


# Global OAuth handler
oauth = FacebookOAuth()

import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode
from dotenv import load_dotenv




load_dotenv()
app = FastAPI()

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

GRAPH_API_VERSION = "v20.0"

@app.get("/auth/login")
def login_insta(discord_id: str = None):
    params = {
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement",
        "response_type": "code",
        "state": discord_id or "secure"
    }
    auth_url = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/auth/callback", response_class=HTMLResponse)
def callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        return f"<h2>Login Error: {error}</h2>"

    if not code:
        return "<h2>No authorization code provided</h2>"

    # EXCHANGE CODE FoR SHORT-LIVED TOKEN(security reasons i think)
    token_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    token_response = requests.get(token_url, params={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }).json()

    short_token = token_response.get("access_token")
    if not short_token:
        return f"<h3>Failed to get short-lived token: {token_response}</h3>"

    # SEXCHANGE SHORT TOKEN FOR LONG-LIVED FACEBOOK TOKEN
    long_lived_fb = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token
        }
    ).json().get("access_token")

    if not long_lived_fb:
        return "<h3>Failed to convert to long-lived Facebook token</h3>"
    print("LONG LIVED FB TOKEN :")
    print(long_lived_fb)
    # GET CONNECTED PAGES
    pages = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts",
        params={"access_token": long_lived_fb}
    ).json()
    print("IT ME")
    print(pages)
    if "data" not in pages or len(pages["data"]) == 0:
        return "<h3>No Facebook Pages found. Instagram Business account required.</h3>"

    page = pages["data"][0]
    page_id = page["id"]
    page_token = page["access_token"] 

    # GET INSTAGRAM BUSINESS ACCOUNT ID
    ig_info = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}",
        params={"fields": "instagram_business_account", "access_token": page_token}
    ).json()
    print("ITS ME AGAIN")
    print(ig_info)
    if "instagram_business_account" not in ig_info:
        return "<h3>This Facebook Page is not linked to an Instagram Business Account.</h3>"

    ig_id = ig_info["instagram_business_account"]["id"]

    #INSTAGRAM USERNAME
    user_info = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}",
        params={"fields": "id,username", "access_token": page_token}
    ).json()

    if state and state != "secure_random_string_123":
        try:
            from utils.database import get_db_connection, insert_user
            conn = get_db_connection()
            insert_user(conn, state, user_info['username'], page_token)
            conn.close()
            return f"""
            <h2> Instagram Linked Successfully!</h2>
            <p>Account: <b>{user_info['username']}</b></p>
            <p>You can now close this window and return to Discord.</p>
            """
        except Exception as e:
            return f"<h3>Error saving to database: {str(e)}</h3>"

    return f"""
    <h2> Authentication Complete</h2>
    <p>Instagram Username: <b>{user_info.get('username')}</b></p>
    <p>Your access token (store this):</p>
    <textarea rows="3" cols="60">{page_token}</textarea>
    """

