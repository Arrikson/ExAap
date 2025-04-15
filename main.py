from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
import os

app = FastAPI()

# Conecta as pastas de arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Página inicial com os links corrigidos
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Página de criar conta
@app.get("/criar-conta", response_class=HTMLResponse)
async def criar_conta(request: Request):
    return templates.TemplateResponse("criar-conta.html", {"request": request})

# Página de solicitação de aulas
@app.get("/quero-aulas", response_class=HTMLResponse)
async def quero_aulas(request: Request):
    return templates.TemplateResponse("quero-aulas.html", {"request": request})

# Página com formulário de dados do aluno
@app.get("/dados-aluno", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("dados-aluno.html", {"request": request})

@app.get("/precos", response_class=HTMLResponse)
async def ver_precos(request: Request):
    return templates.TemplateResponse("precos.html", {"request": request})

@app.get("/aulaonline", response_class=HTMLResponse)
async def aula_online(request: Request):
    return templates.TemplateResponse("aulaonline.html", {"request": request})

# Processamento dos dados do aluno
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

# Página com formulário de dados do professor
@app.get("/dados-professor", response_class=HTMLResponse)
async def get_form_professor(request: Request):
    return templates.TemplateResponse("dados-professor.html", {"request": request})

# Processamento dos dados do professor
@app.post("/registrar-professor")
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
    # Salvando os arquivos enviados
    foto_path = f"static/docs/{doc_foto.filename}"
    pdf_path = f"static/docs/{doc_pdf.filename}"

    os.makedirs("static/docs", exist_ok=True)

    with open(foto_path, "wb") as buffer:
        shutil.copyfileobj(doc_foto.file, buffer)

    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(doc_pdf.file, buffer)

    # Você pode salvar os dados no banco de dados aqui se desejar

    # Redirecionar para a página inicial
    return RedirectResponse(url="/", status_code=303)
