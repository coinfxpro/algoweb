import time
import threading
import requests
import base64
import json
import hashlib
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

__all__ = ['AlgolabAPI']

class AlgolabAPI:
    def __init__(self, username=None, password=None, api_key=None):
        print("\n==== AlgolabAPI başlatılıyor (Düzeltilmiş Versiyon) ====")
        self.username = username
        self.password = password
        self.api_key = api_key or f"API-{username}" if username else None
        self.hostname = "www.algolab.com.tr"
        self.api_hostname = f"https://{self.hostname}"
        # API taban URL'si (/api uzantısı eklendi)
        self.api_url = f"{self.api_hostname}/api"
        self.token = None
        self.refresh_token = None
        self.last_error = None
        self.headers = {}
        # API rate limit: initialize tracking variables
        self.last_request = 0.0
        self._lock = threading.Lock()
        
        # AES şifreleme için anahtar oluştur
        if self.api_key:
            # APIKEY formatı 'API-<base64_string>' beklenir
            try:
                self.api_code = self.api_key.split("-", 1)[1]
            except IndexError:
                # Prefix yoksa temizle
                self.api_code = self.api_key.replace("API-", "").replace("APIKEY-", "")
            try:
                self.aes_key = base64.b64decode(self.api_code.encode("utf-8"))
            except Exception:
                self.aes_key = None
            self.headers = {
                "APIKEY": self.api_key,
                "Content-Type": "application/json"
            }
        else:
            self.api_code = None
            self.aes_key = None
            
        print("==== AlgolabAPI başlatılıyor (Düzeltilmiş Versiyon) ====")
        print(f"API URL: {self.api_url}")
        print(f"API Key: {self.api_key}")
        print(f"API Hostname: {self.hostname}")
        print("AlgolabAPI başarıyla başlatıldı.")

    def make_checker(self, endpoint, payload):
        """Dokümantasyona göre checker hash'i oluşturur"""
        body = json.dumps(payload).replace(' ', '') if payload else ""
        # Dokümantasyona göre api_hostname (https://...) kullanılmalı
        data = self.api_key + self.api_hostname + endpoint + body
        checker = hashlib.sha256(data.encode('utf-8')).hexdigest()
        print(f"Checker için kullanılan data: {data}")
        print(f"Checker hash sonucu: {checker}")
        return checker
        
    def post(self, endpoint, payload, login=False, retry=True):
        '''Dokümantasyondaki örnek koda uygun post metodu.
        Bu metot Algolab API'sinde iki farklı endpoint yapısını destekler:
        1. Tam path içeren ("/api/...") endpoint'ler → URL = https://www.algolab.com.tr + endpoint
        2. Kısa path ("/api/SendOrder" vb.) endpoint'ler → URL = https://www.algolab.com.tr/api + endpoint
        Böylece iki durumda da '/api/api' gibi tekrarlı path oluşması engellenir.
        '''
        print(f"Endpoint: '{endpoint}'")  # Debug: endpoint değerini göster

        # Endpoint mutlaka '/' ile başlamalı
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"

        # Tam URL oluştur – basitçe api_url + endpoint (doküman örneğiyle uyumlu)
        url = f"{self.api_url}{endpoint}"
        print(f"Tam URL: {url}")
        
        headers = self.headers.copy()
        
        if not login:
            # Checker yalnızca giriş dışındaki isteklerde zorunludur
            if self.api_key:
                checker = self.make_checker(endpoint, payload)
                headers["Checker"] = checker
            # Authorization başlığı oturum hash'i ile eklenir
            if self.hash:
                # Send raw hash token without Bearer prefix as per API documentation
                headers["Authorization"] = self.hash
                print(f"Authorization header set to: {self.hash[:20]}...")
                
        print(f"Outgoing API call to {url}")
        print(f"Payload: {json.dumps(payload)}")
        print(f"Headers: {headers}")

        response = self._request(url, payload, headers)

        # 401 Unauthorized durumunda oturumu yenileyip isteği bir kez daha dene
        if not login and retry and response is not None and hasattr(response, "status_code") and response.status_code == 401:
            print("401 yanıtı alındı, SessionRefresh deneniyor...")
            if self.SessionRefresh():
                print("SessionRefresh başarılı, isteği tekrar gönderiliyor.")
                return self.post(endpoint, payload, login=login, retry=False)
        return response
        
    def _request(self, url, payload, headers):
        """Dokümantasyondaki örnek koda uygun _request metodu"""
        try:
            print("\n=== API İsteği Gönderiliyor ===")
            print(f"URL: {url}")
            print(f"Payload: {payload}")
            print(f"Headers: {headers}")
            
            # --- Rate limit handling: ensure minimum 5s interval between API calls ---
            with self._lock:
                now = time.time()
                if self.last_request and (now - self.last_request) < 5:
                    wait_time = 5 - (now - self.last_request) + 0.01
                    print(f"Rate limit aktif. {wait_time:.2f} sn bekleniyor...")
                    time.sleep(wait_time)
                response = requests.post(url, json=payload, headers=headers)
                # Update timestamp after request is sent
                self.last_request = time.time()
            
            print("\n=== API Yanıtı Alındı ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Content-Type: {response.headers.get('Content-Type', 'Belirtilmemiş')}")
            
            # Yanıtın ilk 500 karakterini göster
            response_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
            print(f"Response Text: {response_preview}")
            print()
            
            if response.status_code == 401:
                print("UYARI: API'den 401 Unauthorized geldi! Token/hash veya header formatı hatalı olabilir.")
                # 401 durumunda yanıtı çağıran metoda ilet
                return response
            if response.status_code != 200:
                print(f"HATA: HTTP Hatası: {response.status_code}")
                return None
            return response
        except Exception as e:
            print(f"HATA: İstek gönderilirken hata oluştu: {e}")
            return None


    # -------------------- Oturum Yenileme --------------------
    def SessionRefresh(self):
        '''
        /api/SessionRefresh ile oturumu yeniler.
        Algolab dökümantasyonuna göre bu endpoint sadece Boolean (true/false) dönebilir
        veya bazı sürümlerde {"success": true} biçiminde JSON dönebilir. Her iki durumu da
        destekleyecek şekilde yanıtı işler. Başarılıysa True, aksi hâlde False döner.
        '''
        endpoint = "/api/SessionRefresh"
        payload = {}

        # login=False => Authorization ve Checker header'ları gönderilir
        response = self.post(endpoint, payload, login=False, retry=False)

        # HTTP isteği başarısız olduysa
        if not response:
            print("SessionRefresh: HTTP isteği başarısız.")
            return False

        # Sunucu 200 OK döndürdüyse yanıt gövdesini incele
        if response.status_code == 200:
            try:
                result = response.json()
            except ValueError as ve:
                # Örneğin boş gövde geldi
                print(f"SessionRefresh: JSON decode hatası: {ve}")
                return False

            # Yanıt boolean olabilir
            if isinstance(result, bool):
                if result:
                    print("SessionRefresh: Başarılı (bool true).")
                    return True
                print("SessionRefresh: Sunucu false döndü.")
                return False

            # Yanıt sözlük ise 'success' anahtarını kontrol et
            if isinstance(result, dict):
                if result.get("success") is True:
                    print("SessionRefresh: Başarılı (success:true).")
                    return True
                print(f"SessionRefresh: success:false veya anahtar eksik – yanıt: {result}")
                return False

            # Beklenmedik veri tipi
            print(f"SessionRefresh: Beklenmedik yanıt tipi: {type(result)} – {result}")
            return False

        # 200 dışındaki durum kodu
        print(f"SessionRefresh: HTTP {response.status_code} – oturum yenileme başarısız.")
        return False

    # -------------------- Genel Hata Kontrolü --------------------
    def error_check(self, response, func_name=""):
        """Algolab örnek kodundaki yardımcı fonksiyon. Başarılı durumda response.json() sözlüğünü döner, aksi halde yapısal hata mesajı üretir."""
        if response is None:
            return {"success": False, "message": f"{func_name}: HTTP isteği başarısız"}
        try:
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"{func_name}: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"{func_name}: JSON decode hatası - {e}"}

    def LoginUser(self):
        """Kullanıcı girişi yapar ve SMS onayı için token alır."""
        try:
            if not self.username or not self.password:
                self.last_error = "Kullanıcı adı ve şifre gerekli"
                return None
                
            # Dokümantasyona göre kullanıcı adı ve şifre AES ile şifrelenerek gönderilir
            enc_username = self.encrypt(self.username)
            enc_password = self.encrypt(self.password)
            payload = {
                "username": enc_username,
                "password": enc_password
            }
            
            endpoint = "/api/LoginUser"
            
            response = self.post(endpoint, payload, login=True)
            
            if response and response.status_code == 200:
                try:
                    # JSON yanıtı ayrıştırmayı dene
                    result = response.json()
                    print(f"API yanıtı (JSON): {result}")
                    
                    if result.get("success"):
                        content = result.get('content', {}) or {}
                        self.token = content.get('token') or result.get('token') or ''
                        self.refresh_token = content.get('refreshToken') or result.get('refreshToken') or ''
                        print(f"LoginUser başarılı, token: {self.token}")
                        return self.token
                    else:
                        self.last_error = result.get("message", "Bilinmeyen giriş hatası.")
                        print(f"LoginUser başarısız: {self.last_error}")
                except json.JSONDecodeError as je:
                    # JSON ayrıştırma hatası - yanıt HTML olabilir
                    print(f"API yanıtı geçerli bir JSON değil: {je}")
                    print("API yanıtı HTML içeriyor olabilir. API URL yapısını kontrol edin.")
                    
                    # HTML yanıtının ilk 200 karakterini göster
                    html_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    print(f"HTML yanıtı önizleme: {html_preview}")
                    
                    self.last_error = "API yanıtı geçerli bir JSON değil"
            else:
                print("LoginUser isteği başarısız oldu.")
            return None
        except Exception as e:
            print(f"HATA: LoginUser içinde beklenmedik hata: {e}")
            self.last_error = str(e)
            return None

    def LoginUserControl(self, sms_code):
        """SMS doğrulama kodunu kontrol eder ve giriş yapar."""
        try:
            if not self.token or not sms_code:
                self.last_error = "Token veya SMS kodu eksik"
                return False
                
            # Dokümantasyona göre token ve SMS kodu AES ile şifrelenerek gönderilir
            enc_token = self.encrypt(self.token)
            enc_sms = self.encrypt(sms_code)
            payload = {
                "token": enc_token,
                "password": enc_sms
                # Not: API dokümanlarında bazen 'Password' anahtarı büyük 'P' ile verilmektedir.
                # Gerekirse 'Password': enc_sms şeklinde değiştirilebilir.
            }
            
            endpoint = "/api/LoginUserControl"
            # login=True -> Checker eklenmez
            response = self.post(endpoint, payload, login=True)
            
            if response and response.status_code == 200:
                try:
                    result = response.json()
                    print(f"API yanıtı (JSON): {result}")
                    
                    if result.get("success"):
                        # Hash değeri content içinde dönüyor
                        content = result.get('content', {}) or {}
                        self.hash = content.get('hash')
                        print(f"SMS doğrulama başarılı, hash alındı: {self.hash[:20]}...") if self.hash else print("SMS doğrulama başarılı fakat hash alınamadı")
                        return True
                    else:
                        self.last_error = result.get("message", "SMS doğrulama başarısız.")
                        print(f"SMS doğrulama başarısız: {self.last_error}")
                except json.JSONDecodeError as je:
                    self.last_error = "API yanıtı geçerli bir JSON değil"
                    print(f"API yanıtı geçerli bir JSON değil: {je}")
                    
                    # HTML yanıtının ilk 200 karakterini göster
                    html_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    print(f"HTML yanıtı önizleme: {html_preview}")
            else:
                print("LoginUserControl isteği başarısız oldu.")
            return False
        except Exception as e:
            print(f"HATA: LoginUserControl içinde beklenmedik hata: {e}")
            self.last_error = str(e)
            return False

    def GetInstantPosition(self, sub_account=""):
        """Anlık pozisyon bilgilerini getirir."""
        if not self.hash:
            self.last_error = "Oturum açık değil"
            return None
            
        endpoint = "/api/InstantPosition"
        # Algolab dökümantasyonuna uygun olarak 'Subaccount' anahtarını kullan
        payload = {"Subaccount": sub_account}
        
        # İlk istek
        response = self.post(endpoint, payload)
        if not response:
            return None
        result = response.json()

        # API 5 saniye kuralına takıldıysa kısa bir bekleme sonrası tekrar dene
        if not result.get("success") and "5" in str(result.get("message", "")):
            print("Rate limit mesajı alındı (InstantPosition). 5 saniye beklenip tekrar deneniyor...")
            time.sleep(5)
            response = self.post(endpoint, payload)
            if not response:
                return None
            result = response.json()

        if result.get("success"):
            return result.get("content")
        else:
            self.last_error = result.get("message", "Pozisyon bilgileri alınamadı")
            return None

    def GetEquityInfo(self, symbol=None):
        """Hisse senedi bilgilerini getirir."""
        if not self.hash:
            self.last_error = "Oturum açık değil"
            return None
            
        endpoint = "/api/GetEquityInfo"
        payload = {}
        if symbol:
            payload["symbol"] = symbol
        
        response = self.post(endpoint, payload)
        if not response:
            return None
            
        result = response.json()
        if result.get("success"):
            return result.get("content")
        else:
            self.last_error = result.get("message", "Hisse senedi bilgileri alınamadı")
            return None

    def RiskSimulation(self):
        """Risk simülasyonu bilgilerini getirir."""
        if not self.hash:
            self.last_error = "Oturum açık değil"
            return None
            
        endpoint = "/api/RiskSimulation"
        payload = {"Subaccount": ""}
        
        # İlk istek
        response = self.post(endpoint, payload)
        if not response:
            return None
        result = response.json()

        # API 5 saniye kuralına takıldıysa kısa bir bekleme sonrası tekrar dene
        if not result.get("success") and "5" in str(result.get("message", "")):
            print("Rate limit mesajı alındı (RiskSimulation). 5 saniye beklenip tekrar deneniyor...")
            time.sleep(5)
            response = self.post(endpoint, payload)
            if not response:
                return None
            result = response.json()

        if result.get("success"):
            return result.get("content")
        else:
            self.last_error = result.get("message", "Risk simülasyonu bilgileri alınamadı")
            return None

    def GetCandleData(self, symbol, period="1440"):
        '''Belirtilen sembol için OHLCV verisi getirir.
        period dakika cinsinden (1,5,15,60,1440).
        '''
        endpoint = "/api/GetCandleData"
        payload = {
            "symbol": symbol,
            "period": period
        }
        response = self.post(endpoint, payload)
        if not response:
            return None
        result = response.json()
        if result.get("success"):
            return result.get("content")
        else:
            self.last_error = result.get("message", "Candle verisi alınamadı")
            return None

    def CashFlow(self, sub_account=""):
        """Nakit akışı/bakiye bilgilerini getirir."""
        if not self.hash:
            self.last_error = "Oturum açık değil"
            return None
        endpoint = "/api/CashFlow"
        payload = {"Subaccount": sub_account}
        # İlk istek
        response = self.post(endpoint, payload)
        if not response:
            return None
        result = response.json()

        # API 5 saniye kuralına takıldıysa kısa bir bekleme sonrası tekrar dene
        if not result.get("success") and "5" in str(result.get("message", "")):
            print("Rate limit mesajı alındı (CashFlow). 5 saniye beklenip tekrar deneniyor...")
            time.sleep(5)
            response = self.post(endpoint, payload)
            if not response:
                return None
            result = response.json()

        if result.get("success"):
            return result.get("content")
        else:
            self.last_error = result.get("message", "Nakit bilgileri alınamadı")
            return None

    def encrypt(self, text):
        """Dokümantasyondaki örnek koda uygun AES şifreleme fonksiyonu."""
        if text is None:
            return None
            
        try:
            iv = b'\0' * 16
            
            # Önceden türetilmiş AES anahtarını kullan
            key = self.aes_key
            if not key:
                print("HATA: AES anahtarı oluşturulamadı")
                return None
            
            # AES-CBC şifreleme
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Metni byte'a çevir ve padding ekle
            text_bytes = text.encode('utf-8')
            padded_text = pad(text_bytes, AES.block_size)
            
            # Şifrele ve Base64 ile kodla
            encrypted = cipher.encrypt(padded_text)
            encoded = base64.b64encode(encrypted).decode('utf-8')
            
            print(f"Şifreleme başarılı: {text} -> {encoded[:10]}...")
            return encoded
            
        except Exception as e:
            print(f"HATA: Şifreleme sırasında hata oluştu: {e}")
            return None

    def SendOrder(self, symbol, side, quantity, price=None, order_type='Market'):
        """Yeni bir emir gönderir."""
        endpoint = "/api/SendOrder"
        payload = {
            "symbol": symbol.upper(),
            "direction": side.upper(),              # BUY / SELL
            "pricetype": order_type.lower(),        # market / limit
            "price": str(price) if price not in (None, "", 0) else "0",
            "lot": str(quantity),
            "sms": False,
            "email": False,
            "subAccount": ""
        }
        response = self.post(endpoint, payload)
        return self.error_check(response, "SendOrder")

    def DeleteOrder(self, order_id, sub_account=""):
        """Mevcut bir emri iptal eder.

        Parametreler
        ----------
        order_id : str
            İptal edilecek emrin benzersiz ID değeri.
        sub_account : str, optional
            Alt hesap numarası. Boş gönderilirse aktif hesabı kullanır.
        """
        endpoint = "/api/DeleteOrder"
        payload = {
            "id": order_id,
            "subAccount": sub_account
        }
        response = self.post(endpoint, payload)
        return self.error_check(response, "DeleteOrder")

    # ---------------------------------------------------------------------
    # --------------   EMİR LİSTESİ (Bekleyen Emirler)  -------------------
    # ---------------------------------------------------------------------
    def TodaysTransaction(self, sub_account: str = ""):
        """Algolab /api/TodaysTransaction endpoint'ini çağırarak gün içindeki
        tüm işlemleri (bekleyen, gerçekleşen, kısmi, silinmiş vb.) döner.

        Dönüşteki sözlük yapısı dokümantasyona göre
            {
                "success": true,
                "message": "",
                "content": [ {...}, {...} ]
            }
        şeklindedir. Başarısız durumda `None` döner ve `self.last_error` güncellenir.
        """
        if not self.hash:
            self.last_error = "Oturum açık değil"
            return None

        endpoint = "/api/TodaysTransaction"
        payload = {"Subaccount": sub_account}

        response = self.post(endpoint, payload)
        result = self.error_check(response, "TodaysTransaction")
        if not result.get("success"):
            self.last_error = result.get("message", "TodaysTransaction başarısız")
            return None

        return result.get("content", [])

    def GetOpenOrders(self, sub_account: str = ""):
        """`TodaysTransaction` çıktısından *açık (bekleyen)* emirleri süzer ve
        bizim uygulamanın beklediği sözlük alan adlarına dönüştürür.

        Dönen liste doğrudan `trading.html` şablonuna gönderilebilir.
        """
        tx_list = self.TodaysTransaction(sub_account)
        if tx_list is None:
            return None  # self.last_error zaten set edildi

        open_orders = []
        for item in tx_list:
            status_key = (item.get("equityStatusDescription") or "").upper()
            # WAITING: bekleyen, PARTIAL: kısmi gerçekleşen (halen açık)
            if status_key not in ("WAITING", "PARTIAL"):
                continue

            waiting_price = item.get("waitingprice") or item.get("price") or "-"
            try:
                # Fiyat "2.050000" gibi string olabilir → float'a dönersek sınırlı toksin
                price_float = float(str(waiting_price).replace(",", ".")) if waiting_price not in (None, "", "-") else None
            except ValueError:
                price_float = None

            pricetype = "limit" if price_float not in (None, 0) else "market"

            mapped = {
                "id": item.get("transactionId") or item.get("id") or item.get("atpref"),
                "atpref": item.get("atpref") or item.get("transactionId") or item.get("id"),
                "ticker": item.get("ticker"),
                "buysell": item.get("buysell", "-").upper(),
                "pricetype": pricetype,
                "waitingprice": waiting_price,
                "ordersize": item.get("ordersize"),
                "remainingsize": item.get("remainingsize"),
                "description": status_key  # WAITING / PARTIAL
            }
            open_orders.append(mapped)

        return open_orders
