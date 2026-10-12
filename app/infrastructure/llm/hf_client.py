from __future__ import annotations

import gc
import logging
import re
import threading
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.config import get_settings
from app.infrastructure.llm.errors import GenerationError

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)

__all__ = ["GenerationError", "HFTransformersClient", "get_llm"]

# "template template template template ..." style repetition loops.
_REPEAT_RUN = re.compile(r"\b(\w{2,20})(?:\s+\1){4,}", re.IGNORECASE)

def _looks_degenerate(text: str) -> bool:
    """True when the answer is token soup instead of English prose."""
    if not text.strip():
        return True
    if _REPEAT_RUN.search(text):
        return True
    if text.count("\ufffd") > 10:
        return True
    if sum(1 for ch in text if ord(ch) >= 0x1F300) > 10:
        return True
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) >= 40:
        # Non-Latin/emoji bursts (Chinese, Korean, Devanagari, ...) in an
        # English answer means the logits collapsed.
        odd = sum(1 for ch in letters if ord(ch) > 0x024F)
        if odd / len(letters) > 0.15:
            return True
    return False

class HFTransformersClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.llm_model
        self._device = settings.resolved_llm_device
        self._max_new_tokens = settings.llm_max_new_tokens
        self._temperature = settings.llm_temperature
        self._lock = threading.Lock()
        self._tokenizer: Any = None
        self._model: Any = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # NEVER use float16 on CPU: PyTorch's CPU fp16 kernels produce
            # NaN/garbage logits, which shows up as token soup in the answer.
            dtype = torch.float16 if self._device == "cuda" else torch.float32

            logger.info(
                "loading LLM %s (device=%s, dtype=%s)",
                self._model_name,
                self._device,
                dtype,
            )
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_name,
                dtype=dtype,
                low_cpu_mem_usage=True,
            )
            try:
                self._model.to(self._device)
            except Exception as exc:
                # Do not swallow this: a fp16 model left on CPU answers with
                # garbage. Fall back to float32 on CPU instead.
                logger.warning(
                    "moving LLM to %s failed (%s); falling back to cpu/float32",
                    self._device,
                    exc,
                )
                if dtype != torch.float32:
                    self._model.to("cpu", torch.float32)
                dtype = torch.float32
                self._device = "cpu"
            self._model.eval()
            logger.info("LLM ready: %s on %s", self._model_name, self._device)

    def warm_up(self) -> None:
        self._ensure_loaded()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def ready(self) -> bool:
        return self._model is not None

    def generate(self, system: str, user: str, _retry: bool = True) -> str:
        import torch

        self._ensure_loaded()
        assert self._tokenizer is not None and self._model is not None

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            encoded = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            inputs = encoded["input_ids"].to(self._device)
            attention_mask = encoded.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self._device)

            with torch.inference_mode():
                output = self._model.generate(
                    input_ids=inputs,
                    attention_mask=attention_mask,
                    max_new_tokens=self._max_new_tokens,
                    do_sample=self._temperature > 0,
                    temperature=self._temperature or None,
                    repetition_penalty=1.1,
                    eos_token_id=self._tokenizer.eos_token_id,
                    pad_token_id=self._tokenizer.eos_token_id,
                )

            generated = output[0][inputs.shape[-1]:]
            text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
            if not text:
                raise GenerationError("Model produced an empty response.")
            if _looks_degenerate(text):
                if not _retry:
                    raise GenerationError(
                        "The LLM returned a degenerate (repetitive/garbled) "
                        "answer. Free VRAM (close GPU apps) or lower "
                        "LLM_MAX_NEW_TOKENS, then try again."
                    )
                # In-process state went bad (VRAM pressure / fp16 fallback).
                # Drop the weights, reload once and retry.
                logger.warning("degenerate output detected; reloading LLM and retrying")
                self._free()
                if self._device == "cuda":
                    torch.cuda.empty_cache()
                return self.generate(system, user, _retry=False)
            return text

        except torch.OutOfMemoryError as exc:
            self._free()
            if self._device == "cuda":
                torch.cuda.empty_cache()
            raise GenerationError(
                "The LLM ran out of "
                f"{'VRAM' if self._device == 'cuda' else 'memory'}. "
                "Try a smaller LLM_MAX_NEW_TOKENS or a smaller model."
            ) from exc
        except GenerationError:
            raise
        except Exception as exc:
            logger.exception("generation failed")
            raise GenerationError(f"{type(exc).__name__}: {exc}") from exc

    def _free(self) -> None:
        with self._lock:
            self._model = None
            self._tokenizer = None
            gc.collect()

@lru_cache
def get_llm() -> HFTransformersClient:
    return HFTransformersClient()
