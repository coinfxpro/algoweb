from rq import Worker, Queue
from redis import Redis
import redis

# Redis bağlantısı
redis_conn = redis.Redis()

# Worker fonksiyonu
def process_order(order_data):
    print(f"Processing order: {order_data}")
    # Burada emir işleme kodları yer alacak

# Worker'ı başlatma
if __name__ == '__main__':
    # Yeni rq sürümünde Connection yerine doğrudan Redis bağlantısı kullanılıyor
    worker = Worker([Queue('orders', connection=redis_conn)], connection=redis_conn)
    worker.work()
