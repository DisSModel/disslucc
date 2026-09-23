# Goldens do TerraME/LuccME

`goldens/` é uma cópia dos goldens gerados em
[LambdaGeo/terrame-docker](https://github.com/LambdaGeo/terrame-docker)
**v0.1.0** (`benchmark/goldens/`), com TerraME 2.0.1 + LuccME `6244dd4`. É contra eles que o
disslucc é validado, algoritmo por algoritmo.

Scripts, saídas originais do TerraME e o gerador ficam **só** no terrame-docker; aqui
fica só o resultado, para os testes rodarem sem Docker.

## O que há em `goldens/<nome>/`

| Arquivo | Conteúdo |
|---|---|
| `<nome>.csv.gz` | estado de cada célula ao fim de cada ano: `year,id,col,row`, `<classe>_out` e `<classe>_pot`, 12 casas decimais |
| `terrame.log` | saída do TerraME (demanda, área alocada, iterações por ano) |
| `manifest.json` | script de origem e SHA-256, versões, anos, colunas, iterações por ano (`iterations_per_year`) e a verificação cruzada |

`col`/`row` alinham com `data/input/csAC.zip` (`col`, `row`) e `cs_moju.zip` (`col`, `lin`).

## Quais são

Só os goldens que os testes deste repositório usam. Os outros (os 21 labs do pacote
LuccME) ficam no terrame-docker e entram aqui quando o componente correspondente for
implementado, junto com o teste que os usa.

| Golden | Componentes | Usado em |
|---|---|---|
| `lab01` | PreComputedValues + CLinearRegression + CClueLike (`maxDifference` 5000) | `test_goldens_per_year.py` |
| `lab01_md1643` | idem, `maxDifference` 1643: itera 8–26 vezes por ano | `test_goldens_per_year.py`, `test_validation_lab1.py`, discriminância |
| `lab15` | PreComputedValues + DLogisticRegression + DClueSLike (`maxDifference` 300) | `test_goldens_per_year.py` |
| `lab15_md10` | idem, `maxDifference` 10: itera 56–67 vezes por ano | `test_goldens_per_year.py`, `test_validation_lab15.py`, discriminância |

O último ano de `lab01_md1643` e de `lab15_md10` é a antiga referência deste repositório
(`benchmark/data/*.zip`).

## Antes de usar como prova

- Nos labs do pacote a alocação aceita a primeira passada em todos os anos; só as
  variantes `_md` testam o laço de convergência.
- Nos labs com `CClueLike`, o TerraME nunca executa `correctCellChange` (typo
  `regionregionAloc`). O disslucc executa por padrão; compare com
  `cell_correction=False`. Ver `docs/validation.md`.
- Compare com tolerância (1e-9 no arquivo; os testes usam MAE < 1e-6), nunca pelo
  SHA-256: de uma geração para outra, algumas células mudam na 12ª casa decimal.

## Adicionar ou atualizar

Copie a pasta do golden de `benchmark/goldens/<nome>/` do terrame-docker, na mesma versão
(`v0.1.0`), para `benchmark/goldens/<nome>/` aqui, no mesmo commit do teste que passa a
usá-lo. Nunca edite um golden à mão; para regenerar, use `benchmark/generate.sh <nome>`
no terrame-docker.
