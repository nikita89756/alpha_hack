"""Utilities for loading locally cached or remote BERT checkpoints."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

from typing import Tuple

logger = logging.getLogger(__name__)


def _has_local_checkpoint(directory: str) -> bool:
    """Check whether the directory contains any supported model files."""
    path = Path(directory)
    if not path.exists() or not path.is_dir():
        return False
    return any(
        (path / filename).exists()
        for filename in ("pytorch_model.bin", "tf_model.h5", "model.safetensors")
    )


def load_deeppavlov_bert(
    model_name: str = "DeepPavlov/rubert-base-cased",
    local_dir: str = "ai_assistant/agent_system/model",
    device: str | None = None,
) -> Tuple[AutoModel, AutoTokenizer]:
    """Load the DeepPavlov BERT retriever either from disk or Hugging Face.

    Args:
        model_name: Hugging Face model identifier used as a fallback.
        local_dir: Folder where the checkpoint should be cached.
        device: Optional device override (``cuda``/``cpu``). Autodetect when ``None``.

    Returns:
        Tuple of ``(model, tokenizer)`` ready for inference.
    """
    target_device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    if local_dir and _has_local_checkpoint(local_dir):
        logger.info("Loading DeepPavlov BERT from '%s' on %s", local_dir, target_device)
        source = local_dir
    else:
        logger.warning(
            "Local checkpoint not found. Downloading '%s' from Hugging Face into '%s'.",
            model_name,
            local_dir or "<memory>",
        )
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
            tokenizer.save_pretrained(local_dir)
            model.save_pretrained(local_dir)
            logger.info("Saved downloaded checkpoint to '%s'.", local_dir)
        source = local_dir or model_name

    tokenizer = AutoTokenizer.from_pretrained(source)
    model = AutoModel.from_pretrained(source)

    model = model.to(target_device)
    model.eval()

    logger.info("Model and tokenizer are ready on %s.", target_device)
    return model, tokenizer
