from pywebpush import webpush, generate_vapid_keys

# Gere as chaves VAPID
vapid_keys = generate_vapid_keys()
print(vapid_keys)  # Armazene isso em um lugar seguro
