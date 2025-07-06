from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from functools import wraps
from algolab_api import AlgolabAPI
import os
from datetime import datetime, timedelta
import json
import time
from collections import deque

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ----- Webhook globals -----
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
WEBHOOK_ORDERS = deque(maxlen=200)  # Recent webhook orders

# ----- Strategy storage (in-memory for now) -----
STRATEGIES = []  # Each item: {'id': int, 'data': {...}}
NEXT_STRATEGY_ID = 1
OPEN_ORDERS = []  # In-memory list of open orders created via manual trading page

# Login gerektiren sayfalar için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Oturum kontrolü
        if 'token' not in session or 'hash' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        
        # Her istekte oturum yenileme işlemi yapalım
        try:
            # Son oturum yenileme zamanını kontrol et
            last_refresh = session.get('last_refresh_time', 0)
            current_time = time.time()
            
            # 10 dakikada bir oturumu yenile (600 saniye)
            if current_time - last_refresh > 600:
                print("\n=== Oturum yenileniyor... ===")
                username = session.get('username')
                api_key = session.get('api_key')
                token = session.get('token')
                hash_value = session.get('hash')
                
                # API nesnesini oluştur ve oturumu yenile
                api = AlgolabAPI(username=username, api_key=api_key)
                api.token = token
                api.hash = hash_value
                
                # Oturum yenileme işlemi
                if api.SessionRefresh():
                    # Oturum başarıyla yenilendi, hash değeri güncellendi
                    session['hash'] = api.hash
                    session['last_refresh_time'] = current_time
                    print("=== Oturum başarıyla yenilendi ===")
                else:
                    print("=== Oturum yenileme başarısız! ===")
                    # Oturum yenileme başarısız olduysa, kullanıcıyı login sayfasına yönlendir
                    if request.path != url_for('login'):
                        flash('Oturum süreniz doldu. Lütfen tekrar giriş yapın.', 'warning')
                        return redirect(url_for('login'))
        except Exception as e:
            print(f"Oturum yenileme hatası: {str(e)}")
            # Hata durumunda sessizce devam et, ana işlevi engelleme
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    # Kullanıcı zaten giriş yapmışsa dashboard'a, yapmamışsa login'e yönlendir
    if 'access_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global api_instance, last_login_time
    
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # AlgolabAPI sınıfını kullan
            api_instance = AlgolabAPI(username=username, password=password, api_key=api_key)
            
            # İlk login işlemi
            token = api_instance.LoginUser()
            if not token:
                raise Exception(api_instance.last_error or "Login başarısız")
            
            # Login zamanını kaydet
            last_login_time = datetime.now()
            
            # Session'a bilgileri kaydet
            session['api_key'] = api_key
            session['username'] = username
            session['password'] = password
            session['token'] = token
            session['logged_in'] = True
            
            # SMS doğrulama sayfasına yönlendir
            return redirect(url_for('verify_sms'))
            
        except Exception as e:
            flash(f'Giriş hatası: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/verify_sms', methods=['GET', 'POST'])
