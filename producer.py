import redis
from rq import Queue

# Redis bağlantısı
redis_conn = redis.Redis()

# Kuyruk oluşturma
queue = Queue('orders', connection=redis_conn)

def place_order(order_data):
    # Emiri kuyruklayın
    queue.enqueue('worker.process_order', order_data)

# Örnek emir
order_data = {
    "secret": "secret_key",
    "symbol": "ISCTR",
    "side": "BUY",
    "type": "LIMIT",
    "price": "14.00",
    "quantity": "1"
}

place_order(order_data)
