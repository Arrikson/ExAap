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
from datetime import datetime
from typing import List, Optional, Annotated
from fpdf import FPDF
from pathlib import Path
from weasyprint import HTML

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

PROFESSORES_JSON = "professores.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PDF = os.path.join(BASE_DIR, "static", "docs", "lista_alunos.pdf")
CAMINHO_JSON = os.path.join(BASE_DIR, "alunos.json")

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
                <th>Data de Nascimento</th>
                <th>Idade</th>
                <th>Nome do Pai</th>
                <th>Nome da Mãe</th>
                <th>Morada</th>
                <th>Referência</th>
                <th>Disciplinas</th>
                <th>Outra Disciplina</th>
                <th>Localização</th>
            </tr>
    """

    for p in professores:
        localizacao = f"{p.get('latitude', '')}, {p.get('longitude', '')}"
        conteudo_html += f"""
           <tr>
                <td>{p.get("nome_completo", "")}</td>
                <td>{p.get("data_nascimento", "")}</td>
                <td>{p.get("idade", "")}</td>
                <td>{p.get("nome_pai", "")}</td>
                <td>{p.get("nome_mae", "")}</td>
                <td>{p.get("morada", "")}</td>
                <td>{p.get("referencia", "")}</td>
                <td>{p.get("disciplinas", "")}</td>
                <td>{p.get("outra_disciplina", "")}</td>
                <td>{localizacao}</td>
            </tr>
        """

    conteudo_html += """
        </table>
    </body>
    </html>
    """

    with open("templates/pro-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo_html)

# Carregamento inicial
professores = carregar_professores()

@app.post("/cadastrar-aluno", response_class=HTMLResponse)
async def cadastrar_aluno(
    request: Request,
    nome_completo: str = Form(...),
    data_nascimento: str = Form(...),
    idade: int = Form(...),
    nome_pai: str = Form(...),
    nome_mae: str = Form(...),
    morada: str = Form(...),
    referencia: str = Form(...),
    disciplinas: str = Form(...),
    outra_disciplina: Optional[str] = Form(""),
    latitude: str = Form(...),
    longitude: str = Form(...)
):
    professores = carregar_professores()

    novo_aluno = {
        "nome_completo": nome_completo,
        "data_nascimento": data_nascimento,
        "idade": idade,
        "nome_pai": nome_pai,
        "nome_mae": nome_mae,
        "morada": morada,
        "referencia": referencia,
        "disciplinas": disciplinas,
        "outra_disciplina": outra_disciplina,
        "latitude": latitude,
        "longitude": longitude
    }

    professores.append(novo_aluno)
    salvar_professores(professores)

    return RedirectResponse(url="/pro-info.html", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/criar-conta", response_class=HTMLResponse)
async def criar_conta(request: Request):
    return templates.TemplateResponse("criar-conta.html", {"request": request})

@app.get("/quero-aulas", response_class=HTMLResponse)
async def quero_aulas(request: Request):
    return templates.TemplateResponse("quero-aulas.html", {"request": request})

@app.get("/precos", response_class=HTMLResponse)
async def ver_precos(request: Request):
    return templates.TemplateResponse("precos.html", {"request": request})

@app.get("/aulaonline", response_class=HTMLResponse)
async def aula_online(request: Request):
    return templates.TemplateResponse("aulaonline.html", {"request": request})

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
        return HTMLResponse("Aluno não encontrado", status_code=404)
    
    return templates.TemplateResponse("editar-professor.html", {
        "request": request,
        "professor": professor
    })

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
    nome_completo: str = Form(...),
    data_nascimento: str = Form(...),
    idade: int = Form(...),
    nome_pai: str = Form(...),
    nome_mae: str = Form(...),
    morada: str = Form(...),
    referencia: str = Form(...),
    disciplinas: str = Form(...),  # string separada por vírgula
    outra_disciplina: Optional[str] = Form(""),
    latitude: str = Form(...),
    longitude: str = Form(...)
):
    professores = carregar_professores()

    novo_professor = {
        "nome_completo": nome_completo,
        "data_nascimento": data_nascimento,
        "idade": idade,
        "nome_pai": nome_pai,
        "nome_mae": nome_mae,
        "morada": morada,
        "referencia": referencia,
        "disciplinas": disciplinas,
        "outra_disciplina": outra_disciplina,
        "latitude": latitude,
        "longitude": longitude
    }

    professores.append(novo_professor)
    salvar_professores(professores)
    gerar_html_professores()

    return RedirectResponse(url="/pro-info.html", status_code=303)

    # Registrar as informações do professor
    novo_professor = {
        "nome_completo": nome_completo,
        "data_nascimento": data_nascimento,
        "idade": idade,
        "nome_pai": nome_pai,
        "nome_mae": nome_mae,
        "morada": morada,
        "referencia": referencia,
        "disciplinas": disciplinas,
        "outra_disciplina": outra_disciplina,
        "latitude": latitude,
        "longitude": longitude
    }

    professores.append(novo_professor)
    salvar_professores(professores)
    gerar_html_professores()

    return RedirectResponse(url="/pro-info.html", status_code=303)

@app.get("/gerar-pdf", response_class=FileResponse)
async def gerar_pdf():
    from reportlab.lib.units import cm
    from datetime import datetime
    from reportlab.lib import colors
    from reportlab.platypus import Image as RLImage

    professores = carregar_professores()
    os.makedirs("static/docs", exist_ok=True)
    pdf_path = "static/docs/lista_professores.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)

    width, height = A4
    y = height - 80

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 50, "Novos Professores Cadastrados")

    # Data no canto superior direito
    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 30, f"Data: {data_hoje}")

    for i, p in enumerate(professores):
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.darkblue)
        c.drawString(50, y, f"{i + 1}. {p.get('nome', 'Sem nome')}")
        y -= 20

        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)

        campos = [
            ("Data de Nascimento", aluno.get("data_nascimento", "")),
            ("Idade", str(aluno.get("idade", ""))),
            ("Nome do Pai", aluno.get("nome_pai", "")),
            ("Nome da Mãe", aluno.get("nome_mae", "")),
            ("Morada", aluno.get("morada", "")),
            ("Referência", aluno.get("referencia", "")),
            ("Disciplinas", aluno.get("disciplinas", "")),
            ("Outra Disciplina", aluno.get("outra_disciplina", "")),
            ("Latitude", aluno.get("latitude", "")),
            ("Longitude", aluno.get("longitude", ""))
        ]

        for label, valor in campos:
            if valor:
                c.drawString(60, y, f"{label}: {valor}")
                y -= 15

        # Adicionar imagem, se disponível
        foto_path = p.get("doc_foto", "").lstrip("/")
        if foto_path and os.path.exists(foto_path):
            try:
                c.drawImage(foto_path, width - 6.5*cm, y - 5*cm, width=5.5*cm, height=5.5*cm, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Erro ao adicionar foto: {e}")
                c.drawString(60, y, "Erro ao carregar imagem.")
        y -= 100

        # Linha separadora
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.line(50, y, width - 50, y)
        y -= 30

        if y < 150:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width / 2, height - 50, "Novos Professores Cadastrados")
            c.setFont("Helvetica", 10)
            c.drawRightString(width - 50, height - 30, f"Data: {data_hoje}")

    c.save()
    return FileResponse(pdf_path, media_type="application/pdf", filename="lista_professores.pdf")
