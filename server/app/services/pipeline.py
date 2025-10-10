from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import onnxruntime as ort
from PIL import Image
import numpy as np

from ..core.config import settings
from ..utils.download import download_file


@dataclass
class ModelSpec:
    name: str
    url: str
    filename: str
    providers: Iterable[str] = ("DmlExecutionProvider", "CPUExecutionProvider")


RESTORMER_SPEC = ModelSpec(
    name="restormer_denoise",
    url="https://huggingface.co/itsfivee/Restormer/resolve/main/restormer_denoise.onnx",
    filename="restormer_denoise.onnx",
)

REAL_ESRGAN_SPEC = ModelSpec(
    name="realesrgan_x2plus",
    url="https://huggingface.co/nateraw/real-esrgan/resolve/main/RealESRGAN_x2plus.onnx",
    filename="realesrgan_x2plus.onnx",
)

DEBLUR_SPEC = ModelSpec(
    name="nafnet_deblur",
    url="https://huggingface.co/raman-sc/nafnet/resolve/main/NAFNet-width64-Deblur_oneshot.onnx",
    filename="nafnet_deblur.onnx",
)


class InferencePipeline:
    """Coordinates denoising, upscaling, and deblurring passes."""

    def __init__(self) -> None:
        self.sessions: dict[str, ort.InferenceSession] = {}

    async def load_models(self) -> None:
        for spec in (RESTORMER_SPEC, REAL_ESRGAN_SPEC, DEBLUR_SPEC):
            await self._load_model(spec)

    async def _load_model(self, spec: ModelSpec) -> None:
        model_path = Path(settings.models_dir) / spec.filename
        if not model_path.exists():
            await download_file(spec.url, model_path)
        session = ort.InferenceSession(
            str(model_path),
            providers=list(spec.providers),
            provider_options=[{"device_id": 0}, {}],
        )
        self.sessions[spec.name] = session

    async def process(self, image_path: Path, output_path: Path) -> None:
        await self.load_models()
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, Image.open, image_path)
        image = image.convert("RGB")
        array = np.array(image).astype(np.float32) / 255.0
        array = array.transpose(2, 0, 1)
        array = np.expand_dims(array, axis=0)

        denoised = await self._run_session(RESTORMER_SPEC.name, array)
        refined = await self._run_session(REAL_ESRGAN_SPEC.name, denoised)
        focused = await self._run_session(DEBLUR_SPEC.name, refined)

        focused = np.clip(focused, 0.0, 1.0)
        focused = (focused * 255).astype(np.uint8)
        focused = focused.squeeze(0).transpose(1, 2, 0)

        output_image = Image.fromarray(focused)
        await loop.run_in_executor(None, output_image.save, output_path)

    async def _run_session(self, name: str, array: np.ndarray) -> np.ndarray:
        session = self.sessions[name]
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: array})
        return outputs[0]


pipeline = InferencePipeline()
