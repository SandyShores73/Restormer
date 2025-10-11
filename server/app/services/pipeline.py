from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Optional

import numpy as np
import onnxruntime as ort
from PIL import Image

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


ProgressCallback = Callable[[str, float, str], Awaitable[None]]


class InferencePipeline:
    """Coordinates denoising, upscaling, and deblurring passes."""

    def __init__(self) -> None:
        self.sessions: dict[str, ort.InferenceSession] = {}
        self._logger = logging.getLogger(__name__)

    def describe_environment(self) -> dict[str, object]:
        available = sorted(ort.get_available_providers())
        cached_models = []
        for spec in (RESTORMER_SPEC, REAL_ESRGAN_SPEC, DEBLUR_SPEC):
            model_path = Path(settings.models_dir) / spec.filename
            if model_path.exists():
                cached_models.append(spec.filename)
        return {
            "available_providers": available,
            "loaded_sessions": sorted(self.sessions.keys()),
            "cached_models": cached_models,
            "models_directory": str(settings.models_dir),
        }

    async def load_models(self, progress_callback: Optional[ProgressCallback] = None) -> None:
        for index, spec in enumerate((RESTORMER_SPEC, REAL_ESRGAN_SPEC, DEBLUR_SPEC)):
            if progress_callback:
                await progress_callback(
                    "loading_models",
                    0.1 + index * 0.05,
                    f"Preparing {spec.name.replace('_', ' ')}",
                )
            await self._load_model(spec)
        if progress_callback:
            await progress_callback("loading_models", 0.28, "Models ready for inference")

    async def _load_model(self, spec: ModelSpec) -> None:
        model_path = Path(settings.models_dir) / spec.filename
        if not model_path.exists():
            await download_file(spec.url, model_path)
        providers, provider_options = self._select_providers(spec)
        session = ort.InferenceSession(
            str(model_path),
            providers=providers,
            provider_options=provider_options,
        )
        self.sessions[spec.name] = session

    async def process(
        self,
        image_path: Path,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        async def emit(stage: str, progress: float, message: str) -> None:
            if progress_callback:
                await progress_callback(stage, progress, message)

        await emit("preparing", 0.1, "Loading source image")
        await self.load_models(progress_callback=progress_callback)
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, Image.open, image_path)
        image = image.convert("RGB")
        array = np.array(image).astype(np.float32) / 255.0
        array = array.transpose(2, 0, 1)
        array = np.expand_dims(array, axis=0)

        await emit("denoise", 0.35, "Running Restormer denoise pass")
        denoised = await self._run_session(RESTORMER_SPEC.name, array)
        await emit("enhance", 0.55, "Refining detail with Real-ESRGAN")
        refined = await self._run_session(REAL_ESRGAN_SPEC.name, denoised)
        await emit("refocus", 0.75, "Correcting focus with NAFNet")
        focused = await self._run_session(DEBLUR_SPEC.name, refined)

        focused = np.clip(focused, 0.0, 1.0)
        focused = (focused * 255).astype(np.uint8)
        focused = focused.squeeze(0).transpose(1, 2, 0)

        output_image = Image.fromarray(focused)
        await emit("saving", 0.9, "Compositing final output")
        await loop.run_in_executor(None, output_image.save, output_path)
        await emit("saving", 0.98, "Output saved to disk")

    async def _run_session(self, name: str, array: np.ndarray) -> np.ndarray:
        session = self.sessions[name]
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: array})
        return outputs[0]

    def _select_providers(self, spec: ModelSpec) -> tuple[list[str], list[dict]]:
        """Resolve compatible execution providers for the current environment."""

        available = set(ort.get_available_providers())
        requested = list(spec.providers)
        providers: list[str] = [provider for provider in requested if provider in available]

        if not providers:
            providers = ["CPUExecutionProvider"]

        if providers != requested:
            self._logger.info(
                "Using providers %s for model '%s' (available=%s)",
                providers,
                spec.name,
                sorted(available),
            )

        provider_options: list[dict] = []
        for provider in providers:
            if provider == "DmlExecutionProvider":
                provider_options.append({"device_id": 0})
            else:
                provider_options.append({})

        return providers, provider_options


pipeline = InferencePipeline()
