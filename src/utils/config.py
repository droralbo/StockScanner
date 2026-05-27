from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class IndicatorConfig(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "IndicatorConfig":
        name = raw["name"]
        params = {k: v for k, v in raw.items() if k != "name"}
        return cls(name=name, params=params)


class SymbolConfig(BaseModel):
    symbol: str
    indicators: list[IndicatorConfig]
    interval: str | None = None
    cooldown_minutes: int | None = None


class WatchlistConfig(BaseModel):
    default_interval: str = "5"
    default_cooldown_minutes: int = 60
    default_candles_limit: int = 200
    symbols: list[SymbolConfig]

    def get_interval(self, symbol_cfg: SymbolConfig) -> str:
        return symbol_cfg.interval or self.default_interval

    def get_cooldown(self, symbol_cfg: SymbolConfig) -> int:
        return symbol_cfg.cooldown_minutes or self.default_cooldown_minutes


def load_watchlist(path: Path | str) -> WatchlistConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"watchlist not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    defaults = raw.get("defaults", {})
    symbols_raw = raw.get("symbols", [])

    symbols = []
    for s in symbols_raw:
        indicators = [IndicatorConfig.from_raw(ind) for ind in s.get("indicators", [])]
        symbols.append(
            SymbolConfig(
                symbol=s["symbol"],
                indicators=indicators,
                interval=s.get("interval"),
                cooldown_minutes=s.get("cooldown_minutes"),
            )
        )

    return WatchlistConfig(
        default_interval=str(defaults.get("interval", "5")),
        default_cooldown_minutes=int(defaults.get("cooldown_minutes", 60)),
        default_candles_limit=int(defaults.get("candles_limit", 200)),
        symbols=symbols,
    )