def verify_sms():
    global api_instance
    
    if request.method == 'POST':
        sms_code = request.form.get('sms_code')
        
        if not sms_code:
            flash('SMS kodu gereklidir.', 'danger')
            return render_template('verify_sms.html')
        
        try:
            # Yeni AlgolabAPI sınıfı ile SMS doğrulama
            if api_instance.LoginUserControl(sms_code):
                # Başarılı giriş
                # Session'a bilgileri kaydet
                session['token'] = api_instance.token
                session['refresh_token'] = api_instance.refresh_token
                session['hash'] = api_instance.hash
                session['logged_in'] = True
                
                flash('Başarıyla giriş yaptınız!', 'success')
                return redirect(url_for('dashboard'))
            else:
                raise Exception(api_instance.last_error or "SMS doğrulama başarısız")
            
        except Exception as e:
            flash(f'SMS doğrulama hatası: {str(e)}', 'danger')
    
    return render_template('verify_sms.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # summary dict oluşturulması ve güncellenmesi
    summary = {
        't0_nakit': 0.0,
        't1_nakit': 0.0,
        't2_nakit': 0.0,
        't0_hisse': 0.0,
        't1_hisse': 0.0,
        't2_hisse': 0.0,
        't0_toplam': 0.0,
        't1_toplam': 0.0,
        't2_toplam': 0.0,
        't0_ozkaynakoran': 0.0,
        't1_ozkaynakoran': 0.0,
        't2_ozkaynakoran': 0.0,
        'nakit_haric_toplam': 0.0,
        'aciga_satis_limit': 0.0,
        'kredi_bakiye': 0.0,
        'total_try_amount': 0.0
    }
    username = session.get('username')
    token = session.get('token')
    hash_value = session.get('hash')
    
    # AlgolabAPI nesnesini oturum bilgileriyle başlat (API key dahil)
    api = AlgolabAPI(username=username, api_key=session.get('api_key'))
    api.token = token
    api.hash = hash_value
    
    # Portföy bilgilerini al
    raw_portfolio = api.GetInstantPosition()
    if raw_portfolio is None:
        flash(f"Portföy verisi alınamadı: {api.last_error}", "warning")
        raw_portfolio = []

    def map_position(item):
        try:
            maliyet = float(item.get("maliyet", 0))
            lot = float(item.get("totalstock", 0))
            guncel_fiyat = float(item.get("unitprice", 0))
            toplam_maliyet = maliyet * lot
            toplam_deger = guncel_fiyat * lot
            kar_zarar = toplam_deger - toplam_maliyet
            kar_zarar_yuzde = (kar_zarar / toplam_maliyet * 100) if toplam_maliyet > 0 else 0
        except Exception:
            maliyet = lot = guncel_fiyat = toplam_maliyet = toplam_deger = kar_zarar = kar_zarar_yuzde = 0
        return {
            "symbol": item.get("code", "-"),
            "lot": lot,
            "alis_maliyeti": maliyet,
            "guncel_fiyat": guncel_fiyat,
            "toplam_maliyet": toplam_maliyet,
            "toplam_deger": toplam_deger,
            "kar_zarar": kar_zarar,
            "kar_zarar_yuzde": kar_zarar_yuzde,
        }
    portfolio = [map_position(item) for item in raw_portfolio]

    # Risk simülasyonu verisi
    risk_data = api.RiskSimulation() or {}

    # Nakit akışı verisi
    cash_data = api.CashFlow() or {}

    # Dashboard özet kutuları için default değerler
    summary = {
        'total_cost': 0,
        'total_profit_loss': 0,
        'total_value': 0,
        't0_nakit': 0,
        't1_nakit': 0,
        't2_nakit': 0,
        'kredi': 0,
        'equity': 0,
        'risk': 0,
        'total_try_amount': 0,
    }
    # Portfolio summary
    if portfolio:
        summary['total_cost'] = sum(item['toplam_maliyet'] for item in portfolio)
        summary['total_profit_loss'] = sum(item['kar_zarar'] for item in portfolio)
        summary['total_value'] = sum(item['toplam_deger'] for item in portfolio)
    # Cash summary
    if cash_data:
        summary['t0_nakit'] = cash_data.get('T0', 0)
        summary['t1_nakit'] = cash_data.get('T1', 0)
        summary['t2_nakit'] = cash_data.get('T2', 0)
        summary['kredi'] = cash_data.get('Kredi', 0)
    # Risk summary
    if risk_data:
        summary['equity'] = risk_data.get('Equity', 0)
        summary['risk'] = risk_data.get('Risk', 0)
    # Toplam TRY
    summary['total_try_amount'] = summary['t0_nakit'] + summary['t1_nakit'] + summary['t2_nakit']

    return render_template('dashboard.html', username=username, portfolio=portfolio, summary=summary)

    return render_template('dashboard.html',
                           username=username,
                           portfolio=portfolio,
                           summary=summary)

@app.route('/websocket')
@login_required
def websocket_page():
    api_key_full = session.get('api_key_full')
    access_token = session.get('access_token')
    
    if not api_key_full or not access_token:
        flash('Oturum süreniz doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))
        
    return render_template('websocket.html', 
                           api_key=api_key_full, 
                           token=access_token, 
                           socket_url=f"wss://www.algolab.com.tr/api/ws")

# ----------------- Ek Sayfalar (Basit Yer Tutucu) -----------------

@app.route('/market_data')
@login_required
def market_data():
    """Piyasa verileri sayfası – Algolab API'den /api/GetEquityInfo sonucunu çeker."""
    username = session.get('username')
    api_key = session.get('api_key')
    token = session.get('token')
    hash_value = session.get('hash')

    api = AlgolabAPI(username=username, api_key=api_key)
    api.token = token
    api.hash = hash_value

    # Algolab API'de /api/GetEquityInfo endpoint'i için 'symbol' parametresi zorunludur.
    # Gösterilecek bazı yaygın BIST sembollerini sorguluyoruz.
    default_symbols = ["GARAN", "AKBNK", "THYAO", "SISE", "BIMAS"]
    symbols = []

    for sym in default_symbols:
        equity = api.GetEquityInfo(sym)
        if equity is None:
            print(f"GetEquityInfo failed for {sym}: {api.last_error}")
            continue

        # Dönen JSON alanları tutarsız olabildiği için olası varyasyonlar kontrol ediliyor
        last_price = (equity.get('lst') or equity.get('LastPrice') or
                      equity.get('Last') or equity.get('last_price'))
        change_pct = (equity.get('ChangePercentage') or equity.get('changePercent') or
                      equity.get('ChangePercent') or equity.get('PercentChange') or 0)
        high = equity.get('high') or equity.get('High') or equity.get('max') or equity.get('Max')
        low = equity.get('low') or equity.get('Low') or equity.get('min') or equity.get('Min')
        volume = equity.get('volume') or equity.get('Volume') or equity.get('TradeQuantity')

        try:
            change_pct = float(change_pct)
        except (TypeError, ValueError):
            change_pct = 0.0

        symbols.append({
            "symbol": sym,
            "last_price": last_price,
            "change_percentage": change_pct,
            "high": high,
            "low": low,
            "volume": volume,
        })

        # API dokümantasyonundaki 5 sn kuralını tamamen beklemek yerine kısa bir gecikme ekleniyor.
        time.sleep(0.2)

    if not symbols:
        flash(f"Piyasa verileri alınamadı: {api.last_error}", "warning")

    return render_template('market_data.html', symbols=symbols)



@app.route('/analysis')
@login_required
def analysis():
    return render_template('analysis.html')

@app.route('/backtest', defaults={'id': None})
@app.route('/backtest/<int:id>')
@login_required
def backtest(id=None):
    """Render backtest page with available strategies. If an id is given it will be returned to the
    template as selected_strategy_id so the front-end JS can pre-select it (optional)."""
    return render_template('backtest.html', strategies=STRATEGIES, selected_strategy_id=id)

@app.route('/webhook/orders')
@login_required
def webhook_orders_page():
    return render_template('webhook_orders.html', webhook_orders=list(WEBHOOK_ORDERS))

@app.route('/webhook-settings', methods=['GET', 'POST'])
@login_required
def webhook_settings():
    global WEBHOOK_SECRET
    if request.method == 'POST':
        new_secret = request.form.get('webhook_secret')
        if new_secret:
            WEBHOOK_SECRET = new_secret.strip()
            flash('Webhook secret key güncellendi.', 'success')
            return redirect(url_for('webhook_settings'))
    return render_template('webhook_settings.html', current_secret=WEBHOOK_SECRET)

# ----- Webhook Endpoints -----

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    """TradingView'den gelen webhook mesajlarını işler."""
    from datetime import datetime
    global api_instance, WEBHOOK_ORDERS
    data = request.get_json(silent=True)
    if not data:
        return jsonify(success=False, error='JSON body yok'), 400

    # Secret doğrulama (TradingView passphrase kullanır)
    if WEBHOOK_SECRET and data.get('passphrase') != WEBHOOK_SECRET:
        print(f"[DEBUG] Webhook doğrulama hatası: Gelen passphrase='{data.get('passphrase')}', Beklenen='{WEBHOOK_SECRET}'")
        return jsonify(success=False, error='Secret key hatalı'), 403

    symbol = data.get('symbol')
    side_raw = str(data.get('side', '')).upper()
    order_type_raw = str(data.get('type', 'MARKET')).upper()
    quantity = data.get('quantity')
    price = data.get('price')

    # Gelen webhook verilerini detaylı logla
    print(f"[DEBUG] TradingView Webhook Verisi: symbol={symbol}, side={side_raw}, type={order_type_raw}, quantity={quantity}, price={price}")

    if not symbol or not side_raw or not quantity:
        return jsonify(success=False, error='Eksik parametre'), 400

    side = 'Buy' if side_raw == 'BUY' else 'Sell'
    order_type = 'Market' if order_type_raw == 'MARKET' else 'Limit'
    
    # Emir tipi dönüşümünü logla
    print(f"[DEBUG] Dönüştürülen emir tipi: {order_type_raw} -> {order_type}")

    order_status = 'waiting'
    order_id = None
    error_message = None

    try:
        if 'api_instance' in globals() and api_instance:
            # API'ye gönderilecek parametreleri logla
            print(f"[DEBUG] API'ye gönderilecek parametreler: symbol={symbol}, side={side}, quantity={quantity}, price={price}, order_type={order_type}")
            
            res = api_instance.SendOrder(symbol, side, quantity, price, order_type)
            print(f"Webhook API yanıtı: {res}")
            
            # API yanıtını detaylı kontrol et
            if isinstance(res, dict):
                # success=true olsa bile content kısmında hata mesajı olabilir
                if res.get('success') is True:
                    content = res.get('content')
                    # İçerik bir string ve hata mesajı içeriyorsa
                    if isinstance(content, str) and ('Error' in content or 'Limit' in content or 'exceed' in content.lower()):
                        order_status = f'error: {content}'
                        error_message = content
                    else:
                        order_id = res.get('orderId') or res.get('OrderID') or res.get('id')
                        order_status = 'filled'
                else:
                    # API başarısız yanıt döndü
                    error_message = res.get('message', 'API hatası')
                    order_status = f'error: {error_message}'
            else:
                # Başarılı yanıt, dict olmayan format
                order_status = 'filled'
    except Exception as e:
        error_message = str(e)
        order_status = f'error: {error_message}'

    WEBHOOK_ORDERS.appendleft({
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'side': 'AL' if side_raw == 'BUY' else 'SAT',
        'quantity': quantity,
        'price': price or '',
        'status': order_status,
        'order_id': order_id or '',
        'source': 'TradingView',
        'error': error_message
    })

    return jsonify(success=(error_message is None), status=order_status, order_id=order_id, error=error_message)

@app.route('/webhook/orders/data')
@login_required
def webhook_orders_data():
    """AJAX tablo güncellemesi için son webhook emirlerini döner."""
    return jsonify(success=True, orders=list(WEBHOOK_ORDERS))

# --------------- API Yardımcı Endpoints ---------------

@app.route('/api/equity_info')
@login_required
def api_equity_info():
    """Tekil sembol bilgisi döner – front-end'ten sembol ekleme için kullanılır."""
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify(success=False, error="symbol parametresi zorunlu"), 400

    api = AlgolabAPI(username=session.get('username'), api_key=session.get('api_key'))
    api.token = session.get('token')
    api.hash = session.get('hash')

    data = api.GetEquityInfo(symbol.upper())
    if data is None:
        return jsonify(success=False, error=api.last_error or "Veri alınamadı"), 200

    # Ortak alanları normalize et
    result = {
        "symbol": symbol.upper(),
        "last_price": data.get('lst') or data.get('LastPrice') or data.get('Last') or data.get('last_price'),
        "change_percentage": data.get('ChangePercentage') or data.get('changePercent') or data.get('ChangePercent') or 0,
        "high": data.get('High') or data.get('high') or data.get('max') or data.get('Max'),
        "low": data.get('Low') or data.get('low') or data.get('min') or data.get('Min'),
        "volume": data.get('Volume') or data.get('volume') or data.get('TradeQuantity')
    }
    return jsonify(success=True, data=result)

@app.route('/api/candle_data')
@login_required
def api_candle_data():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval', '1m')  # 1m,5m,15m,1h,1d

    if not symbol:
        return jsonify(success=False, error="symbol parametresi zorunlu"), 400

    # Algolab periyot dakika cinsinden: map edelim
    interval_map = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '1d': 1440
    }
    period_minutes = interval_map.get(interval, 1)

    api = AlgolabAPI(username=session.get('username'), api_key=session.get('api_key'))
    api.token = session.get('token')
    api.hash = session.get('hash')

    candles = api.GetCandleData(symbol.upper(), str(period_minutes))
    if candles is None:
        return jsonify(success=False, error=api.last_error or "Veri alınamadı"), 200

    # candles içeriği list ise doğrudan kullanalım
    ohlc = candles if isinstance(candles, list) else candles.get('content')
    if not ohlc:
        return jsonify(success=False, error="Boş veri"), 200

    # Plotly grafiği üret
    from plotly import graph_objs as go

    dates = [item.get('date') or item.get('Date') for item in ohlc]
    opens = [float(item.get('open') or item.get('Open') or item.get('o') or 0) for item in ohlc]
    highs = [float(item.get('high') or item.get('High') or item.get('h') or 0) for item in ohlc]
    lows = [float(item.get('low') or item.get('Low') or item.get('l') or 0) for item in ohlc]
    closes = [float(item.get('close') or item.get('Close') or item.get('c') or 0) for item in ohlc]

    fig = go.Figure(data=[go.Candlestick(x=dates, open=opens, high=highs, low=lows, close=closes)])
    fig.update_layout(title=f"{symbol.upper()} – {interval} Grafik", xaxis_title="Tarih", yaxis_title="Fiyat")

    return jsonify(success=True, chart=fig.to_json())

# Yeni eklenen sayfalar
@app.route('/daily-transactions')
@login_required
def daily_transactions():
    # Şimdilik boş liste döndür
    return render_template('daily_transactions.html', transactions=[])

@app.route('/my-strategies')
@login_required
def my_strategies():
    return render_template('my_strategies.html', strategies=STRATEGIES)

# Eski underscore URL'si için yönlendirme (geriye dönük uyumluluk)
@app.route('/my_strategies')
@login_required
def my_strategies_alias():
    return redirect(url_for('my_strategies'))

@app.route('/strategy-add', methods=['GET', 'POST'])
@login_required
def strategy_add():
    return render_template('strategy_add.html')

# ---------- Strategy API ----------
@app.route('/api/save_strategy', methods=['POST'])
@login_required
def api_save_strategy():
    """Stores strategy JSON sent from front-end."""
    global STRATEGIES, NEXT_STRATEGY_ID
    data = request.get_json(silent=True)
    if not data:
        return jsonify(success=False, message='JSON body yok'), 400

    # Basit doğrulama – ismi zorunlu
    if not data.get('strategyName'):
        return jsonify(success=False, message='Strateji adı zorunlu'), 400

    strategy_entry = {
        'id': NEXT_STRATEGY_ID,
        'name': data.get('strategyName'),
        'type': data.get('strategyType'),
        'symbol': data.get('stockSymbol') or data.get('symbol', '-'),
        'timeframe': data.get('timeframe', '-'),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'performance': 0,
        'settings': data  # full raw data
    }
    STRATEGIES.append(strategy_entry)
    NEXT_STRATEGY_ID += 1

    return jsonify(success=True, strategy_id=strategy_entry['id'])

@app.route('/api/get_quote', methods=['POST'])
@login_required
def get_quote():
    api_key_full = session.get('api_key_full')
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token')
    
    if not api_key_full or not access_token:
        return jsonify(error="Oturum süreniz doldu"), 401
    
    symbol = request.json.get('symbol')
    if not symbol:
        return jsonify(error="Sembol belirtilmedi"), 400
    
    try:
        # API nesnesini başlat
        api = AlgolabAPI(api_key_full=api_key_full)
        api.access_token = access_token
        api.refresh_token = refresh_token
        
        # Alıntıyı çek - çalışan örnekte get_quote kullanılıyor
        quote_data = api.get_quote(symbol)
        
        if quote_data:
            # Geriye dönen veri yapısını algolab_api.py uyumlu hale getir
            formatted_quote = {
                'Symbol': quote_data.get('symbol', ''),
                'LastPrice': quote_data.get('lastPrice', 0),
                'HighPrice': quote_data.get('highPrice', 0),
                'LowPrice': quote_data.get('lowPrice', 0),
                'OpenPrice': quote_data.get('openPrice', 0),
                'ClosePrice': quote_data.get('previousClose', 0),
                'Volume': quote_data.get('volume', 0),
                'Time': quote_data.get('timestamp', '')
            }
            return jsonify(formatted_quote)
        else:
            return jsonify(error="Alıntı alınamadı"), 500
    
    except Exception as e:
        return jsonify(error=f"Hata: {str(e)}"), 500

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'info')
    return redirect(url_for('login'))

