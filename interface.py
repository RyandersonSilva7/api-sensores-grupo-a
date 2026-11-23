import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import pickle
import sensor_pb2

API_URL = "http://localhost:8000/api/leituras"


def buscar_api(formato):
    try:
        return requests.get(API_URL, params={"formato": formato}, timeout=5)
    except Exception as e:
        messagebox.showerror("Erro de Conexão", f"Verifique se o uvicorn está rodando.\nDetalhe: {e}")
        return None


def testar_formato(formato):
    resp = buscar_api(formato)
    if not resp:
        return
    lbl_info.config(text=f"Status: {resp.status_code} | Content-Type: {resp.headers.get('content-type')} | Tamanho: {len(resp.content)} bytes")
    txt_a.delete("1.0", tk.END)
    if formato == "protobuf":
        lista = sensor_pb2.ListaLeituras()
        lista.ParseFromString(resp.content)
        txt_a.insert(tk.END, f"BINÁRIO ({len(resp.content)} bytes):\n{resp.content}\n\nDECODIFICADO:\n")
        for l in lista.leituras:
            temp = f"{l.temperatura}°{l.unidade_temp}" if l.HasField("temperatura") else "AUSENTE"
            txt_a.insert(tk.END, f"{l.sensor_id} | {l.localizacao} | Temp: {temp} | Hora: {l.timestamp}\n")
    elif formato == "serializacao":
        txt_a.insert(tk.END, f"BINÁRIO ({len(resp.content)} bytes):\n{resp.content}\n\nDESSERIALIZADO:\n{pickle.loads(resp.content)}")
    else:
        txt_a.insert(tk.END, resp.text)


root = tk.Tk()
root.title("Estudo de Caso 1 - Grupo A: Inspetor de Formatos da API Mock")
root.geometry("880x580")

frame = ttk.Frame(root, padding=10)
frame.pack(fill="both", expand=True)

fr_btn = tk.Frame(frame)
fr_btn.pack(fill="x")
for nome, fmt in [("JSON", "json"), ("XML", "xml"), ("YAML", "yaml"), ("CSV", "csv"), ("Protobuf", "protobuf"), ("Pickle", "serializacao")]:
    ttk.Button(fr_btn, text=nome, command=lambda f=fmt: testar_formato(f)).pack(side="left", expand=True, fill="x", padx=2)

lbl_info = tk.Label(frame, text="Clique em um formato acima...", font=("Segoe UI", 9, "bold"), fg="#0052cc")
lbl_info.pack(anchor="w", pady=6)
txt_a = scrolledtext.ScrolledText(frame, font=("Consolas", 10))
txt_a.pack(fill="both", expand=True)

root.mainloop()
