import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from bson import ObjectId

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_business_collection():
    """Мок для MongoDB коллекции businesses"""
    collection = Mock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find = Mock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    return collection


@pytest.fixture
def sample_business():
    """Создает тестовый бизнес"""
    return {
        "_id": ObjectId(),
        "user_id": "test_user_id",
        "name": "Test Business",
        "description": "Test Description",
        "industry": "IT"
    }


class TestCreateBusiness:
    """Тесты для создания бизнеса"""
    
    @pytest.mark.asyncio
    async def test_create_business_success(self, client, mock_business_collection, sample_business):
        """Тест успешного создания бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            inserted_id = ObjectId()
            mock_business_collection.insert_one = AsyncMock(
                return_value=Mock(inserted_id=inserted_id)
            )
            mock_business_collection.find_one = AsyncMock(return_value=sample_business)
            
            response = client.post(
                "/businesses/",
                json={
                    "name": "Test Business",
                    "description": "Test Description",
                    "industry": "IT"
                },
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Business"
            assert data["user_id"] == "test_user_id"
    
    def test_create_business_missing_header(self, client):
        """Тест создания бизнеса без заголовка X-User-Id"""
        response = client.post(
            "/businesses/",
            json={
                "name": "Test Business",
                "description": "Test Description"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestListBusinesses:
    """Тесты для получения списка бизнесов"""
    
    @pytest.mark.asyncio
    async def test_list_businesses_success(self, client, mock_business_collection, sample_business):
        """Тест успешного получения списка бизнесов"""
        with patch('main.business_collection', mock_business_collection):
            mock_cursor = Mock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_business])
            mock_business_collection.find = Mock(return_value=mock_cursor)
            
            response = client.get(
                "/businesses/",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_list_businesses_missing_header(self, client):
        """Тест получения списка без заголовка"""
        response = client.get("/businesses/")
        
        assert response.status_code == 422


class TestGetBusiness:
    """Тесты для получения бизнеса"""
    
    @pytest.mark.asyncio
    async def test_get_business_success(self, client, mock_business_collection, sample_business):
        """Тест успешного получения бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.find_one = AsyncMock(return_value=sample_business)
            
            business_id = str(sample_business["_id"])
            response = client.get(
                f"/businesses/{business_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Business"
    
    @pytest.mark.asyncio
    async def test_get_business_not_found(self, client, mock_business_collection):
        """Тест получения несуществующего бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.find_one = AsyncMock(return_value=None)
            
            business_id = str(ObjectId())
            response = client.get(
                f"/businesses/{business_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_business_access_denied(self, client, mock_business_collection, sample_business):
        """Тест получения чужого бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.find_one = AsyncMock(return_value=sample_business)
            
            business_id = str(sample_business["_id"])
            response = client.get(
                f"/businesses/{business_id}",
                headers={"X-User-Id": "other_user_id"}
            )
            
            assert response.status_code == 403


class TestUpdateBusiness:
    """Тесты для обновления бизнеса"""
    
    @pytest.mark.asyncio
    async def test_update_business_success(self, client, mock_business_collection, sample_business):
        """Тест успешного обновления бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            updated_business = sample_business.copy()
            updated_business["name"] = "Updated Business"
            
            mock_business_collection.find_one = AsyncMock(return_value=sample_business)
            mock_business_collection.update_one = AsyncMock()
            mock_business_collection.find_one = AsyncMock(return_value=updated_business)
            
            business_id = str(sample_business["_id"])
            response = client.patch(
                f"/businesses/{business_id}",
                json={"name": "Updated Business"},
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Business"
    
    @pytest.mark.asyncio
    async def test_update_business_access_denied(self, client, mock_business_collection, sample_business):
        """Тест обновления чужого бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.find_one = AsyncMock(return_value=sample_business)
            
            business_id = str(sample_business["_id"])
            response = client.patch(
                f"/businesses/{business_id}",
                json={"name": "Updated Business"},
                headers={"X-User-Id": "other_user_id"}
            )
            
            assert response.status_code == 403


class TestDeleteBusiness:
    """Тесты для удаления бизнеса"""
    
    @pytest.mark.asyncio
    async def test_delete_business_success(self, client, mock_business_collection):
        """Тест успешного удаления бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.delete_one = AsyncMock(
                return_value=Mock(deleted_count=1)
            )
            
            business_id = str(ObjectId())
            response = client.delete(
                f"/businesses/{business_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_delete_business_not_found(self, client, mock_business_collection):
        """Тест удаления несуществующего бизнеса"""
        with patch('main.business_collection', mock_business_collection):
            mock_business_collection.delete_one = AsyncMock(
                return_value=Mock(deleted_count=0)
            )
            
            business_id = str(ObjectId())
            response = client.delete(
                f"/businesses/{business_id}",
                headers={"X-User-Id": "test_user_id"}
            )
            
            assert response.status_code == 404

