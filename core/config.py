from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    name: str = "LogiBox"
    display_name: str = "LogiBox · 物流工程分析平台"
    version: str = "3.4.0"
    edition: str = "矩阵版"
    organization: str = "LogiBox"
    default_width: int = 1500
    default_height: int = 900
    minimum_width: int = 1180
    minimum_height: int = 720


APP_CONFIG = AppConfig()
