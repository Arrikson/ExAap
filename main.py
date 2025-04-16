from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel
from fastapi import Body
import shutil
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

PROFESSORES_JSON = "professores.json"
ALUNOS_JSON = "alunos.json"

# Verifica e cria alunos.json se não existir
if not os.path.exists(ALUNOS_JSON):
    with open(ALUNOS_JSON, "w", encoding="utf-8") as f:
        json.dump([], f)

# ----------------- FUNÇÕES AUXILIARES -----------------

def carregar_professores():
    if os.path.exists(PROFESSORES_JSON):
        with open(PROFESSORES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_professores(professores):
    with open(PROFESSORES_JSON, "w", encoding="utf-8") as f:
        json.dump(professores, f, ensure_ascii=False, indent=4)

def gerar_html_professores():
    professores = carregar_professores()
    conteudo_html = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <title>Professores Registrados</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f8f9fa;
                padding: 20px;
            }
            h1 {
                text-align: center;
                color: #343a40;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background-color: #fff;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                border: 1px solid #dee2e6;
                text-align: left;
            }
            th {
                background-color: #343a40;
                color: #fff;
            }
            tr:nth-child(even) {
                background-color: #f1f1f1;
            }
            img {
                max-width: 80px;
                border-radius: 8px;
            }
        </style>
    </head>
    <body>
        <h1>Lista de Professores Registrados</h1>
        <table>
            <tr>
                <th>Foto</th>
                <th>Nome</th>
                <th>BI</th>
                <th>Email</th>
                <th>Telefone</th>
                <th>Localização</th>
            </tr>
    """
    for p in professores:
        foto_html = f'<img src="{p["doc_foto"]}" alt="Foto">' if "doc_foto" in p else "N/A"
        conteudo_html += f"""
            <tr>
                <td>{foto_html}</td>
                <td>{p.get("nome", "")}</td>
                <td>{p.get("bi", "")}</td>
                <td>{p.get("email", "")}</td>
                <td>{p.get("telefone", "")}</td>
                <td>{p.get("localizacao", "")}</td>
            </tr>
        """
    conteudo_html += "</table></body></html>"
    with open("templates/pro-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo_html)

def carregar_alunos():
    if os.path.exists(ALUNOS_JSON):
        with open(ALUNOS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_alunos(alunos):
    with open(ALUNOS_JSON, "w", encoding="utf-8") as f:
        json.dump(alunos, f, ensure_ascii=False, indent=4)

def gerar_html_alunos():
    alunos = carregar_alunos()
    conteudo_html = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <title>Alunos Registrados</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f8f9fa;
                padding: 20px;
            }
            h1 {
                text-align: center;
                color: #343a40;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background-color: #fff;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                border: 1px solid #dee2e6;
                text-align: left;
            }
            th {
                background-color: #343a40;
                color: #fff;
            }
            tr:nth-child(even) {
                background-color: #f1f1f1;
            }
        </style>
    </head>
    <body>
        <h1>Lista de Alunos Registrados</h1>
        <table>
            <tr>
                <th>Nome</th>
                <th>BI</th>
                <th>Idade</th>
                <th>Classe</th>
                <th>Nome do Pai</th>
                <th>Nome da Mãe</th>
                <th>Disciplinas</th>
                <th>Localização</th>
            </tr>
    """
    for a in alunos:
        conteudo_html += f"""
            <tr>
                <td>{a.get("name", "")}</td>
                <td>{a.get("bi", "")}</td>
                <td>{a.get("age", "")}</td>
                <td>{a.get("class", "")}</td>
                <td>{a.get("father_name", "")}</td>
                <td>{a.get("mother_name", "")}</td>
                <td>{", ".join(a.get("disciplinas", []))}</td>
                <td>{a.get("localizacao", "")}</td>
            </tr>
        """
    conteudo_html += "</table></body></html>"
    with open("templates/aluno-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo_html)

# ----------------- ROTAS -----------------

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

@app.get("/aluno-info.html", response_class=HTMLResponse)
async def mostrar_alunos_estatico(request: Request):
    return templates.TemplateResponse("aluno-info.html", {"request": request})

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

    novo_aluno = {
        "name": name,
        "bi": bi,
        "age": age,
        "class": class_,
        "father_name": father_name,
        "mother_name": mother_name,
        "disciplinas": disciplinas,
        "localizacao": f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
    }

    alunos = carregar_alunos()
    alunos.append(novo_aluno)
    salvar_alunos(alunos)
    gerar_html_alunos()

    return templates.TemplateResponse("registro.aluno.html", {"request": request, "dados": novo_aluno})

@app.post("/api/alunos", response_class=JSONResponse)
async def receber_aluno_api(aluno: dict):
    alunos = carregar_alunos()
    alunos.append(aluno)
    salvar_alunos(alunos)
    gerar_html_alunos()
    return {"message": "Aluno registrado com sucesso"}

@app.get("/api/alunos")
async def listar_alunos():
    alunos = carregar_alunos()
    return JSONResponse(content=alunos)

@app.get("/info-p.html", response_class=HTMLResponse)
async def mostrar_professores(request: Request):
    professores = carregar_professores()
    return templates.TemplateResponse("info-p.html", {"request": request, "professores": professores})

@app.post("/excluir-professor/{bi}")
async def excluir_professor(bi: str):
    global professores
    professores = [p for p in professores if p["bi"] != bi]
    salvar_professores(professores)
    gerar_html_professores()
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
async def mostrar_professores_estatico(request: Request):
    return templates.TemplateResponse("pro-info.html", {"request": request})

@app.get("/dados-professor.html", response_class=HTMLResponse)
async def dados_professor(request: Request):
    return templates.TemplateResponse("dados-professor.html", {"request": request})

@app.post("/api/professores", response_class=JSONResponse)
async def receber_professor_api(professor: dict = Body(...)):
    professores = carregar_professores()
    professores.append(professor)
    salvar_professores(professores)
    gerar_html_professores()
    return {"message": "Professor registrado com sucesso"}

@app.get("/api/professores")
def listar_professores():
    professores = carregar_professores()
    return JSONResponse(content=professores)

@app.post("/registrar-professor", response_class=HTMLResponse)
async def registrar_professor(
    request: Request,
    nome: str = Form(...),
    bi: int = Form(...),
    email: str = Form(...),
    telefone: str = Form(...),
    doc_foto: UploadFile = File(...),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    foto_path = f"static/{doc_foto.filename}"
    with open(foto_path, "wb") as buffer:
        shutil.copyfileobj(doc_foto.file, buffer)

    novo_professor = {
        "nome": nome,
        "bi": bi,
        "email": email,
        "telefone": telefone,
        "doc_foto": foto_path,
        "localizacao": f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
    }

    professores = carregar_professores()
    professores.append(novo_professor)
    salvar_professores(professores)
    gerar_html_professores()

    return templates.TemplateResponse("registro.professor.html", {"request": request, "dados": novo_professor})