@app.route('/favicon.ico')
def favicon():
    return '', 204

# ---------- Trading / Order Management ----------
@app.route('/trading')
@login_required
def trading():
    """Manual trading page showing open orders.

    Her sayfa yenilemesinde Algolab API'den bekleyen emirler çağrılır ve
    küresel OPEN_ORDERS listesi tazelenir. API başarısız olursa eski liste
    korunur ve ekranda hata yerine mevcut veriler gösterilir.
    """
    global api_instance, OPEN_ORDERS

    try:
        if api_instance:
            latest_orders = api_instance.GetOpenOrders() or []
            if latest_orders:
                OPEN_ORDERS = latest_orders
                print(f"[DEBUG] trading() – OPEN_ORDERS API'den güncellendi, yeni uzunluk: {len(OPEN_ORDERS)}")
            else:
                print(f"[WARN] trading() – GetOpenOrders boş döndü veya hata: {api_instance.last_error}")
    except Exception as e:
        print(f"[ERROR] trading() – GetOpenOrders istisnası: {e}")

    rendered = render_template('trading.html', orders=OPEN_ORDERS)
    return rendered

@app.route('/send_order', methods=['POST'])
@login_required
def send_order():
    data = request.get_json(force=True, silent=True) or {}
    symbol = data.get('symbol', '').upper()
    direction = data.get('direction')
    pricetype = data.get('priceType') or data.get('pricetype')
    price = data.get('price')
    quantity = data.get('quantity') or data.get('lot')
    if not all([symbol, direction, pricetype, quantity]):
        return jsonify(success=False, error='Eksik parametre'), 400

    order_type = 'Market' if pricetype == 'piyasa' else 'Limit'
    try:
        quantity_int = int(quantity)
    except ValueError:
        return jsonify(success=False, error='Lot sayısı geçersiz'), 400

    try:
        price_val = float(price) if price not in (None, '', '0', 0) else None
    except ValueError:
        return jsonify(success=False, error='Fiyat geçersiz'), 400

    try:
        api_response = api_instance.SendOrder(symbol, direction.capitalize(), quantity_int, price_val, order_type)
        if not api_response or not api_response.get('success'):
            return jsonify(success=False, error=api_response.get('message', 'Bilinmeyen hata')), 500

        ref_no = api_response.get('content') or 'REF-N/A'
        # İçerik "Referans Numaranız: XYZ;...." formatında ise sadece ilk kısmı al
        if isinstance(ref_no, str) and ':' in ref_no:
            ref_no = ref_no.split(':', 1)[1].split(';')[0].strip()

        order_entry = {
            'atpref': ref_no,               # Referans numarası
            'ticker': symbol,              # Sembol
            'buysell': direction.upper(),  # BUY / SELL
            'pricetype': pricetype,        # market / limit
            'waitingprice': price_val or '-',
            'ordersize': quantity_int,
            'remainingsize': quantity_int, # Başlangıçta tamamı bekliyor
            'description': 'ACTIVE'        # Durum
        }
        global OPEN_ORDERS
        OPEN_ORDERS.append(order_entry)
        print(f"[DEBUG] OPEN_ORDERS appended — toplam {len(OPEN_ORDERS)} kayıt: {OPEN_ORDERS[-1]}")
        return jsonify(success=True, content=ref_no)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/cancel_order', methods=['POST'])
