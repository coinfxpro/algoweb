import time
import threading
from algolab_api import AlgolabAPI

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.token_refresh_thread = None
        self.running = True
        self.start_token_refresh_thread()
    
    def get_session(self, api_key):
        """Get session for given API key"""
        return self.sessions.get(api_key)

    def start_token_refresh_thread(self):
        def refresh_tokens():
            while self.running:
                current_time = time.time()
                for api_key in list(self.sessions.keys()):
                    session = self.sessions.get(api_key)
                    if session and current_time - session.get('last_refresh', 0) >= 540:  # 9 minutes
                        try:
                            self.refresh_session_token(api_key)
                        except Exception as e:
                            print(f"Token refresh error for {api_key}: {str(e)}")
                time.sleep(60)  # Check every minute

        if not self.token_refresh_thread:
            self.token_refresh_thread = threading.Thread(target=refresh_tokens, daemon=True)
            self.token_refresh_thread.start()

    def refresh_session_token(self, api_key):
        """Refresh token for given API key"""
        session = self.sessions.get(api_key)
        if not session:
            return False
        
        try:
            algolab_api = AlgolabAPI(api_key)
            new_token = algolab_api.refresh_token(session['refresh_token'])
            if new_token:
                session['token'] = new_token
                session['last_refresh'] = time.time()
                self.sessions[api_key] = session
                return True
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
        return False

    def create_session(self, api_key, token, refresh_token):
        """Create new session for API key"""
        self.sessions[api_key] = {
            'token': token,
            'refresh_token': refresh_token,
            'last_refresh': time.time()
        }
        return True

# Singleton instance
session_manager = SessionManager()
