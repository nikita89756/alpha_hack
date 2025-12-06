import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model_id = "openai/whisper-small"

def load_model():
    logging.info(f"Загрузка модели {model_id} на устройство {device}")
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    return {
        "model": model,
        "processor": processor,
        "device": device,
        "torch_dtype": torch_dtype
    }

global_model = None
if __name__ == "__main__":
    global_model = load_model()
    logging.info("Модель успешно загружена и инициализирована")