@login_required
def cancel_order():
    """Manual order cancellation endpoint.

    Expects JSON body: {"id": "<order_ref>"}
    Calls Algolab DeleteOrder API and, on success, removes the order from the in-memory list.
    """
    global api_instance, OPEN_ORDERS
    data = request.get_json(force=True, silent=True) or {}
    order_id = data.get('id')
    if not order_id:
        return jsonify(success=False, error='Order ID required'), 400

    try:
        # Algolab API çağrısı
        api_resp = api_instance.DeleteOrder(order_id)
        if not api_resp or api_resp.get('success') is not True:
            return jsonify(success=False, error=api_resp.get('message', 'İptal başarısız')), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

    # Yerel listeden kaldır
    index = next((i for i, o in enumerate(OPEN_ORDERS)
                      if o.get('id') == order_id or o.get('atpref') == order_id), None)
    if index is not None:
        OPEN_ORDERS.pop(index)

    return jsonify(success=True, message='Emir iptal edildi')

# ---------- Strategy Delete API ----------
@app.route('/api/delete_strategy/<int:strategy_id>', methods=['DELETE'])
@login_required
def api_delete_strategy(strategy_id):
    """Remove a strategy by id from the in-memory list."""
    global STRATEGIES
    index = next((i for i, s in enumerate(STRATEGIES) if s['id'] == strategy_id), None)
    if index is None:
        return jsonify(success=False, message='Strateji bulunamadı'), 404
    STRATEGIES.pop(index)
    return jsonify(success=True)

