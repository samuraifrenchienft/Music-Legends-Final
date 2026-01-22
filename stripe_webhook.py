# stripe_webhook.py
from flask import Flask, request, jsonify
import stripe
import os
from dotenv import load_dotenv
from database import DatabaseManager
from stripe_payments import stripe_manager

load_dotenv('.env.txt')

app = Flask(__name__)
db = DatabaseManager()

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('stripe-signature')
    
    # Verify webhook signature
    if not stripe_manager.verify_webhook_signature(payload, sig_header):
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Process the event
    event_result = stripe_manager.process_webhook_event(payload)
    
    if event_result['type'] == 'pack_publish_completed':
        # Mark pack as published and LIVE
        pack_id = event_result['pack_id']
        payment_intent_id = event_result['payment_intent_id']
        
        success = db.publish_pack(pack_id, payment_intent_id)
        if success:
            print(f"✅ Pack {pack_id} published successfully")
            return jsonify({'status': 'pack_published'})
        else:
            print(f"❌ Failed to publish pack {pack_id}")
            return jsonify({'error': 'Publish failed'}), 500
    
    elif event_result['type'] == 'pack_purchase_completed':
        # Process pack purchase
        pack_id = event_result['pack_id']
        buyer_id = event_result['buyer_id']
        payment_intent_id = event_result['payment_intent_id']
        amount_cents = event_result['amount_cents']
        
        # Get pack details
        live_packs = db.get_live_packs(limit=100)
        pack = next((p for p in live_packs if p['pack_id'] == pack_id), None)
        
        if pack:
            # Process purchase and generate cards
            purchase_id = db.purchase_pack(pack_id, buyer_id, payment_intent_id, amount_cents)
            if purchase_id:
                print(f"✅ Pack purchase {purchase_id} completed for user {buyer_id}")
                return jsonify({'status': 'purchase_completed', 'purchase_id': purchase_id})
        
        print(f"❌ Failed to process pack purchase for {pack_id}")
        return jsonify({'error': 'Purchase failed'}), 500
    
    elif event_result['type'] == 'error':
        print(f"❌ Webhook processing error: {event_result['error']}")
        return jsonify({'error': 'Processing error'}), 500
    
    return jsonify({'status': 'received'})

if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
