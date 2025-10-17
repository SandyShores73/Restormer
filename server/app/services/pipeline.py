from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Optional
from zipfile import ZipFile

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


RESTORMER_MODEL_LIBRARY: dict[str, ModelSpec] = {
    "denoise": ModelSpec(
        name="restormer_denoise",
        url="https://huggingface.co/swz30/Restormer/resolve/main/restormer_denoise.onnx",
        filename="restormer_denoise.onnx",
    ),
    "motion_deblur": ModelSpec(
        name="restormer_motion_deblur",
        url="https://huggingface.co/swz30/Restormer/resolve/main/restormer_motion_deblur.onnx",
        filename="restormer_motion_deblur.onnx",
    ),
    "defocus_deblur": ModelSpec(
        name="restormer_defocus_deblur",
        url="https://huggingface.co/swz30/Restormer/resolve/main/restormer_defocus_deblur.onnx",
        filename="restormer_defocus_deblur.onnx",
    ),
}

MODE_LABELS: dict[str, str] = {
    "denoise": "Restormer Denoising",
    "motion_deblur": "Restormer Motion Deblurring",
    "defocus_deblur": "Restormer Defocus Deblurring",
}

SUPPORTED_MODES = tuple(RESTORMER_MODEL_LIBRARY.keys())

ProgressCallback = Callable[[str, float, str], Awaitable[None]]


class InferencePipeline:
    """Coordinates batched Restormer inference across denoise/deblur tasks."""

    def __init__(self) -> None:
        self.sessions: dict[str, ort.InferenceSession] = {}
        self._logger = logging.getLogger(__name__)

    def describe_environment(self) -> dict[str, object]:
        available = sorted(ort.get_available_providers())
        cached_models = []
        for spec in RESTORMER_MODEL_LIBRARY.values():
            model_path = Path(settings.models_dir) / spec.filename
            if model_path.exists():
                cached_models.append(spec.filename)
        return {
            "available_providers": available,
            "loaded_sessions": sorted(self.sessions.keys()),
            "cached_models": cached_models,
            "models_directory": str(settings.models_dir),
            "supported_modes": sorted(MODE_LABELS.items()),
        }

    async def prepare_all_models(self, progress_callback: Optional[ProgressCallback] = None) -> None:
        for index, (mode, spec) in enumerate(RESTORMER_MODEL_LIBRARY.items()):
            if progress_callback:
                await progress_callback(
                    "loading_models",
                    0.05 + index * 0.05,
                    f"Preparing {MODE_LABELS[mode]}",
                )
            await self._ensure_session(spec)
        if progress_callback:
            await progress_callback("loading_models", 0.25, "Restormer weights cached")

    async def process_batch(
        self,
        image_paths: list[Path],
        output_dir: Path,
        *,
        mode: str,
        passes: int,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> tuple[Path, list[dict[str, str]]]:
        if mode not in RESTORMER_MODEL_LIBRARY:
            raise ValueError(f"Unsupported Restormer mode '{mode}'")

        spec = RESTORMER_MODEL_LIBRARY[mode]
        self._logger.info(
            "Processing batch",
            extra={"mode": mode, "passes": passes, "image_count": len(image_paths)},
        )
        await self._emit(progress_callback, "loading_models", 0.05, f"Preparing {MODE_LABELS[mode]}")
        await self._ensure_session(spec)
        await self._emit(progress_callback, "loading_models", 0.08, "Weights ready")

        loop = asyncio.get_running_loop()
        total_images = len(image_paths)
        total_passes = max(1, passes) * max(1, total_images)
        completed_passes = 0

        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []

        for image_index, image_path in enumerate(image_paths):
            image_label = image_path.name
            await self._emit(
                progress_callback,
                "batch_prepare",
                0.1 + (image_index / max(1, total_images)) * 0.15,
                f"Loading {image_label}",
            )
            image = await loop.run_in_executor(None, Image.open, image_path)
            image = image.convert("RGB")
            array = np.array(image, dtype=np.float32) / 255.0
            array = np.expand_dims(array.transpose(2, 0, 1), axis=0)

            current = array
            for pass_index in range(max(1, passes)):
                await self._emit(
                    progress_callback,
                    "restormer_pass",
                    0.28 + (completed_passes / max(1, total_passes)) * 0.5,
                    f"{MODE_LABELS[mode]} pass {pass_index + 1} for {image_label}",
                )
                current = await self._run_session(spec.name, current)
                completed_passes += 1

            final_image = self._to_image(current)
            output_name = f"{Path(image_label).stem}_{mode}_x{max(1, passes)}.png"
            output_path = output_dir / output_name
            await self._emit(
                progress_callback,
                "saving",
                0.82 + ((image_index + 1) / max(1, total_images)) * 0.08,
                f"Saving {output_name}",
            )
            await loop.run_in_executor(None, final_image.save, output_path)
            saved_paths.append(output_path)

        archive_path = output_dir / "restormer_outputs.zip"
        if archive_path.exists():
            archive_path.unlink()
        await self._emit(progress_callback, "archiving", 0.92, "Packaging processed imagery")
        with ZipFile(archive_path, "w") as archive:
            for file_path in saved_paths:
                archive.write(file_path, arcname=file_path.name)

        await self._emit(progress_callback, "completed", 0.98, "Batch ready for download")
        manifest = [{"filename": path.name, "path": str(path)} for path in saved_paths]
        self._logger.info(
            "Batch completed",
            extra={"mode": mode, "output_files": len(saved_paths), "archive": str(archive_path)},
        )
        return archive_path, manifest

    async def _emit(
        self,
        progress_callback: Optional[ProgressCallback],
        stage: str,
        progress: float,
        message: str,
    ) -> None:
        if progress_callback:
            await progress_callback(stage, progress, message)

    async def _ensure_session(self, spec: ModelSpec) -> None:
        if spec.name in self.sessions:
            return
        model_path = Path(settings.models_dir) / spec.filename
        if not model_path.exists():
            self._logger.info("Downloading model", extra={"model": spec.filename})
            await download_file(spec.url, model_path)
        providers, provider_options = self._select_providers(spec)
        self._logger.info(
            "Creating session",
            extra={"model": spec.filename, "providers": providers},
        )
        session = ort.InferenceSession(
            str(model_path),
            providers=providers,
            provider_options=provider_options,
        )
        self.sessions[spec.name] = session

    async def _run_session(self, name: str, array: np.ndarray) -> np.ndarray:
        session = self.sessions[name]
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: array})
        return outputs[0]

    @staticmethod
    def _to_image(array: np.ndarray) -> Image.Image:
        clipped = np.clip(array, 0.0, 1.0)
        clipped = (clipped * 255).astype(np.uint8)
        clipped = clipped.squeeze(0).transpose(1, 2, 0)
        return Image.fromarray(clipped)

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