# ---------- Strategy Detail (placeholder) ----------
@app.route('/strategy/<int:id>')
@login_required
def strategy_detail(id):
    strategy = next((s for s in STRATEGIES if s['id'] == id), None)
    if not strategy:
        flash('Strateji bulunamadı', 'danger')
        return redirect(url_for('my_strategies'))
    # Basit JSON çıktısı – ileride HTML şablonu ile değiştirilebilir
    return jsonify(strategy)

# ---------- Strategy Edit (placeholder) ----------
@app.route('/strategy-edit/<int:id>', methods=['GET', 'POST'])
@login_required
def strategy_edit(id):
    strategy = next((s for s in STRATEGIES if s['id'] == id), None)
    if not strategy:
        flash('Strateji bulunamadı', 'danger')
        return redirect(url_for('my_strategies'))
    if request.method == 'POST':
        # Temel alan güncellemesi – ayrıntılı validasyon eklenebilir
        strategy['name'] = request.form.get('strategyName', strategy['name'])
        strategy['symbol'] = request.form.get('symbol', strategy['symbol'])
        flash('Strateji güncellendi', 'success')
        return redirect(url_for('my_strategies'))
    return jsonify(strategy)

if __name__ == '__main__':
    print("Algolab Web uygulaması başlatılıyor...")
    print(f"API URL: https://www.algolab.com.tr")
    print("API Key artık kullanıcıya özel olarak dinamik üretiliyor.")
    print("Tarayıcıda 'http://localhost:8086' adresini ziyaret edin")
    app.run(debug=True, port=8091, host='0.0.0.0')
