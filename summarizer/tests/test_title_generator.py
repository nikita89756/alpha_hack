import pytest
from unittest.mock import Mock, patch, AsyncMock
from title_generator import LLMClient, TitleGenerator, generate_chat_title, init_generator


@pytest.fixture
def mock_openai_client():
    """Мок для OpenAI клиента"""
    with patch('title_generator.OpenAI') as mock:
        client_instance = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message = Mock()
        mock_completion.choices[0].message.content = "Тестовое название"
        
        client_instance.chat.completions.create = Mock(return_value=mock_completion)
        mock.return_value = client_instance
        yield client_instance


class TestLLMClient:
    """Тесты для LLMClient"""
    
    def test_init(self, mock_openai_client):
        """Тест инициализации LLMClient"""
        client = LLMClient(api_key="test_key")
        assert client.model == "qwen/qwen-2.5-72b-instruct"
    
    def test_get_completion(self, mock_openai_client):
        """Тест получения ответа от LLM"""
        client = LLMClient(api_key="test_key")
        client.client = mock_openai_client
        
        messages = [{"role": "user", "content": "Test"}]
        result = client.get_completion(messages)
        
        assert result == "Тестовое название"
        mock_openai_client.chat.completions.create.assert_called_once()
    
    def test_get_completion_error(self, mock_openai_client):
        """Тест обработки ошибки LLM"""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        client = LLMClient(api_key="test_key")
        client.client = mock_openai_client
        
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(Exception) as exc_info:
            client.get_completion(messages)
        
        assert "Ошибка при обращении к LLM" in str(exc_info.value)


class TestTitleGenerator:
    """Тесты для TitleGenerator"""
    
    def test_generate_title_success(self, mock_openai_client):
        """Тест успешной генерации названия"""
        llm_client = LLMClient(api_key="test_key")
        llm_client.client = mock_openai_client
        
        generator = TitleGenerator(llm_client=llm_client)
        result = generator.generate_title("Первое сообщение пользователя")
        
        assert result == "Тестовое название"
    
    def test_generate_title_too_long(self, mock_openai_client):
        """Тест генерации слишком длинного названия"""
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message = Mock()
        mock_completion.choices[0].message.content = "Очень длинное название которое превышает лимит в 50 символов"
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        llm_client = LLMClient(api_key="test_key")
        llm_client.client = mock_openai_client
        
        generator = TitleGenerator(llm_client=llm_client)
        result = generator.generate_title("Test message")
        
        assert len(result) <= 50
        assert result.endswith("...")
    
    def test_generate_title_too_short(self, mock_openai_client):
        """Тест генерации слишком короткого названия"""
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message = Mock()
        mock_completion.choices[0].message.content = "А"
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        llm_client = LLMClient(api_key="test_key")
        llm_client.client = mock_openai_client
        
        generator = TitleGenerator(llm_client=llm_client)
        result = generator.generate_title("Test message")
        
        assert result == "Новое обращение"
    
    def test_generate_title_error(self, mock_openai_client):
        """Тест обработки ошибки при генерации"""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        llm_client = LLMClient(api_key="test_key")
        llm_client.client = mock_openai_client
        
        generator = TitleGenerator(llm_client=llm_client)
        result = generator.generate_title("Test message")
        
        assert result == "Новое обращение"


class TestGenerateChatTitle:
    """Тесты для функции generate_chat_title"""
    
    @pytest.mark.asyncio
    async def test_generate_chat_title_success(self, mock_openai_client):
        """Тест успешной генерации названия чата"""
        with patch('title_generator._title_generator') as mock_generator:
            mock_generator.generate_title = Mock(return_value="Тестовое название")
            
            result = await generate_chat_title("Первое сообщение")
            
            assert result == "Тестовое название"
    
    @pytest.mark.asyncio
    async def test_generate_chat_title_init_error(self, mock_openai_client):
        """Тест генерации при ошибке инициализации"""
        with patch('title_generator._title_generator', None), \
             patch('title_generator.init_generator', return_value=False):
            
            result = await generate_chat_title("Первое сообщение")
            
            assert result == "Новое обращение"
    
    @pytest.mark.asyncio
    async def test_generate_chat_title_generation_error(self, mock_openai_client):
        """Тест обработки ошибки генерации"""
        with patch('title_generator._title_generator') as mock_generator:
            mock_generator.generate_title = Mock(side_effect=Exception("Generation error"))
            
            result = await generate_chat_title("Первое сообщение")
            
            assert result == "Новое обращение"


class TestInitGenerator:
    """Тесты для инициализации генератора"""
    
    def test_init_generator_success(self, mock_openai_client):
        """Тест успешной инициализации"""
        with patch('title_generator.api_key', "test_key"):
            result = init_generator()
            assert result is True
    
    def test_init_generator_no_api_key(self):
        """Тест инициализации без API ключа"""
        with patch('title_generator.api_key', ""):
            result = init_generator()
            assert result is False

