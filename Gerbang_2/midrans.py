import midtransclient


core_api = midtransclient.CoreApi(
    is_production=False,
    server_key='SB-Mid-server-OzanXf7sA6GWJOZUJGt__cOY' 
)

order_id = "ORDER-QRIS-123456" 
gross_amount = 75500 

transaction_details = {
    "order_id": order_id,
    "gross_amount": gross_amount
}

charge_payload = {
    "payment_type": "qris",
    "transaction_details": transaction_details,
}

try:
    charge_response = core_api.charge(charge_payload)
    
   
    qr_action = next((action for action in charge_response['actions'] if action['name'] == 'generate-qr-code'), None)
    
    if qr_action:
        qr_code_url = qr_action['url']
        print(f"Transaksi QRIS berhasil dibuat. Status: {charge_response['transaction_status']}")
        print(f"URL Gambar QRIS: {qr_code_url}")
        print(f"Order ID: {charge_response['order_id']}")
    else:
        print("QRIS Action tidak ditemukan dalam respons.")
        
except Exception as e:
    print(f"Gagal membuat transaksi Midtrans: {e}")

