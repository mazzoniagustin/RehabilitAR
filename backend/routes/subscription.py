from services import subscription_service
from fastapi import APIRouter, HTTPException, Depends
from utils.permissions import get_current_user

router = APIRouter()

@router.post("/subscriptions")
def create_subscription(current_user=Depends(get_current_user)):
    return subscription_service.dar_alta_suscripcion(current_user['id'])