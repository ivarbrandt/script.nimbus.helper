import xbmc
import threading
from typing import Optional, Type
from dataclasses import dataclass
from ..image import ImageBlur


@dataclass
class ImageAnalysisConfig:
    enabled: bool = False
    radius: str = "30"  # Changed default to match original
    saturation: str = "1.5"

    @classmethod
    def from_skin_settings(cls):
        """Create config from current skin settings"""
        return cls(
            enabled=xbmc.getCondVisibility("Skin.HasSetting(Enable.BackgroundBlur)"),
            radius=xbmc.getInfoLabel("Skin.String(BlurRadius)") or "30",
            saturation=xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.5",
        )


class ImageMonitor(threading.Thread):
    """Monitors and analyzes images in a separate thread."""

    def __init__(
        self,
        analyzer_class: Type[ImageBlur],
        config: Optional[ImageAnalysisConfig] = None,
    ):
        super().__init__()
        self.analyzer_class = analyzer_class
        self.config = config or ImageAnalysisConfig()
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self) -> None:
        """Main monitoring loop."""
        monitor = xbmc.Monitor()
        while not self._stop_event.is_set():
            try:
                if self._is_paused():
                    xbmc.Monitor().waitForAbort(2)
                    continue

                if self._not_nimbus():
                    xbmc.Monitor().waitForAbort(15)
                    continue

                current_config = ImageAnalysisConfig.from_skin_settings()

                if current_config.enabled:
                    self.analyzer_class(
                        radius=current_config.radius,
                        saturation=current_config.saturation,
                    )
                    monitor.waitForAbort(0.2)
                else:
                    monitor.waitForAbort(3)

            except Exception as e:
                xbmc.log(f"Image analysis error: {str(e)}", xbmc.LOGERROR)
                xbmc.Monitor().waitForAbort(0.2)

    def _is_paused(self) -> bool:
        return xbmc.getInfoLabel("Window(Home).Property(pause_services)") == "true"

    def _not_nimbus(self) -> bool:
        return xbmc.getSkinDir() != "skin.nimbus"

    def stop(self) -> None:
        self._stop_event.set()
