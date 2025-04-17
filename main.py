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

ALUNOS_JSON = "alunos.json"

# Função para carregar os alunos
def carregar_alunos():
    try:
        with open(ALUNOS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Função para salvar os alunos
def salvar_alunos(alunos):
    with open(ALUNOS_JSON, "w", encoding="utf-8") as f:
        json.dump(alunos, f, ensure_ascii=False, indent=4)

# Placeholder para uso futuro
def gerar_html_alunos():
    pass

# Função que gera o HTML do contrato
def gerar_html_contrato(nome="Aluno(a)", nome_pai="Pai", nome_mae="Mãe"):
    html = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <title>Contrato de Prestação de Serviços</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f8f9fa; }}
            .container {{ background: #fff; padding: 20px; border-radius: 12px; max-width: 600px; margin: 0 auto; box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1); }}
            h2 {{ text-align: center; color: #2e86de; }}
            p, li {{ font-size: 14px; line-height: 1.6; }}
            ol {{ padding-left: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Contrato de Prestação de Serviços</h2>
            <p><strong>Aluno(a):</strong> {nome}</p>
            <p><strong>Responsável (Pai):</strong> {nome_pai}</p>
            <p><strong>Responsável (Mãe):</strong> {nome_mae}</p>
            <ol>
                <li><strong>Objeto do contrato:</strong><br> Prestação de serviços de auxílio escolar ao(a) aluno(a) acima mencionado(a), com aulas de explicação domiciliar.</li>
                <li><strong>Duração:</strong><br> Inicial de 3 meses, renovável automaticamente.</li>
                <li><strong>Valor:</strong><br> 24.900,00 Kz/mês. Pagamento até o último dia do mês. Após 10 dias de atraso: juros de 10% na conta BAI nº 282309786 10 001.</li>
                <li><strong>Professor:</strong><br> Substituível sem custo caso não atenda às expectativas.</li>
                <li><strong>Má conduta:</strong><br> O professor será responsabilizado legalmente.</li>
                <li><strong>Leis:</strong><br> Regido pelas leis da República de Angola.</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return html
    
# Geração do PDF do contrato
@app.get("/gerar-pdf", response_class=Response)
async def gerar_pdf():
    # Dados fictícios ou últimos dados cadastrados (melhorar depois)
    alunos = carregar_alunos()
    if not alunos:
        return Response(content="Nenhum aluno cadastrado.", status_code=404)

    ultimo = alunos[-1]
    html = gerar_html_contrato(ultimo.get("nome", ""), ultimo.get("pai", ""), ultimo.get("mae", ""))
    pdf = HTML(string=html).write_pdf()

    response = Response(content=pdf, media_type="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=contrato.pdf"
    return response

# Rota da página de registro
@app.get("/registrar-aluno", response_class=HTMLResponse)
async def form_aluno(request: Request):
    return templates.TemplateResponse("registrar-aluno.html", {"request": request})

@app.get("/info-a.html", response_class=HTMLResponse)
async def mostrar_alunos(request: Request):
    alunos = carregar_alunos()
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": alunos})

# Gerar lista de alunos em PDF
@app.get("/gerar-pdf-alunos/download", response_class=FileResponse)
async def baixar_pdf_alunos():
    alunos = carregar_alunos()
    os.makedirs("static/docs", exist_ok=True)
    pdf_path = "static/docs/lista_alunos.pdf"

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 80

    titulo = "Novos Alunos Cadastrados"
    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    def desenhar_cabecalho():
        nonlocal y
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#2e86de"))
        c.drawCentredString(width / 2, height - 50, titulo)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.grey)
        c.drawRightString(width - 50, height - 30, f"Data: {data_hoje}")
        y = height - 80

    desenhar_cabecalho()

    for i, a in enumerate(alunos):
        if y < 150:
            c.showPage()
            desenhar_cabecalho()

        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.darkgreen)
        c.drawString(50, y, f"{i + 1}. {a.get('nome', 'Sem nome')}")
        y -= 20

        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        campos = [
            ("BI", a.get("bi", "")),
            ("Idade", a.get("idade", "")),
            ("Classe", a.get("classe", "")),
            ("Nome do Pai", a.get("pai", "")),
            ("Nome da Mãe", a.get("mae", "")),
            ("Disciplinas", ", ".join(a.get("disciplinas", []))),
            ("Localização", a.get("localizacao", "")),
        ]
        for label, valor in campos:
            if valor:
                c.drawString(60, y, f"{label}: {valor}")
                y -= 15

        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(50, y, width - 50, y)
        y -= 30

    c.save()
    return FileResponse(pdf_path, media_type="application/pdf", filename="lista_alunos.pdf")

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
    return alunos_data

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
