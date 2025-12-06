from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from transformers import pipeline
from download_and_initialize_model import load_model, global_model
import io
import soundfile as sf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if global_model is None:
    global_model = load_model()

model = global_model["model"]
processor = global_model["processor"]
device = global_model["device"]
torch_dtype = global_model["torch_dtype"]

pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
)

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        audio_data, sample_rate = sf.read(io.BytesIO(contents), dtype='float32')

        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        if sample_rate != 16000:
            from scipy.signal import resample
            number_of_samples = round(len(audio_data) * 16000 / sample_rate)
            audio_data = resample(audio_data, number_of_samples)

        chunk_size = 16000 * 30
        chunks = [
            audio_data[i:i + chunk_size]
            for i in range(0, len(audio_data), chunk_size)
        ]

        full_text_parts = []

        for i, chunk in enumerate(chunks):
            logging.info(f"Обработка чанка {i + 1} из {len(chunks)}")
            result = pipe(
                chunk,
                generate_kwargs={
                    "language": "ru",
                    "task": "transcribe",
                    "return_timestamps": False,
                }
            )["text"].strip()

            if result:
                full_text_parts.append(result)

        full_text = " ".join(full_text_parts).strip()

        return {
            "filename": file.filename,
            "text": full_text,
            "duration_sec": len(audio_data) / 16000,
            "chunks_processed": len(chunks)
        }

    except Exception as e:
        logging.error(f"Ошибка транскрипции: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка транскрипции: {str(e)}")


@app.get("/health")
def health():
    return {
        "status": "OK",
        "model_loaded": global_model is not None,
        "device": device
    }

active_transcriptions = []

@app.get("/api/summaries")
async def get_summaries():
    return {"summaries": [t['text'] for t in active_transcriptions] if active_transcriptions else []}


@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Этот эндпоинт не поддерживает цельную транскрипцию. Используйте POST /transcribe.")
    await websocket.close()


if __name__ == "main":
    import uvicorn
    logging.info("Запуск сервера на 0.0.0.0:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8010, reload=False)