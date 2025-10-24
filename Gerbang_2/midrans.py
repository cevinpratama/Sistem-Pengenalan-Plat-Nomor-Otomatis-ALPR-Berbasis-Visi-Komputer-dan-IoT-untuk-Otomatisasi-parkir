import midtransclient
import time
import sys 

core_api = midtransclient.CoreApi(
    is_production=False,
    server_key='SB-Mid-server-OzanXf7sA6GWJOZUJGt__cOY' 
)

order_id = "ORDER-QRIS-123456" 
gross_amount = 75500

INTERVAL_DETIK = 5
MAX_CEK = 20 

print(f"Memulai pengecekan status untuk Order ID: {order_id}...")
print(f"Interval: {INTERVAL_DETIK} detik. Maksimal pengecekan: {MAX_CEK} kali.")
print("-" * 50)

for i in range(1, MAX_CEK + 1):
    try:
        status_response = core_api.transaction.status(order_id)
        
        current_status = status_response['transaction_status']
        
        print(f"[{i}/{MAX_CEK}] Status saat ini: {current_status}...")
        
        if current_status == 'settlement' or current_status == 'capture':
            print("\n✅ PEMBAYARAN BERHASIL!")
            print(f"Order ID: {status_response['order_id']}")
            print(f"Jumlah: {status_response['gross_amount']}")
            print(f"Waktu Pembayaran: {status_response.get('settlement_time', 'N/A')}")
            sys.exit(0) 
            
        elif current_status == 'expire' or current_status == 'cancel':
            print("\n❌ TRANSAKSI GAGAL ATAU KEDALUWARSA.")
            sys.exit(0) 

        elif current_status == 'pending':
            pass
            
        else:
            print(f"\n⚠️ STATUS TIDAK DIKENAL ATAU GAGAL: {current_status}")
            sys.exit(0)
            
    except midtransclient.http.exceptions.NotFound:
        print(f"\n❌ ERROR: Transaksi dengan Order ID {order_id} tidak ditemukan.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR API Midtrans: {e}")
        
    
    time.sleep(INTERVAL_DETIK)

print("-" * 50)
print(f"🛑 Polling selesai setelah {MAX_CEK} kali pengecekan.")
print(f"Status terakhir untuk Order ID {order_id} masih PENDING atau terjadi masalah.")