import midtransclient
import time
import sys 
import os

from midtransclient.error_midtrans import MidtransAPIError

SERVER_KEY = os.environ.get('MIDTRANS_SERVER_KEY', None) 

if SERVER_KEY is None:
    print("❌ ERROR: Variabel lingkungan MIDTRANS_SERVER_KEY tidak ditemukan.")
    print("SILAKAN ATUR DULU: export MIDTRANS_SERVER_KEY=\"SB-Mid-server-...\"")
    sys.exit(1)


core_api = midtransclient.CoreApi(
    is_production=False,
    server_key=SERVER_KEY 
)

order_id = f"QRIS-APP-{int(time.time())}" 
gross_amount = 1000

try:
    transaction_details = {
        "order_id": order_id,
        "gross_amount": gross_amount
    }
    charge_payload = {
        "payment_type": "qris",
        "transaction_details": transaction_details,
    }
    
    print(f"Mengirim permintaan CHARGE untuk Order ID: {order_id}...")
    charge_response = core_api.charge(charge_payload)
    
    qr_action = next((a for a in charge_response.get('actions', []) if a['name'] == 'generate-qr-code'), None)
    
    if qr_action:
        qr_code_url = qr_action['url']
        print("\n=== INFORMASI TRANSAKSI BARU ===")
        print(f"Status Charge: {charge_response['transaction_status']}")
        print(f"Order ID: {charge_response['order_id']}") 
        print(f"URL Gambar QRIS: {qr_code_url}")
        print("MOHON LAKUKAN PEMBAYARAN SEKARANG untuk menguji polling.")
        print("=" * 50)
    else:
        print("Gagal mendapatkan URL QRIS.")
        sys.exit(1)

except MidtransAPIError as e:
    print(f"\n❌ ERROR CHARGE API Midtrans: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR Umum saat Charge: {e}")
    sys.exit(1)

INTERVAL_DETIK = 5
MAX_CEK = 20 

print(f"\nMemulai pengecekan status untuk Order ID: {order_id}...")
print(f"Interval: {INTERVAL_DETIK} detik. Maksimal pengecekan: {MAX_CEK} kali.")
print("-" * 50)

for i in range(1, MAX_CEK + 1):
    try:
        status_response = core_api.transactions.status(order_id)
        
        current_status = status_response['transaction_status']
        
        print(f"[{i}/{MAX_CEK}] Status saat ini: {current_status}...")
        
        if current_status in ('settlement', 'capture'):
            print("\n✅ PEMBAYARAN BERHASIL! Transaksi SUDAH LUNAS.")
            print(f"Order ID: {status_response['order_id']}")
            print(f"Waktu Pembayaran: {status_response.get('settlement_time', 'N/A')}")
            sys.exit(0) 
            
        elif current_status in ('expire', 'cancel', 'deny'):
            print("\n❌ TRANSAKSI GAGAL ATAU KEDALUWARSA.")
            sys.exit(0) 

        elif current_status == 'pending':
            pass
            
    except MidtransAPIError as e:
        if "Transaction doesn't exist" in str(e):
            print(f"\n❌ ERROR: Transaksi dengan Order ID {order_id} tidak ditemukan.")
        else:
             print(f"\n❌ ERROR API Midtrans (Polling): {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR Umum saat Polling: {e}")
        sys.exit(1)
        
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
print(f"Status terakhir untuk Order ID {order_id} masih PENDING.")
print(f"Status terakhir untuk Order ID {order_id} masih PENDING atau terjadi masalah.")
