# test_minimal_purchase.py
from services.minimal_purchase import handle_purchase_minimal

KEY = "TEST-123"

print("Testing minimal purchase handler...")
print(f"First call: {handle_purchase_minimal(1, 'founder_black', KEY)}")
print(f"Second call: {handle_purchase_minimal(1, 'founder_black', KEY)}")

print("\nTesting with different key...")
KEY2 = "TEST-456"
print(f"Different key: {handle_purchase_minimal(1, 'founder_black', KEY2)}")

print("\nVerifying purchase records...")
from models.purchase import Purchase

# Check first purchase
purchase1 = Purchase.find_by_key(KEY)
if purchase1:
    print(f"Purchase 1: {purchase1.to_dict()}")
else:
    print("Purchase 1 not found")

# Check second purchase (should be None)
purchase2 = Purchase.find_by_key(KEY)
if purchase2:
    print(f"Purchase 2: {purchase2.to_dict()}")
else:
    print("Purchase 2 correctly returned None (duplicate)")

# Check different key purchase
purchase3 = Purchase.find_by_key(KEY2)
if purchase3:
    print(f"Purchase 3: {purchase3.to_dict()}")
else:
    print("Purchase 3 not found")

print(f"\nTotal purchases in storage: {len(Purchase._storage)}")
print("Test complete!")
