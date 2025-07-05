# AlgoLab Web Trading Platform

Algolab.com.tr API'sini kullanarak geliştirilmiş web tabanlı trading platformu.

## Özellikler

- Web arayüzü ile kolay kullanım
- TradingView webhook entegrasyonu
- Otomatik oturum yönetimi
- Portföy takibi
- Günlük işlem geçmişi
- Webhook emir geçmişi

## Kurulum

### Localhost Kurulumu

1. Repo'yu klonlayın:
```bash
git clone https://github.com/coinfxpro/AlgoLab_Web.git
cd AlgoLab_Web
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

4. SQLite veritabanını oluşturun:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### Sunucu Kurulumu (Render.com)

1. Render.com'da yeni bir Web Service oluşturun
2. GitHub reponuzu bağlayın
3. Environment variables'ları ayarlayın:
   - `SECRET_KEY`: Rastgele bir string
   - Diğer gerekli environment variables'lar

4. Build Command:
```bash
pip install -r requirements.txt
```

5. Start Command:
```bash
gunicorn app:app
```

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
    "secret": "your-webhook-secret",
    "symbol": "PAPIL",
    "side": "BUY",  // veya "SELL"
    "type": "MARKET",  // veya "LIMIT"
    "price": "0",  // LIMIT emirleri için fiyat
    "quantity": "1"
}
```

### Emir Tipleri

1. **Market (Piyasa) Emirleri**
```json
{
    "secret": "your_secret",
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
    "secret": "your_secret",
    "symbol": "SASA",
    "side": "BUY",
    "type": "LIMIT",
    "price": "3.55",
    "quantity": "1"
}
```
- Limit emirlerde mutlaka `price` belirtin
- Emir belirtilen fiyattan gerçekleşir

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
  -d '{"secret":"your_secret","symbol":"SASA","side":"BUY","type":"MARKET","quantity":"1"}'

# Limit Emri Testi
curl -X POST http://localhost:5001/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"secret":"your_secret","symbol":"SASA","side":"BUY","type":"LIMIT","price":"3.55","quantity":"1"}'
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
