# pokeliketierlist

Meta y builds de **PokéSurvivor**, generados automáticamente en `public/meta.json`.

## Cómo funciona

- `scripts/update_pokesurvivor_meta.py` contiene los datos del meta (lista `POKEMON`), los valida y escribe `public/meta.json`.
  Solo reescribe el archivo si el contenido cambió, así no hay commits vacíos.
- `.github/workflows/update-meta.yml` ejecuta el script cada 6 horas y con **Run workflow** (`workflow_dispatch`),
  y hace commit + push de `public/meta.json` si cambió, usando `GITHUB_TOKEN` con `contents: write`.

Para actualizar el meta, edita `POKEMON` en el script y ejecútalo:

```bash
python3 scripts/update_pokesurvivor_meta.py
```

`--force` reescribe el archivo (y la fecha) aunque no haya cambios; `--output RUTA` cambia el destino.

## Consumirlo desde React

```tsx
const res = await fetch("/meta.json");
const meta: PokeSurvivorMeta = await res.json();

meta.pokemon.map((p) => <PokemonCard key={p.id} pokemon={p} />);
```

Tipos TypeScript del archivo (`schemaVersion: 1`):

```ts
export interface PokeSurvivorMeta {
  schemaVersion: 1;
  gameVersion: string;
  generatedAt: string; // ISO 8601 UTC, p. ej. "2026-11-03T22:30:56Z"
  event: { id: string; name: string; focus: string; currency: string };
  tiers: Tier[]; // de mejor a peor
  pokemon: MetaPokemon[]; // ya ordenados por rank
}

export type Tier = "S+" | "S" | "A" | "B" | "C";

export interface MetaPokemon {
  id: string;
  rank: number;
  name: string;
  region: string;
  tier: Tier;
  types: string[];
  role: string;
  isLegendary: boolean;
  stats: {
    hp: number;
    speedPercent: number; // 115 => 115%
    attackMultiplier: number; // 1.52
    attackStat: "Atk" | "SpA";
  };
  kecleonNature: { name: string; increases: string; decreases: string; candyFarmNote: string };
  ability: { name: string; nameEn?: string; description: string };
  item: { name: string; effect: string };
  moves: MetaMove[]; // siempre 4
  display: { attack: string; speed: string; nature: string }; // etiquetas ya formateadas
}

export interface MetaMove {
  id: string;
  slot: 1 | 2 | 3 | 4;
  name: string;
  nameEn?: string;
  category: string;
  goldenCard: string; // carta dorada de evolución
  goldenCardEffect: string;
}
```
