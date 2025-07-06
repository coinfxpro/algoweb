# AlgoLab Web Trading Platform

Algolab.com.tr API'sini kullanarak geliştirilmiş web tabanlı trading platformu.

## Proje Yapısı ve Çalışma Mantığı

Bu proje, Algolab API'sini kullanarak borsa işlemlerini web arayüzü üzerinden gerçekleştirmenizi sağlar. Temel bileşenleri:

- **Flask Web Uygulaması (`app.py`)**: Kullanıcı arayüzü ve API endpoint'lerini sağlar
- **Algolab API Entegrasyonu (`algolab_api.py`)**: Algolab.com.tr API'si ile iletişimi sağlar
- **Tick to OHLCV Dönüştürücü (`tick_to_ohlcv_converter.py`)**: Gerçek zamanlı işlem verilerini OHLCV (Open-High-Low-Close-Volume) formatına dönüştürür
- **WebSocket Bağlantısı (`ws.py`)**: Gerçek zamanlı veri akışı için WebSocket bağlantısını yönetir
- **Oturum Yönetimi (`session_manager.py`)**: API oturumlarını otomatik olarak yeniler

### Veri Akışı

1. Kullanıcı web arayüzünden veya webhook aracılığıyla emir gönderir
2. Uygulama, Algolab API'sine istek yapar
3. API yanıtı işlenir ve kullanıcıya gösterilir
4. WebSocket bağlantısı ile gerçek zamanlı veri akışı sağlanır

## Özellikler

- Web arayüzü ile kolay kullanım
- TradingView webhook entegrasyonu
- Otomatik oturum yönetimi
- Portföy takibi
- Günlük işlem geçmişi
- Webhook emir geçmişi
- Gerçek zamanlı veri akışı
- OHLCV veri dönüşümü

## Kurulum

### Localhost Kurulumu

1. Repo'yu klonlayın:
```bash
git clone https://github.com/coinfxpro/algoweb.git
cd algoweb
```

