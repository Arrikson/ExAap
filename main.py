from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
import os
import json

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Caminho do arquivo JSON
PROFESSORES_JSON = "professores.json"

# Função para carregar os dados do arquivo JSON
def carregar_professores():
    if os.path.exists(PROFESSORES_JSON):
        with open(PROFESSORES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Função para salvar os dados no arquivo JSON
def salvar_professores(professores):
    with open(PROFESSORES_JSON, "w", encoding="utf-8") as f:
        json.dump(professores, f, ensure_ascii=False, indent=4)

# Lista em memória inicial
professores = carregar_professores()

# ROTAS:

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/criar-conta", response_class=HTMLResponse)
async def criar_conta(request: Request):
    return templates.TemplateResponse("criar-conta.html", {"request": request})

@app.get("/quero-aulas", response_class=HTMLResponse)
async def quero_aulas(request: Request):
    return templates.TemplateResponse("quero-aulas.html", {"request": request})

@app.get("/dados-aluno", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("dados-aluno.html", {"request": request})

@app.get("/precos", response_class=HTMLResponse)
async def ver_precos(request: Request):
    return templates.TemplateResponse("precos.html", {"request": request})

@app.get("/aulaonline", response_class=HTMLResponse)
async def aula_online(request: Request):
    return templates.TemplateResponse("aulaonline.html", {"request": request})

@app.post("/registrar-aluno", response_class=HTMLResponse)
async def registrar_aluno(
    request: Request,
    name: str = Form(...),
    bi: int = Form(...),
    age: int = Form(...),
    class_: str = Form(..., alias="class"),
    father_name: str = Form(..., alias="father-name"),
    mother_name: str = Form(..., alias="mother-name"),
    discipline: List[str] = Form([]),
    other_discipline: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    disciplinas = discipline
    if other_discipline:
        disciplinas.append(other_discipline)

    dados = {
        "name": name,
        "bi": bi,
        "age": age,
        "class": class_,
        "father_name": father_name,
        "mother_name": mother_name,
        "disciplinas": disciplinas,
        "localizacao": f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
    }

    return templates.TemplateResponse("registro.aluno.html", {"request": request, "dados": dados})

@app.get("/info-p.html", response_class=HTMLResponse)
async def mostrar_professores(request: Request):
    professores = carregar_professores()  # Aqui carrega os dados do JSON
    return templates.TemplateResponse("info-p.html", {"request": request, "professores": professores})

@app.post("/excluir-professor/{bi}")
async def excluir_professor(bi: str):
    global professores
    professores = [p for p in professores if p["bi"] != bi]
    salvar_professores(professores)
    return RedirectResponse(url="/info-p", status_code=303)

@app.get("/editar-professor/{bi}", response_class=HTMLResponse)
async def editar_professor_form(bi: str, request: Request):
    professor = next((p for p in professores if p["bi"] == bi), None)
    if not professor:
        return HTMLResponse("Professor não encontrado", status_code=404)
    
    return templates.TemplateResponse("editar-professor.html", {
        "request": request,
        "professor": professor
    })

@app.get("/pro-info.html", response_class=HTMLResponse)
async def mostrar_professores(request: Request):
    # Carrega os dados dos professores a partir do arquivo JSON
    professores = carregar_professores()

    # Renderiza a página pro-info.html com os dados dos professores
    return templates.TemplateResponse("pro-info.html", {"request": request, "professores": professores})

@app.get("/dados-professor.html", response_class=HTMLResponse)
async def dados_professor(request: Request):
    return templates.TemplateResponse("dados-professor.html", {"request": request})

@app.get("/api/professores", response_class=JSONResponse)
async def api_professores():
    professores = carregar_professores()
    return professores

@app.post("/registrar-professor", response_class=HTMLResponse)
async def registrar_professor(
    request: Request,
    nome: str = Form(...),
    bi: str = Form(...),
    habilitacao: str = Form(...),
    licenciatura_area: Optional[str] = Form(""),
    disciplinas: List[str] = Form([]),
    outras_disciplinas: Optional[str] = Form(""),
    telefone: str = Form(...),
    email: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    doc_foto: UploadFile = File(...),
    doc_pdf: UploadFile = File(...)
):
    # Lê a lista de professores existentes
    professores = carregar_professores()

    # Define os caminhos para os documentos
    foto_path = f"static/docs/{doc_foto.filename}"
    pdf_path = f"static/docs/{doc_pdf.filename}"
    os.makedirs("static/docs", exist_ok=True)

    with open(foto_path, "wb") as buffer:
        shutil.copyfileobj(doc_foto.file, buffer)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(doc_pdf.file, buffer)

    # Adiciona o novo professor à lista
    novo_professor = {
        "nome": nome,
        "bi": bi,
        "habilitacao": habilitacao,
        "licenciatura_area": licenciatura_area,
        "disciplinas": disciplinas,
        "outras_disciplinas": outras_disciplinas,
        "telefone": telefone,
        "email": email,
        "localizacao": f"Latitude: {latitude}, Longitude: {longitude}",
        "doc_foto": "/" + foto_path,
        "doc_pdf": "/" + pdf_path
    }

    professores.append(novo_professor)

    # Salva os dados no arquivo JSON
    salvar_professores(professores)

    return RedirectResponse(url="/pro-info.html", status_code=303)

