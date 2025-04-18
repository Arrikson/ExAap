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
from fastapi.responses import Response, FileResponse
from fpdf import FPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PDF = os.path.join(BASE_DIR, "static", "docs", "lista_alunos.pdf")
CAMINHO_JSON = os.path.join(BASE_DIR, "alunos.json")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

PROFESSORES_JSON = "professores.json"
ALUNOS_JSON = "alunos.json"

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

    conteudo_html += """
        </table>
    </body>
    </html>
    """

    with open("templates/pro-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo_html)

# Carregamento inicial
professores = carregar_professores()

class Aluno(BaseModel):
    nome: str
    bi: str
    idade: int
    classe: str
    pai: str
    mae: str
    disciplinas: List[str]
    localizacao: str

def carregar_alunos():
    if os.path.exists(CAMINHO_JSON):
        with open(CAMINHO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_alunos(alunos):
    with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
        json.dump(alunos, f, ensure_ascii=False, indent=4)

def gerar_pdf_individual(aluno):
    nome_arquivo = f"static/docs/{aluno['nome'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "Ficha de Inscrição de Aluno")
    y -= 40

    c.setFont("Helvetica", 12)
    campos = [
        ("Nome", aluno["nome"]),
        ("B.I.", aluno["bi"]),
        ("Idade", str(aluno["idade"])),
        ("Classe", aluno["classe"]),
        ("Pai", aluno["pai"]),
        ("Mãe", aluno["mae"]),
        ("Disciplinas", ", ".join(aluno["disciplinas"])),
        ("Localização", aluno["localizacao"]),
    ]

    for label, valor in campos:
        c.drawString(50, y, f"{label}: {valor}")
        y -= 20

    c.save()
    return nome_arquivo

@app.get("/dados-alunos")
async def get_alunos():
    return carregar_alunos()

# Rota POST para enviar os dados do formulário
@app.post("/enviar-dados")
async def enviar_dados(
    name: str = Form(...),
    bi: int = Form(...),
    age: int = Form(...),
    class_: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    discipline: List[str] = Form(...),
    other_discipline: str = Form(None)
):
    # Criar um objeto Aluno com os dados recebidos
    aluno = Aluno(
        name=name,
        bi=bi,
        age=age,
        class_=class_,
        father_name=father_name,
        mother_name=mother_name,
        latitude=latitude,
        longitude=longitude,
        discipline=discipline,
        other_discipline=other_discipline
    )

    # Carregar os alunos atuais
    alunos = carregar_alunos()

    # Adicionar o novo aluno à lista
    alunos.append(aluno.dict())

    # Salvar a lista de alunos no arquivo JSON
    salvar_alunos(alunos)

    return {"message": "Dados enviados com sucesso!"}

@app.get("/info-alunos", response_class=HTMLResponse)
async def info_alunos(request: Request):
    dados = carregar_alunos()
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": dados})

@app.get("/registrar-aluno", response_class=HTMLResponse)
async def form_aluno(request: Request):
    return templates.TemplateResponse("registrar-aluno.html", {"request": request})

@app.post("/registrar-aluno", response_class=HTMLResponse)
async def registrar_aluno(
    request: Request,
    nome: str = Form(...),
    bi: str = Form(...),
    idade: int = Form(...),
    classe: str = Form(...),
    pai: str = Form(...),
    mae: str = Form(...),
    disciplinas: Annotated[List[str], Form()] = [],
    outra_disciplina: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    if outra_disciplina:
        disciplinas.append(outra_disciplina)

    localizacao = f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"

    novo_aluno = {
        "nome": nome,
        "bi": bi,
        "idade": idade,
        "classe": classe,
        "pai": pai,
        "mae": mae,
        "disciplinas": disciplinas,
        "localizacao": localizacao
    }

    alunos = carregar_alunos()
    alunos.append(novo_aluno)
    salvar_alunos(alunos)

    caminho_pdf = gerar_pdf_individual(novo_aluno)

    return FileResponse(caminho_pdf, media_type="application/pdf", filename=os.path.basename(caminho_pdf))

@app.get("/info-a.html", response_class=HTMLResponse)
async def mostrar_alunos(request: Request):
    alunos = carregar_alunos()
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": alunos})

def carregar_alunos():
    with open("alunos.json", "r", encoding="utf-8") as file:
        return json.load(file)

@app.get("/gerar-pdf-alunos")
async def gerar_pdf_alunos():
    alunos = carregar_alunos()  # função que lê do alunos.json

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Lista de Alunos Registrados", ln=True, align="C")
    pdf.ln(10)

    for aluno in alunos:
        pdf.cell(200, 10, txt=f"Nome: {aluno['nome']}", ln=True)
        pdf.cell(200, 10, txt=f"BI: {aluno['bi']}", ln=True)
        pdf.cell(200, 10, txt=f"Idade: {aluno['idade']}", ln=True)
        pdf.cell(200, 10, txt=f"Classe: {aluno['classe']}", ln=True)
        pdf.cell(200, 10, txt=f"Pai: {aluno['pai']}", ln=True)
        pdf.cell(200, 10, txt=f"Mãe: {aluno['mae']}", ln=True)
        pdf.cell(200, 10, txt=f"Disciplinas: {', '.join(aluno['disciplinas'])}", ln=True)
        pdf.cell(200, 10, txt=f"Localização: {aluno['localizacao']}", ln=True)
        pdf.ln(10)

    nome_arquivo = "alunos_registrados.pdf"
    caminho_arquivo = os.path.join("static", nome_arquivo)
    pdf.output(caminho_arquivo)

    return FileResponse(path=caminho_arquivo, filename=nome_arquivo, media_type="application/pdf")
    
 # Cadastro do aluno
@app.post("/registrar-aluno", response_class=HTMLResponse)
async def registrar_aluno(
    request: Request,
    nome: str = Form(...),
    bi: str = Form(...),
    idade: int = Form(...),
    classe: str = Form(...),
    pai: str = Form(...),
    mae: str = Form(...),
    disciplinas: Annotated[List[str], Form()] = [],
    outra_disciplina: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    todas_disciplinas = disciplinas
    if outra_disciplina:
        todas_disciplinas.append(outra_disciplina)

    dados = {
        "nome": nome,
        "bi": bi,
        "idade": idade,
        "classe": classe,
        "pai": pai,
        "mae": mae,
        "disciplinas": todas_disciplinas,
        "localizacao": f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
    }

    alunos = carregar_alunos()
    alunos.append(dados)
    salvar_alunos(alunos)

    # Gera o contrato HTML para exibição
    contrato_html = gerar_html_contrato(nome, pai, mae)

    return templates.TemplateResponse("aluno-info.html", {
        "request": request,
        "dados": dados,
        "contrato": contrato_html,
        "now": datetime.now()
    })

@app.get("/dados-alunos") 
async def get_alunos():
    # Caminho para o arquivo JSON dos alunos
    with open("alunos.json", "r") as file:
        alunos_data = json.load(file)
    return alunos_data;       

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("dados-aluno.html", {"request": request})

@app.post("/enviar-dados")
async def enviar_dados(
    name: str = Form(...),
    bi: int = Form(...),
    age: int = Form(...),
    class_: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    latitude: str = Form(""),
    longitude: str = Form(""),
    discipline: list[str] = Form([]),
    other_discipline: str = Form("")
):
    try:
        disciplinas = discipline.copy()
        if other_discipline:
            disciplinas.append(other_discipline)

        novo_aluno = {
            "name": name,
            "bi": bi,
            "age": age,
            "class": class_,
            "father_name": father_name,
            "mother_name": mother_name,
            "latitude": latitude,
            "longitude": longitude,
            "disciplines": disciplinas,
            "created_at": datetime.now().isoformat()
        }

        # Lê os dados existentes
        if os.path.exists(ALUNOS_JSON_PATH):
            with open(ALUNOS_JSON_PATH, "r", encoding="utf-8") as f:
                dados_existentes = json.load(f)
        else:
            dados_existentes = []

        # Adiciona o novo aluno
        dados_existentes.append(novo_aluno)

        # Salva novamente o arquivo
        with open(ALUNOS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(dados_existentes, f, ensure_ascii=False, indent=4)

        return templates.TemplateResponse("aluno-info.html", {"request": Request, "aluno": novo_aluno})

    except Exception as e:
        return HTMLResponse(content=f"Erro ao salvar dados: {str(e)}", status_code=500)
    
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

# Definição do modelo para os dados dos alunos
class Aluno(BaseModel):
    nome: str
    bi: str
    idade: int
    classe: str
    pai: str
    mae: str
    disciplinas: List[str]
    localizacao: str

# Função para carregar os dados dos alunos de um arquivo JSON
def carregar_dados_alunos():
    arquivo_alunos = Path("dados-alunos.json")
    if arquivo_alunos.exists():
        with open(arquivo_alunos, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return [Aluno(**aluno) for aluno in dados]  # Retorna uma lista de objetos Aluno
    return []

# Rota para exibir a lista de alunos na página info-alunos.html
@app.get("/info-alunos", response_class=HTMLResponse)
async def info_alunos(request: Request):
    alunos = carregar_dados_alunos()  # Carrega os dados dos alunos
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": alunos, "now": datetime.datetime.now()})


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
    professores = carregar_professores()

    # Diretório para armazenar os arquivos
    os.makedirs("static/docs", exist_ok=True)

    # Caminhos para salvar as fotos e PDFs
    foto_path = f"static/docs/{doc_foto.filename}"
    pdf_path = f"static/docs/{doc_pdf.filename}"

    # Salvar as fotos e PDFs no diretório
    with open(foto_path, "wb") as buffer:
        shutil.copyfileobj(doc_foto.file, buffer)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(doc_pdf.file, buffer)

    # Registrar as informações do professor
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
        "doc_foto": "/" + foto_path,  # Caminho relativo para a foto
        "doc_pdf": "/" + pdf_path     # Caminho relativo para o PDF
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
            ("BI", p.get("bi", "")),
            ("Habilitações", p.get("habilitacao", "")),
            ("Área da Licenciatura", p.get("licenciatura_area", "")),
            ("Disciplinas", ", ".join(p.get("disciplinas", []))),
            ("Outras Disciplinas", p.get("outras_disciplinas", "")),
            ("Telefone", p.get("telefone", "")),
            ("Email", p.get("email", "")),
            ("Localização", p.get("localizacao", "")),
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
