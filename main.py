from fastapi import FastAPI, Request, Response, Query
from enum import Enum
from typing import Optional
import json
import yaml
import csv
import io
import pickle
from dicttoxml import dicttoxml
import sensor_pb2

app = FastAPI(
    title="API Mock — Monitoramento Ambiental (Grupo A)",
    description="API de simulação de sensores agrícolas heterogêneos com suporte a múltiplos formatos de serialização e representação de dados.",
    version="1.0.0"
)

class FormatoEnum(str, Enum):
    json = "json"
    xml = "xml"
    yaml = "yaml"
    csv = "csv"
    protobuf = "protobuf"
    serializacao = "serializacao"

LEITURAS_SENSORES = [
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
        "precipitacao": None
    },
    {
        "sensor_id": "SENS-CH-03",
        "localizacao": "Pomar Leste - Setor C",
        "timestamp": "2026-11-17T06:35:00-05:00",
        "temperatura": -999.0,
        "unidade_temp": "C",
        "umidade": None,
        "luminosidade": 410,
        "precipitacao": 12.4
    },
    {
        "sensor_id": "SENS-US-04",
        "localizacao": "Area Irrigada - Setor D",
        "timestamp": "2026-11-17T08:40:00-03:00",
        "temperatura": 104.0,
        "unidade_temp": "F",
        "umidade": 18.0,
        "luminosidade": 1100,
        "precipitacao": 0.0
    }
]

EXEMPLOS_OPENAPI = {
    200: {
        "description": "Leituras retornadas no formato solicitado",
        "content": {
            "application/json": {
                "example": {"leituras": [LEITURAS_SENSORES[0]]}
            },
            "application/xml": {
                "example": "<monitoramento><leitura><sensor_id>SENS-BR-01</sensor_id><temperatura>28.5</temperatura></leitura></monitoramento>"
            },
            "application/x-yaml": {
                "example": "leituras:\n- sensor_id: SENS-BR-01\n  temperatura: 28.5\n  unidade_temp: C"
            },
            "text/csv": {
                "example": "sensor_id;localizacao;timestamp;temperatura;unidade_temp;umidade;luminosidade;precipitacao\nSENS-BR-01;Talhao Norte - Setor A;2026-11-17T08:30:00-03:00;28.5;C;65.0;820;0.0"
            },
            "application/x-protobuf": {
                "example": "Payload binário codificado segundo o esquema sensor.proto"
            },
            "application/octet-stream": {
                "example": "Stream de bytes gerado via Python pickle.dumps()"
            }
        }
    }
}

@app.get(
    "/api/leituras",
    summary="Obter leituras dos sensores",
    description="Retorna as medições simuladas. Escolha o formato pelo parâmetro `formato` ou pelo cabeçalho HTTP `Accept`.",
    responses=EXEMPLOS_OPENAPI
)
def listar_leituras(
    request: Request,
    formato: Optional[FormatoEnum] = Query(
        default=None,
        description="Formato desejado para representação dos dados (sobrescreve o header Accept)"
    )
):
    selecao = (formato.value if formato else request.headers.get("accept", "application/json")).lower()

    if "xml" in selecao:
        xml_bytes = dicttoxml(LEITURAS_SENSORES, custom_root="monitoramento", item_func=lambda x: "leitura", attr_type=False)
        return Response(content=xml_bytes, media_type="application/xml")

    elif "yaml" in selecao:
        yaml_str = yaml.dump({"leituras": LEITURAS_SENSORES}, allow_unicode=True, sort_keys=False)
        return Response(content=yaml_str, media_type="application/x-yaml")

    elif "csv" in selecao:
        output = io.StringIO()
        colunas = LEITURAS_SENSORES[0].keys()
        writer = csv.DictWriter(output, fieldnames=colunas, delimiter=";")
        writer.writeheader()
        writer.writerows(LEITURAS_SENSORES)
        return Response(content=output.getvalue(), media_type="text/csv")

    elif "protobuf" in selecao:
        lista_proto = sensor_pb2.ListaLeituras()
        for item in LEITURAS_SENSORES:
            leitura = lista_proto.leituras.add()
            leitura.sensor_id = item["sensor_id"]
            leitura.localizacao = item["localizacao"]
            leitura.timestamp = item["timestamp"]
            leitura.unidade_temp = item["unidade_temp"]
            if item["temperatura"] is not None:
                leitura.temperatura = item["temperatura"]
            if item["umidade"] is not None:
                leitura.umidade = item["umidade"]
            if item["luminosidade"] is not None:
                leitura.luminosidade = item["luminosidade"]
            if item["precipitacao"] is not None:
                leitura.precipitacao = item["precipitacao"]
        return Response(content=lista_proto.SerializeToString(), media_type="application/x-protobuf")

    elif "serializacao" in selecao or "octet-stream" in selecao:
        bytes_serializados = pickle.dumps(LEITURAS_SENSORES)
        return Response(content=bytes_serializados, media_type="application/octet-stream")

    return Response(
        content=json.dumps({"leituras": LEITURAS_SENSORES}, ensure_ascii=False, indent=2),
        media_type="application/json"
    )
