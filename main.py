from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    discipline: list[str] = Form([]),
    other_discipline: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    # Junta todas as disciplinas
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


