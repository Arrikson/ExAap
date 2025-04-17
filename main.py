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

def carregar_alunos():
    try:
        with open(ALUNOS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Função para salvar os alunos em JSON
def salvar_alunos(alunos):
    with open(ALUNOS_JSON, "w", encoding="utf-8") as f:
        json.dump(alunos, f, ensure_ascii=False, indent=4)

# Função para gerar HTML com os alunos cadastrados (placeholder)
def gerar_html_alunos():
    # Esta função pode ser usada futuramente para gerar um HTML com os dados de alunos
    pass

# Função para gerar o HTML do contrato
def gerar_html_contrato():
    html = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contrato de Prestação de Serviços</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f8f9fa;
                padding: 20px;
                margin: 0;
                color: #333;
            }
            .container {
                background: #fff;
                padding: 20px;
                border-radius: 12px;
                max-width: 600px;
                margin: 0 auto;
                box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
            }
            .logo {
                width: 60px;
                position: absolute;
                top: 20px;
                left: 20px;
            }
            h2 {
                text-align: center;
                margin-bottom: 15px;
                font-size: 18px;
                color: #2e86de;
            }
            p {
                font-size: 14px;
                line-height: 1.6;
                margin: 10px 0;
            }
            .clausulas {
                margin-top: 20px;
                font-size: 13px;
                line-height: 1.5;
            }
            .clausulas ul {
                margin-left: 20px;
            }
            .clausulas li {
                margin: 5px 0;
            }
            .copy-btn {
                background-color: #2e86de;
                color: white;
                padding: 5px 10px;
                border: none;
                cursor: pointer;
                border-radius: 5px;
            }
            .copy-btn:focus {
                outline: none;
            }
        </style>
    </head>
    <body>
        <img src="static/logo.png" alt="Logo" class="logo">
        <h2>Contrato de Prestação de Serviços</h2>
        <div class="clausulas">
            <ol>
                <li><strong>Objeto do contrato:</strong><br>
                O presente contrato tem como objeto a prestação de serviços de auxílio escolar ao(a) aluno(a) acima mencionado(a), através de aulas de explicação domiciliar, com foco nas necessidades educacionais do(a) aluno(a), conforme a avaliação prévia do Centro.</li>
                <li><strong>Duração do contrato:</strong><br>
                Este contrato tem uma duração inicial de 3 meses, com renovação automática ao final de cada período, caso nenhuma das partes se manifeste contrária à renovação.</li>
                <li><strong>Valor e pagamento:</strong><br>
                O valor mensal para a prestação dos serviços de auxílio escolar é de 24.900,00 Kz, com pagamento a ser efetuado até o último dia de cada mês. Caso o pagamento seja efetuado com atraso superior a 10 dias, será acrescido uma taxa de juros de 10% sobre o valor total na conta do banco BAI nº 282309786 10 001, IBAN nº 0040.0000.8230.9786.1016.6.</li>
                <li><strong>Responsabilidade pela prestação dos serviços:</strong><br>
                O Centro compromete-se a designar o melhor professor domiciliar disponível, adequado às necessidades do(a) aluno(a). Caso o(a) responsável pelo aluno(a) considere que o professor designado não atende às expectativas, poderá solicitar a substituição do profissional, sendo esta substituição realizada sem custos adicionais para o cliente.</li>
                <li><strong>Responsabilidade do professor:</strong><br>
                Caso o professor seja responsável por qualquer ato de má conduta dentro da residência do cliente, ele será responsabilizado, sendo passível de penalização legal e/ou extrajudicial, conforme a gravidade do ato.</li>
                <li><strong>Outras disposições:</strong><br>
                Este contrato é regido pelas leis da República de Angola e qualquer questão não prevista nas cláusulas acima será resolvida de acordo com a legislação vigente.</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return html

# Rota para gerar e enviar o PDF
@app.get("/gerar-pdf")
async def gerar_pdf():
    html = gerar_html_contrato()
    pdf = HTML(string=html).write_pdf()

    response = Response(content=pdf, media_type="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=contrato.pdf"
    return response

# Rota para exibir os alunos em HTML
@app.get("/info-a.html", response_class=HTMLResponse)
async def mostrar_alunos(request: Request):
    alunos = carregar_alunos()
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": alunos})

# Rota para gerar o PDF dos alunos
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
    gerar_html_alunos()

    return templates.TemplateResponse("aluno-info.html", {
        "request": request,
        "dados": dados,
        "now": datetime.now()
    })

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
