import requests
import pickle
import sensor_pb2

BASE_URL = "http://localhost:8000/api/leituras"

def testar_formatos():
    formatos = ["json", "xml", "yaml", "csv", "protobuf", "serializacao"]

    for fmt in formatos:
        print("=" * 60)
        print(f"TESTANDO FORMATO: {fmt.upper()}")
        
        resposta = requests.get(BASE_URL, params={"formato": fmt})
        tamanho_bytes = len(resposta.content)
        
        print(f"Status HTTP: {resposta.status_code} | Content-Type: {resposta.headers.get('content-type')}")
        print(f"Tamanho da resposta: {tamanho_bytes} bytes\n")

        # Decodificação específica para os formatos binários
        if fmt == "protobuf":
            lista_proto = sensor_pb2.ListaLeituras()
            lista_proto.ParseFromString(resposta.content)
            print("Dados decodificados do Protocol Buffer:")
            for leitura in lista_proto.leituras:
                temp = f"{leitura.temperatura}°{leitura.unidade_temp}" if leitura.HasField("temperatura") else "AUSENTE"
                print(f" -> Sensor: {leitura.sensor_id} | Local: {leitura.localizacao} | Temp: {temp} | Hora: {leitura.timestamp}")

        elif fmt == "serializacao":
            dados_obj = pickle.loads(resposta.content)
            print("Dados desserializados (Python Pickle):")
            for item in dados_obj:
                print(f" -> Sensor: {item['sensor_id']} | Temp: {item['temperatura']}°{item['unidade_temp']} | Umidade: {item['umidade']}")

        else:
            # Formatos textuais (JSON, XML, YAML, CSV)
            print("Conteúdo textual recebido:")
            print(resposta.text)

if __name__ == "__main__":
    testar_formatos()
