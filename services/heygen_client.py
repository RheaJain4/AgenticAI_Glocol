"""
HeyGen Video Generation Client
================================
Interface for generating AI-powered news videos from emergency scripts.
Currently stubbed — enable by setting HEYGEN_API_KEY in .env.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from config import HEYGEN_API_KEY, is_heygen_enabled

logger = logging.getLogger(__name__)


class HeyGenClient:
    """
    Interface for the HeyGen API.
    When HEYGEN_API_KEY is not set, operates in stub mode.
    """

    def __init__(self):
        self._enabled = is_heygen_enabled()
        if not self._enabled:
            logger.info(
                "HeyGen is STUBBED — set HEYGEN_API_KEY in .env to enable video generation."
            )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def create_video(
        self,
        script: str,
        avatar_id: str = "default",
        voice_id: str = "default",
    ) -> str:
        """
        Submit a video generation job.

        Args:
            script: The narration text for the video.
            avatar_id: HeyGen avatar ID.
            voice_id: HeyGen voice ID.

        Returns:
            video_id: A unique identifier for the video job.
        """
        if not self._enabled:
            video_id = f"stub_{uuid.uuid4().hex[:8]}"
            logger.info(
                "[STUB] Video creation requested (id=%s). "
                "Script length: %d chars. No actual video will be generated.",
                video_id,
                len(script),
            )
            return video_id

        # --- Real HeyGen API integration (future) ---
        # import httpx
        # response = httpx.post(
        #     "https://api.heygen.com/v2/video/generate",
        #     headers={"X-Api-Key": HEYGEN_API_KEY},
        #     json={
        #         "video_inputs": [{
        #             "character": {"type": "avatar", "avatar_id": avatar_id},
        #             "voice": {"type": "text", "input_text": script, "voice_id": voice_id},
        #         }],
        #     },
        # )
        # return response.json()["data"]["video_id"]
        raise NotImplementedError("Real HeyGen integration not yet implemented.")

    def poll_status(self, video_id: str) -> Dict[str, Any]:
        """
        Check the status of a video generation job.

        Returns:
            dict with "status" and "progress" keys.
        """
        if not self._enabled or video_id.startswith("stub_"):
            return {
                "video_id": video_id,
                "status": "completed",
                "progress": 100,
                "message": "Stub mode — no video generated.",
            }

        raise NotImplementedError("Real HeyGen integration not yet implemented.")

    def download_video(
        self, video_id: str, output_path: str
    ) -> Optional[str]:
        """
        Download a completed video to the specified path.

        Returns:
            The file path if successful, None if stubbed.
        """
        if not self._enabled or video_id.startswith("stub_"):
            logger.info(
                "[STUB] Video download requested for %s — no file to download.",
                video_id,
            )
            return None

        raise NotImplementedError("Real HeyGen integration not yet implemented.")

    def generate_and_save(
        self,
        script: str,
        output_dir: str,
        avatar_id: str = "default",
        voice_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Full workflow: create video → poll → download.
        In stub mode, saves the script as a text file instead.

        Returns:
            Dict with video_id, status, and file_path (if available).
        """
        video_id = self.create_video(script, avatar_id, voice_id)

        if not self._enabled or video_id.startswith("stub_"):
            # Save the broadcast script as text
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)
            script_path = output / "broadcast_script.txt"
            script_path.write_text(script, encoding="utf-8")
            logger.info("[STUB] Broadcast script saved to %s", script_path)

            return {
                "video_id": video_id,
                "status": "stub_completed",
                "file_path": str(script_path),
                "message": "HeyGen is stubbed. Script saved as text file.",
            }

        # Real flow: poll until complete, then download
        status = self.poll_status(video_id)
        if status["status"] == "completed":
            file_path = self.download_video(
                video_id, str(Path(output_dir) / "broadcast_video.mp4")
            )
            return {
                "video_id": video_id,
                "status": "completed",
                "file_path": file_path,
            }

        return {"video_id": video_id, "status": status["status"]}
