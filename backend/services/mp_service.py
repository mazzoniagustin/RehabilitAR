import os
import mercadopago
from dotenv import load_dotenv

load_dotenv()

TEST_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN_TEST")

sdk = mercadopago.SDK(TEST_TOKEN)   