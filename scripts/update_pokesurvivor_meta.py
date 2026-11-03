#!/usr/bin/env python3
"""Genera public/meta.json con el meta actual de PokéSurvivor.

El JSON está pensado para consumirse directamente desde un dashboard en React:
  - claves en camelCase y estables entre versiones (ver SCHEMA_VERSION),
  - valores numéricos como números (no strings con símbolos) para poder
    ordenar, filtrar y graficar sin parsear,
  - cada Pokémon y cada movimiento tiene un "id" único para usar como `key`,
  - fechas en ISO 8601 UTC (`new Date(meta.generatedAt)` funciona tal cual).

El archivo solo se reescribe si el contenido cambia (ignorando la marca de
tiempo), así el workflow programado no genera commits vacíos cada 6 horas.

Uso:
    python scripts/update_pokesurvivor_meta.py [--output RUTA] [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
GAME_VERSION = "1.52.8-halloween-meta"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "public" / "meta.json"

# Orden de tiers de mejor a peor; el dashboard puede usarlo para agrupar/ordenar.
TIERS = ["S+", "S", "A", "B", "C"]

EVENT = {
    "id": "halloween",
    "name": "Evento de Halloween",
    "focus": "Farmeo masivo de caramelos",
    "currency": "Caramelos de Halloween",
}

# --------------------------------------------------------------------------- #
# Datos del meta. Edita esta lista para actualizar las builds.
# --------------------------------------------------------------------------- #
POKEMON = [
    {
        "id": "darkrai",
        "name": "Darkrai",
        "region": "Sinnoh",
        "tier": "S+",
        "types": ["Siniestro"],
        "role": "Farmeo de Evento (AoE)",
        "isLegendary": True,
        "stats": {
            "hp": 1200,
            "speedPercent": 115,
            "attackMultiplier": 1.52,
            "attackStat": "SpA",
        },
        "kecleonNature": {
            "name": "Modesta",
            "increases": "SpA",
            "decreases": "Atk",
            "candyFarmNote": "Maximiza el daño en área para limpiar oleadas y recoger caramelos más rápido.",
        },
        "ability": {
            "name": "Mal Sueño",
            "nameEn": "Bad Dreams",
            "description": "Daño pasivo en área",
        },
        "item": {"name": "Garra Rápida", "effect": "+20% Recarga / Farmeo"},
        "moves": [
            {"name": "Pulso Umbrío", "category": "Especial", "goldenCard": "Sprint", "goldenCardEffect": "Ondas Múltiples"},
            {"name": "Bola Sombra", "category": "Especial", "goldenCard": "Reflejos", "goldenCardEffect": "Perforación"},
            {"name": "Maquinación", "category": "Buff", "goldenCard": "Poder", "goldenCardEffect": "Buff Máximo"},
            {"name": "Endurecer", "nameEn": "Harden", "category": "Defensivo", "goldenCard": "Armadura", "goldenCardEffect": "80% Reducción"},
        ],
    },
    {
        "id": "mewtwo",
        "name": "Mewtwo",
        "region": "Kanto",
        "tier": "S+",
        "types": ["Psíquico"],
        "role": "Glass Cannon / Eventos",
        "isLegendary": True,
        "stats": {
            "hp": 1100,
            "speedPercent": 120,
            "attackMultiplier": 1.55,
            "attackStat": "SpA",
        },
        "kecleonNature": {
            "name": "Miedosa",
            "increases": "Vel",
            "decreases": "Atk",
            "candyFarmNote": "Más velocidad = más recorrido del mapa y más caramelos recogidos por partida.",
        },
        "ability": {
            "name": "Presión",
            "nameEn": "Pressure",
            "description": "Reduce cooldowns de élites",
        },
        "item": {"name": "Vidasfera", "effect": "+30% Daño / -10% HP"},
        "moves": [
            {"name": "Ondas Mentales", "category": "Especial", "goldenCard": "Poder", "goldenCardEffect": "Daño Bruto"},
            {"name": "Psicorrayo", "category": "Especial", "goldenCard": "Reflejos", "goldenCardEffect": "Cadencia"},
            {"name": "Recuperación", "category": "Curación", "goldenCard": "Síntesis", "goldenCardEffect": "Regen Pasiva"},
            {"name": "Barrera", "category": "Defensivo", "goldenCard": "Vigor", "goldenCardEffect": "Escudo Extra"},
        ],
    },
    {
        "id": "slaking",
        "name": "Slaking",
        "region": "Hoenn",
        "tier": "S",
        "types": ["Normal"],
        "role": "Tanque Físico / F2P Top",
        "isLegendary": False,
        "stats": {
            "hp": 2400,
            "speedPercent": 95,
            "attackMultiplier": 1.58,
            "attackStat": "Atk",
        },
        "kecleonNature": {
            "name": "Firme",
            "increases": "Atk",
            "decreases": "SpA",
            "candyFarmNote": "Su ataque especial no se usa, así que la penalización es gratis; aguanta oleadas largas de farmeo.",
        },
        "ability": {
            "name": "Ausente Modificado",
            "nameEn": "Truant (modificado)",
            "description": "Burst masivo cada 5s",
        },
        "item": {"name": "Cinta Fuerte", "effect": "+15% Daño Físico"},
        "moves": [
            {"name": "Golpe Cuerpo", "category": "Físico", "goldenCard": "Poder", "goldenCardEffect": "Impacto Área"},
            {"name": "Terremoto", "category": "Físico", "goldenCard": "Reflejos", "goldenCardEffect": "Ondas Sísmicas"},
            {"name": "Corpulencia", "category": "Buff", "goldenCard": "Vigor", "goldenCardEffect": "Vida Máxima"},
            {"name": "Descanso", "category": "Curación", "goldenCard": "Síntesis", "goldenCardEffect": "Curación Total"},
        ],
    },
]


def slugify(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "-".join("".join(c if c.isalnum() else " " for c in normalized.lower()).split())


def build_pokemon(raw: dict, rank: int) -> dict:
    """Completa campos derivados (ids de movimientos, rank, etiquetas listas para mostrar)."""
    stats = raw["stats"]
    moves = [
        {"id": f"{raw['id']}-{slugify(m['name'])}", "slot": i + 1, **m}
        for i, m in enumerate(raw["moves"])
    ]
    nature = raw["kecleonNature"]
    return {
        **raw,
        "rank": rank,
        "moves": moves,
        # Etiquetas ya formateadas por si el dashboard solo quiere mostrarlas.
        "display": {
            "attack": f"×{stats['attackMultiplier']:.2f} {stats['attackStat']}",
            "speed": f"{stats['speedPercent']}%",
            "nature": f"{nature['name']} (+{nature['increases']}, -{nature['decreases']})",
        },
    }


def build_meta() -> dict:
    # Orden por tier; dentro del mismo tier se respeta el orden editorial de POKEMON.
    ordered = sorted(POKEMON, key=lambda p: TIERS.index(p["tier"]))
    pokemon = [build_pokemon(p, rank) for rank, p in enumerate(ordered, start=1)]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "gameVersion": GAME_VERSION,
        "generatedAt": None,  # se rellena al escribir
        "event": EVENT,
        "tiers": TIERS,
        "pokemon": pokemon,
    }


def validate(meta: dict) -> None:
    """Falla rápido si los datos rompen el contrato que espera el dashboard."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    for p in meta["pokemon"]:
        pid = p.get("id")
        if not pid or pid in seen_ids:
            errors.append(f"id de Pokémon vacío o duplicado: {pid!r}")
        seen_ids.add(pid)
        if p["tier"] not in TIERS:
            errors.append(f"{pid}: tier desconocido {p['tier']!r}")
        if len(p["moves"]) != 4:
            errors.append(f"{pid}: la build debe tener exactamente 4 movimientos (tiene {len(p['moves'])})")
        for key in ("hp", "speedPercent", "attackMultiplier"):
            if not isinstance(p["stats"].get(key), (int, float)) or isinstance(p["stats"].get(key), bool):
                errors.append(f"{pid}: stats.{key} debe ser numérico")
        for m in p["moves"]:
            for key in ("name", "category", "goldenCard"):
                if not m.get(key):
                    errors.append(f"{pid}: movimiento sin '{key}'")
    if errors:
        raise ValueError("Datos de meta inválidos:\n  - " + "\n  - ".join(errors))


def without_timestamp(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if k != "generatedAt"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="ruta del JSON (por defecto public/meta.json)")
    parser.add_argument("--force", action="store_true", help="reescribir aunque no haya cambios")
    args = parser.parse_args(argv)

    meta = build_meta()
    validate(meta)

    output: Path = args.output
    if output.exists() and not args.force:
        try:
            current = json.loads(output.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = None
        if current is not None and without_timestamp(current) == without_timestamp(meta):
            print(f"Sin cambios en el meta; {output} se deja igual.")
            return 0

    meta["generatedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(output)
    print(f"Archivo {output} generado correctamente ({len(meta['pokemon'])} Pokémon).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
