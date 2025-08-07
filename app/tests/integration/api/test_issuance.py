import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_issuance_endpoint(async_client: AsyncClient, admin_token: str, shareholder_user):
    """Test de création d'une émission d'actions."""
    user, profile = shareholder_user
    
    # Créer d'abord une classe d'actions si nécessaire
    # (Vous devrez peut-être adapter ceci selon votre API)
    share_class_payload = {
        "id": "preferred_a",
        "name": "Preferred Series A",
        "type": "preferred"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Optionnel : créer la classe d'actions si elle n'existe pas
    # await async_client.post("/api/share-classes/", json=share_class_payload, headers=headers)
    
    # Créer l'émission
    issuance_payload = {
        "shareholder_id": str(profile.id),
        "share_class_id": "preferred_a",
        "quantity": 100,
        "price_per_share": 500,
        "currency": "XAF"
    }
    
    response = await async_client.post(
        "/api/issuances/", 
        json=issuance_payload, 
        headers=headers
    )
    
    # Vérifications
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "issuance_id" in data, f"Missing 'issuance_id' in response: {data}"
    assert data["message"].lower().startswith("share issuance created"), f"Unexpected message: {data.get('message')}"
    
    # Vérifications supplémentaires optionnelles
    if "issuance" in data:
        issuance = data["issuance"]
        assert issuance["shareholder_id"] == str(profile.id)
        assert issuance["share_class_id"] == "preferred_a"
        assert issuance["quantity"] == 100
        assert issuance["price_per_share"] == 500
        assert issuance["currency"] == "XAF"

@pytest.mark.asyncio
async def test_create_issuance_unauthorized(async_client: AsyncClient):
    """Test de création d'émission sans authentification."""
    payload = {
        "shareholder_id": str(uuid4()),
        "share_class_id": "preferred_a",
        "quantity": 100,
        "price_per_share": 500,
        "currency": "XAF"
    }
    
    # Pas de header Authorization
    response = await async_client.post("/api/issuances/", json=payload)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


@pytest.mark.asyncio
async def test_create_issuance_invalid_data(async_client: AsyncClient, admin_token: str):
    """Test de création d'émission avec des données invalides."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test avec quantité négative
    invalid_payload = {
        "shareholder_id": str(uuid4()),
        "share_class_id": "preferred_a",
        "quantity": -100,  # Quantité négative
        "price_per_share": 500,
        "currency": "XAF"
    }
    
    response = await async_client.post("/api/issuances/", json=invalid_payload, headers=headers)
    assert response.status_code == 422, f"Expected 422 for negative quantity, got {response.status_code}"
    
    # Test avec données manquantes
    incomplete_payload = {
        "shareholder_id": str(uuid4()),
        # share_class_id manquant
        "quantity": 100,
        "price_per_share": 500
    }
    
    response = await async_client.post("/api/issuances/", json=incomplete_payload, headers=headers)
    assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"