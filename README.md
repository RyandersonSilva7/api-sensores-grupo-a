# API Mock — Monitoramento Ambiental com Sensores IoT (Grupo A)

**Disciplina:** Sistemas Distribuídos — IFCE Campus Tianguá · **Prof.:** Nécio de Lima Veras
**Atividade:** Representação de dados e interoperabilidade — **Estudo de Caso 1**
**Grupo A (API mock)** → consumida pelo **Grupo B (aplicação cliente)**

API mock em **FastAPI** que simula sensores agrícolas de diferentes fabricantes e entrega as mesmas leituras em **6 formatos de representação de dados**, escolhidos pelo cliente a cada requisição.

---

## Sumário
1. [Desafios de interoperabilidade simulados](#1-desafios-de-interoperabilidade-simulados)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Como rodar o servidor localmente](#3-como-rodar-o-servidor-localmente)
4. [Contrato de dados](#4-contrato-de-dados)
5. [Endpoint e escolha do formato](#5-endpoint-e-escolha-do-formato)
6. [Exemplos de requisição e resposta](#6-exemplos-de-requisição-e-resposta)
7. [Dados simulados (e o que o cliente deve tratar)](#7-dados-simulados-e-o-que-o-cliente-deve-tratar)
8. [Como consumir (guia rápido para o Grupo B)](#8-como-consumir-guia-rápido-para-o-grupo-b)
9. [Clientes de teste incluídos](#9-clientes-de-teste-incluídos)
10. [Comparação dos formatos](#10-comparação-dos-formatos)
11. [Problemas comuns](#11-problemas-comuns)

---

## 1. Desafios de interoperabilidade simulados

| Desafio (enunciado) | Onde aparece nos dados |
| :--- | :--- |
| Sensores em **°C ou °F** | Campo `unidade_temp` (`"C"` ou `"F"`); `SENS-US-02` e `SENS-US-04` reportam em °F |
| **Fusos horários** diferentes | `timestamp` ISO 8601 com offsets `-03:00`, `Z` (UTC) e `-05:00` |
| Medições **ausentes** | Campos `null` (JSON/YAML), vazios (CSV/XML) ou não preenchidos (Protobuf) |
| Medições **inválidas** | `temperatura = -999.0` (código de erro de hardware) em `SENS-CH-03` |

> A API **não normaliza nada de propósito**: os dados saem "sujos" como chegariam de fabricantes diferentes. Padronizar é responsabilidade do cliente (Grupo B).

---

## 2. Estrutura do repositório

```
.
├── main.py            # Servidor FastAPI (endpoint /api/leituras, 6 formatos)
├── sensor.proto       # Contrato Protocol Buffers (proto3)
├── sensor_pb2.py      # Código Python gerado a partir do sensor.proto
├── cliente_teste.py   # Cliente de terminal: consulta os 6 formatos e mede o tamanho
├── interface.py       # Cliente gráfico (Tkinter): inspetor dos formatos da API
├── requirements.txt   # Dependências
└── README.md
```

---

## 3. Como rodar o servidor localmente

### Pré-requisitos
- **Python 3.10+** (testado com 3.11) e **pip**
- (Opcional) Git

### Passo a passo

```bash
# 1. Clonar o repositório
git clone <URL-DO-REPOSITORIO>
cd <NOME-DA-PASTA>

# 2. (Recomendado) Criar e ativar um ambiente virtual
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (CMD/PowerShell):
.venv\Scripts\activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Iniciar o servidor
uvicorn main:app --reload
```

O servidor sobe em **http://localhost:8000**:

| O quê | URL |
| :--- | :--- |
| Endpoint principal | http://localhost:8000/api/leituras |
| Documentação interativa (Swagger UI) | http://localhost:8000/docs |
| Esquema OpenAPI (JSON) | http://localhost:8000/openapi.json |

Para o **Grupo B** acessar de **outra máquina da mesma rede** (na demonstração), suba o servidor escutando em todas as interfaces e informe o IP da máquina do servidor:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
# o cliente acessa: http://<IP-DA-MAQUINA>:8000/api/leituras
```

### Recompilar o contrato Protocol Buffers (só se necessário)
O `sensor_pb2.py` já vem pronto no repositório. Se aparecer erro de versão do `protobuf` ao iniciar, regenere-o com a versão instalada no seu ambiente:

```bash
python -m grpc_tools.protoc -I. --python_out=. sensor.proto
```

### Testar rapidamente
Com o servidor rodando, em **outro terminal**:

```bash
curl "http://localhost:8000/api/leituras?formato=json"
# ou
python cliente_teste.py
```

---

## 4. Contrato de dados

Cada leitura representa uma coleta de um sensor.

| Campo | Tipo | Descrição | Observações |
| :--- | :--- | :--- | :--- |
| `sensor_id` | string | Identificador único do sensor | Ex.: `SENS-BR-01` |
| `localizacao` | string | Setor/talhão da propriedade | Ex.: `Talhao Norte - Setor A` |
| `timestamp` | string | Data/hora da coleta, **ISO 8601** | Offset **varia** por sensor (`-03:00`, `Z`, `-05:00`) |
| `temperatura` | float \| null | Temperatura medida | Unidade em `unidade_temp`. Pode vir `null` ou `-999.0` (inválida) |
| `unidade_temp` | string | `"C"` (Celsius) ou `"F"` (Fahrenheit) | Sempre presente |
| `umidade` | float \| null | Umidade relativa do ar (%) | Pode vir `null` |
| `luminosidade` | int \| null | Luminosidade (lux) | Pode vir `null` |
| `precipitacao` | float \| null | Precipitação (mm) | Pode vir `null` |

Contrato Protocol Buffers (`sensor.proto`):

```proto
syntax = "proto3";
package agro;

message LeituraSensor {
  string sensor_id = 1;
  string localizacao = 2;
  string timestamp = 3;
  optional double temperatura = 4;
  string unidade_temp = 5;
  optional double umidade = 6;
  optional int32 luminosidade = 7;
  optional double precipitacao = 8;
}

message ListaLeituras {
  repeated LeituraSensor leituras = 1;
}
```

> Os campos de medição usam `optional` para que o cliente consiga distinguir **"valor 0.0 medido"** de **"medição ausente"** com `HasField()`. Sem isso, o proto3 devolveria `0.0` para campos não enviados.

---

## 5. Endpoint e escolha do formato

### `GET /api/leituras`

O formato pode ser escolhido de **duas formas**. Se as duas forem enviadas, **o parâmetro `formato` tem prioridade** sobre o cabeçalho `Accept`. Sem nenhuma das duas, a resposta é **JSON**.

1. **Query string:** `?formato=<opcao>`
2. **Cabeçalho HTTP:** `Accept: <media-type>`

| Formato | `?formato=` | `Accept` | `Content-Type` da resposta | Natureza |
| :--- | :--- | :--- | :--- | :--- |
| **JSON** (padrão) | `json` | `application/json` | `application/json` | Textual |
| **XML** | `xml` | `application/xml` | `application/xml` | Textual |
| **YAML** | `yaml` | `application/x-yaml` | `application/x-yaml` | Textual |
| **CSV** (formato textual próprio) | `csv` | `text/csv` | `text/csv` | Textual, separador `;` |
| **Protocol Buffer** | `protobuf` | `application/x-protobuf` | `application/x-protobuf` | Binário (requer `sensor.proto`) |
| **Serialização** (Python `pickle`) | `serializacao` | `application/octet-stream` | `application/octet-stream` | Binário (somente clientes Python) |

**Códigos de status**

| Código | Quando |
| :--- | :--- |
| `200 OK` | Leituras retornadas |
| `422 Unprocessable Entity` | `formato` fora das 6 opções válidas |

---

## 6. Exemplos de requisição e resposta

> Valores abaixo vêm diretamente dos dados de `main.py`. Respostas abreviadas mostram só as 2 primeiras leituras, exceto onde indicado.

### 6.1 JSON — `GET /api/leituras?formato=json`

```bash
curl "http://localhost:8000/api/leituras?formato=json"
```
```json
{
  "leituras": [
    {
      "sensor_id": "SENS-BR-01",
      "localizacao": "Talhao Norte - Setor A",
      "timestamp": "2026-11-17T08:30:00-03:00",
      "temperatura": 28.5,
      "unidade_temp": "C",
      "umidade": 65.0,
      "luminosidade": 820,
      "precipitacao": 0.0
    },
    {
      "sensor_id": "SENS-US-02",
      "localizacao": "Estufa Sul - Setor B",
      "timestamp": "2026-11-17T11:32:00Z",
      "temperatura": 89.6,
      "unidade_temp": "F",
      "umidade": 42.5,
      "luminosidade": 950,
      "precipitacao": null
    }
  ]
}
```

### 6.2 XML — `GET /api/leituras?formato=xml`

```bash
curl "http://localhost:8000/api/leituras?formato=xml"
```
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<monitoramento>
  <leitura>
    <sensor_id>SENS-BR-01</sensor_id>
    <localizacao>Talhao Norte - Setor A</localizacao>
    <timestamp>2026-11-17T08:30:00-03:00</timestamp>
    <temperatura>28.5</temperatura>
    <unidade_temp>C</unidade_temp>
    <umidade>65.0</umidade>
    <luminosidade>820</luminosidade>
    <precipitacao>0.0</precipitacao>
  </leitura>
  <!-- demais <leitura>; valores None viram tag vazia, ex.: <precipitacao></precipitacao> -->
</monitoramento>
```
*(O XML é gerado pela biblioteca `dicttoxml`; a indentação real pode diferir — o conteúdo é o mesmo.)*

### 6.3 YAML — `GET /api/leituras?formato=yaml`

```bash
curl "http://localhost:8000/api/leituras?formato=yaml"
```
```yaml
leituras:
- sensor_id: SENS-BR-01
  localizacao: Talhao Norte - Setor A
  timestamp: '2026-11-17T08:30:00-03:00'
  temperatura: 28.5
  unidade_temp: C
  umidade: 65.0
  luminosidade: 820
  precipitacao: 0.0
- sensor_id: SENS-US-02
  localizacao: Estufa Sul - Setor B
  timestamp: '2026-11-17T11:32:00Z'
  temperatura: 89.6
  unidade_temp: F
  umidade: 42.5
  luminosidade: 950
  precipitacao: null
```

### 6.4 CSV — `GET /api/leituras?formato=csv` (resposta completa)

```bash
curl "http://localhost:8000/api/leituras?formato=csv"
```
```csv
sensor_id;localizacao;timestamp;temperatura;unidade_temp;umidade;luminosidade;precipitacao
SENS-BR-01;Talhao Norte - Setor A;2026-11-17T08:30:00-03:00;28.5;C;65.0;820;0.0
SENS-US-02;Estufa Sul - Setor B;2026-11-17T11:32:00Z;89.6;F;42.5;950;
SENS-CH-03;Pomar Leste - Setor C;2026-11-17T06:35:00-05:00;-999.0;C;;410;12.4
SENS-US-04;Area Irrigada - Setor D;2026-11-17T08:40:00-03:00;104.0;F;18.0;1100;0.0
```
Separador `;`, primeira linha é o cabeçalho, **campo vazio = valor ausente**.

### 6.5 Protocol Buffer — `GET /api/leituras?formato=protobuf`

```bash
curl -s "http://localhost:8000/api/leituras?formato=protobuf" -o leituras.bin
```
Corpo binário codificado como `agro.ListaLeituras`. Decodificação em Python:

```python
import requests, sensor_pb2

resp = requests.get("http://localhost:8000/api/leituras", params={"formato": "protobuf"})
lista = sensor_pb2.ListaLeituras()
lista.ParseFromString(resp.content)

for l in lista.leituras:
    temp = f"{l.temperatura}°{l.unidade_temp}" if l.HasField("temperatura") else "AUSENTE"
    print(l.sensor_id, l.localizacao, temp, l.timestamp)
```

### 6.6 Serialização (pickle) — `GET /api/leituras?formato=serializacao`

```python
import requests, pickle

resp = requests.get("http://localhost:8000/api/leituras", params={"formato": "serializacao"})
leituras = pickle.loads(resp.content)   # lista de dicts Python
print(leituras[0]["sensor_id"])
```
> ⚠️ **Segurança:** `pickle.loads` executa código arbitrário se o dado vier de fonte não confiável. Aqui é aceitável porque o servidor é local e controlado por nós; **nunca** use `pickle` para dados de origem desconhecida. Só funciona com clientes Python.

### 6.7 Negociação por cabeçalho `Accept`

```bash
curl -H "Accept: application/x-yaml" http://localhost:8000/api/leituras
curl -H "Accept: text/csv"           http://localhost:8000/api/leituras
```

### 6.8 Erro — formato inválido

```bash
curl -i "http://localhost:8000/api/leituras?formato=txt"
# HTTP/1.1 422 Unprocessable Entity
```

---

## 7. Dados simulados (e o que o cliente deve tratar)

| `sensor_id` | Localização | Timestamp | Temperatura | Umidade | Luminosidade | Precipitação | Situação |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SENS-BR-01` | Talhao Norte - Setor A | `2026-11-17T08:30:00-03:00` | 28.5 °C | 65.0 | 820 | 0.0 | Leitura normal |
| `SENS-US-02` | Estufa Sul - Setor B | `2026-11-17T11:32:00Z` | 89.6 **°F** (= 32.0 °C) | 42.5 | 950 | **ausente** | °F + UTC + campo ausente |
| `SENS-CH-03` | Pomar Leste - Setor C | `2026-11-17T06:35:00-05:00` | **-999.0** (inválida) | **ausente** | 410 | 12.4 | Falha de hardware + fuso -05:00 |
| `SENS-US-04` | Area Irrigada - Setor D | `2026-11-17T08:40:00-03:00` | 104.0 **°F** (= 40.0 °C) | 18.0 | 1100 | 0.0 | °F + condição extrema (calor/seca) |

Os quatro timestamps caem na mesma janela (11:30–11:40 UTC), apenas escritos em fusos diferentes.

---

## 8. Como consumir (guia rápido para o Grupo B)

Combinado entre os grupos: o Grupo B pode usar **qualquer** dos 6 formatos. Pontos de atenção:

- **Temperatura:** converter °F → °C com `C = (F − 32) × 5/9` conforme `unidade_temp`.
- **Valores inválidos:** `-999.0` é código de erro de hardware, não uma temperatura real — descartar.
- **Fusos:** interpretar o offset do ISO 8601 e converter para um único fuso (ou UTC) antes de comparar ou ordenar. O sufixo `Z` equivale a `+00:00`.
- **Ausentes:** `null`/vazio/`HasField() == False` → não contar como `0` nas médias.
- **CSV:** separador `;`; campo vazio significa ausente; números usam ponto decimal.
- **Protobuf:** use `HasField("campo")` para detectar ausência; precisa do `sensor.proto`.

---

## 9. Clientes de teste incluídos

- **`cliente_teste.py`** — percorre os 6 formatos, imprime status HTTP, `Content-Type`, tamanho em bytes e o conteúdo decodificado.
  ```bash
  python cliente_teste.py
  ```
- **`interface.py`** — interface gráfica (Tkinter, já incluso no Python do Windows/macOS; no Linux pode exigir `sudo apt install python3-tk`). Um botão por formato: mostra status HTTP, `Content-Type`, tamanho e o conteúdo (bruto e decodificado nos binários).
  ```bash
  python interface.py
  ```

Ambos assumem o servidor em `http://localhost:8000`.

---

## 10. Comparação dos formatos

Tamanho do corpo da resposta para as **mesmas 4 leituras** (medido localmente com os dados deste repositório):

| Formato | Tamanho | Legível por humanos | Tipos explícitos | Representa ausência como | Observação |
| :--- | ---: | :---: | :---: | :--- | :--- |
| Protocol Buffer | **367 bytes** | ❌ | ✅ (schema) | Campo não preenchido (`HasField`) | Menor e mais rápido; exige `.proto` |
| CSV | 407 bytes | ✅ | ❌ (tudo texto) | Campo vazio | Simples e tabular; sem aninhamento nem tipos |
| Pickle | 560 bytes | ❌ | ✅ | `None` | Só Python; inseguro com dados não confiáveis |
| YAML | 797 bytes | ✅ | parcial | `null` | Muito legível; parsing mais lento |
| JSON | 1105 bytes | ✅ | parcial | `null` | Padrão da web; amplo suporte |
| XML | *varia (maior que JSON)* | ✅ | ❌ (tudo texto) | Tag vazia | Verboso; bom para validação (XSD) |

Você pode reproduzir as medições com `python cliente_teste.py`.

---

## 11. Problemas comuns

| Sintoma | Causa / solução |
| :--- | :--- |
| `ModuleNotFoundError: sensor_pb2` | Rode o comando de compilação do `.proto` (seção 3) a partir da pasta do projeto |
| `VersionError` / erro de runtime do protobuf ao importar `sensor_pb2` | Versão do `protobuf` instalada é mais antiga que a do código gerado: `pip install -U protobuf` ou recompile o `.proto` |
| `ModuleNotFoundError: fastapi` (ou `yaml`, `dicttoxml`…) | Execute `pip install -r requirements.txt` com o ambiente virtual ativo |
| `uvicorn: command not found` | Use `python -m uvicorn main:app --reload` |
| `Address already in use` (porta 8000) | Use outra porta: `uvicorn main:app --port 8001` |
| Cliente em outra máquina não conecta | Suba com `--host 0.0.0.0` e libere a porta 8000 no firewall |
| `422 Unprocessable Entity` | `formato` inválido; use um dos 6 valores da seção 5 |

---

## Equipe
Grupo A — preencha aqui os nomes dos integrantes.