2. Virtual environment oluşturun (opsiyonel ama önerilen):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
.\venv\Scripts\activate  # Windows
```

3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. `config.py` dosyasını düzenleyin:
```python
# USER INFO
MY_API_KEY='API-KEY' # API Key'inizi Buraya Giriniz
MY_USERNAME = "TC veya Denizbank Kullanici Adi" # TC veya Denizbank Kullanıcı Adınızı Buraya Giriniz
MY_PASSWORD = "Şifre" # Denizbank İnternet Bankacılığı Şifrenizi Buraya Giriniz
```

5. Uygulamayı çalıştırın:
```bash
python app.py
```

### Render.com Üzerinde Kurulum

1. GitHub hesabınızda bu repo'yu fork edin veya doğrudan Render.com'a bağlanın

2. Render.com'da yeni bir Web Service oluşturun:
   - **Name**: AlgoLab Web
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

3. Environment Variables ayarlayın:
   - `WEBHOOK_SECRET`: Güvenli bir rastgele string (webhook güvenliği için)
   - `PYTHON_VERSION`: 3.11.0

4. Advanced Settings:
   - Auto-Deploy: Yes (GitHub repo'nuz güncellendiğinde otomatik dağıtım için)
   - Health Check Path: `/`
   - Instance Type: Free (başlangıç için) veya Basic (üretim için)

5. Create Web Service butonuna tıklayın ve dağıtımın tamamlanmasını bekleyin

## Kullanım

### İlk Kurulum

1. Web arayüzüne giriş yapın (`/login`)
2. Algolab API bilgilerinizi girin:
   - API Key
   - Username
   - Password
3. SMS doğrulamasını tamamlayın
4. Webhook secret key oluşturun (`/webhook-settings`)

### TradingView Webhook Ayarları

1. TradingView stratejinizde webhook URL'sini ayarlayın:
```
https://your-app-url.com/webhook/tradingview
```

2. Webhook mesaj formatı:
```json
{
    "passphrase": "your-webhook-secret",
    "symbol": "PAPIL",
    "side": "BUY",  // veya "SELL"
    "type": "MARKET",  // veya "LIMIT"
    "price": "0",  // LIMIT emirleri için fiyat
    "quantity": "1"  // Lot miktarı 1 ve katları olmalıdır
}
```

3. Webhook Emir Durumları:
   - **Emir İletildi**: Emir Algolab API'ye başarıyla iletildi
   - **Hata**: Emir gönderiminde bir hata oluştu (hata detayı gösterilir)
   - **Bekliyor**: Emir işleniyor

### Emir Tipleri

1. **Market (Piyasa) Emirleri**
```json
{
    "passphrase": "your_webhook_secret",
    "symbol": "SASA",
    "side": "BUY",
    "type": "MARKET",
    "quantity": "1"
}
```
- Market emirlerinde `price` belirtmeyin
- Emir anında piyasa fiyatından gerçekleşir

2. **Limit Emirleri**
```json
{
    "passphrase": "your_webhook_secret",
    "symbol": "SASA",
    "side": "BUY",
    "type": "LIMIT",
    "price": "3.55",
    "quantity": "1"
}
```
- Limit emirlerde mutlaka `price` belirtin
- Emir belirtilen fiyattan gerçekleşir
- Lot miktarı 1 ve katları olmalıdır (1, 2, 3 vb.)

### Önemli Notlar

1. **Oturum Yönetimi**:
   - İlk login ve SMS doğrulaması gereklidir
   - Sonraki webhook işlemleri otomatik çalışır
   - Oturumlar otomatik yenilenir (10 dakikada bir)
   - Web uygulamasını kapatabilirsiniz, webhook'lar çalışmaya devam eder

2. **Render.com Kullanımı**:
   - Ücretsiz planda 15 dakika inaktivite sonrası uyku moduna geçer
   - Uptime Robot ile uyanık tutulabilir
   - Aylık 750 saat çalışma sınırı vardır

3. **Uptime Robot Kurulumu** (Opsiyonel):
   - Uptimerobot.com'da hesap oluşturun
   - Yeni HTTP(s) monitör ekleyin
   - URL: `https://your-app-url.com/health`
   - 5 dakika kontrol aralığı ayarlayın

## Güvenlik

1. Webhook secret key'inizi güvende tutun
2. API bilgilerinizi environment variables olarak saklayın
3. Güçlü şifreler kullanın

## Sorun Giderme

1. **401 Hatası**:
   - Yeniden login olun
   - SMS doğrulaması yapın

2. **Webhook Çalışmıyor**:
   - Secret key'i kontrol edin
   - Sunucunun uyanık olduğundan emin olun
   - Logları kontrol edin

3. **Sunucu Uyku Modu**:
   - Uptime Robot kullanın
   - veya Pro plana geçin

### Test Etme

Webhook'u test etmek için cURL kullanabilirsiniz:

```bash
# Market Emri Testi
curl -X POST http://localhost:5001/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"passphrase":"your_webhook_secret","symbol":"SASA","side":"BUY","type":"MARKET","quantity":"1"}'

# Limit Emri Testi
curl -X POST http://localhost:5001/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"passphrase":"your_webhook_secret","symbol":"SASA","side":"BUY","type":"LIMIT","price":"3.55","quantity":"1"}'
```

## Notlar

- Market emirleri anında piyasa fiyatından gerçekleşir
- Limit emirler belirtilen fiyata gelene kadar bekler
- Her kullanıcının kendine özel webhook secret key'i vardır
- Webhook üzerinden gelen emirler "Webhook Emirleri" sayfasında görüntülenir

## Güvenlik

- Her webhook isteği için secret key kontrolü yapılır
- Secret key'ler veritabanında güvenli şekilde saklanır
- Her kullanıcı sadece kendi emirlerini görüntüleyebilir

## Sorun Giderme

**Port 5001 kullanımda hatası:**
```bash
# Portu kullanan işlemi bulun
lsof -i :5001

# İşlemi sonlandırın
kill -9 <PID>

# Veya tek komutla
kill -9 $(lsof -t -i:5001)
```

## Lisans

MIT
