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

# Utilitários
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alunos Registrados</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            body {
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f6f9;
                padding: 40px;
            }
            .top-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }
            h1 {
                color: #2c3e50;
                margin: 0;
            }
            .data-registro {
                font-size: 14px;
                color: #7f8c8d;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background-color: #ffffff;
                box-shadow: 0 0 15px rgba(0,0,0,0.1);
            }
            th, td {
                padding: 14px;
                border: 1px solid #dcdcdc;
                text-align: left;
            }
            th {
                background-color: #2e86de;
                color: #fff;
            }
            tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            .actions a {
                margin-right: 10px;
                text-decoration: none;
                color: #2e86de;
            }
            .actions a:hover {
                text-decoration: underline;
            }
            .contract-clause {
                margin-top: 30px;
                font-size: 12px;
                color: #7f8c8d;
            }
            .contract-clause p {
                margin: 8px 0;
            }
            .contract-clause .icon-copy {
                cursor: pointer;
                color: #2e86de;
            }
            .pdf-button {
                margin-top: 20px;
                padding: 10px 20px;
                background-color: #2e86de;
                color: white;
                border: none;
                cursor: pointer;
                font-size: 16px;
            }
            .pdf-button:hover {
                background-color: #1e5fa0;
            }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <h1>Lista de Alunos Registrados</h1>
            <div class="data-registro">
                Data: {{ aluno.registro }}
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Nome</th>
                    <th>Idade</th>
                    <th>Data de Nascimento</th>
                    <th>Morada</th>
                    <th>Ponto de Referência</th>
                    <th>Disciplinas</th>
                    <th>Localização</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for a in alunos:
        conteudo_html += f"""
            <tr>
                <td>{a.get("nome_completo", "")}</td>
                <td>{a.get("idade", "")}</td>
                <td>{a.get("data_nascimento", "")}</td>
                <td>{a.get("morada", "")}</td>
                <td>{a.get("referencia", "")}</td>
                <td>{a.get("disciplinas", "")} {f"({a['outra_disciplina']})" if a.get("outra_disciplina") else ""}</td>
                <td>{a.get("localizacao", "")}</td>
                <td class="actions">
                    <a href="/editar-aluno/{a['nome_completo']}">Editar</a> |
                    <a href="/excluir-aluno/{a['nome_completo']}">Excluir</a>
                </td>
            </tr>
        """
    
    conteudo_html += """
            </tbody>
        </table>

        <!-- Botão para gerar o PDF -->
        <div>
            <button class="pdf-button" onclick="gerarPdf()">Gerar PDF do Aluno</button>
        </div>

        <!-- Informações Contratuais -->
        <div class="contract-clause">
            <p><strong>Cláusulas:</strong></p>
            <p><strong>1. Objeto do contrato</strong><br>
            O presente contrato tem como objeto a prestação de serviços de auxílio escolar ao(a) aluno(a) acima mencionado(a), através de aulas de explicação domiciliar, com foco nas necessidades educacionais do(a) aluno(a), conforme a avaliação prévia do Centro.</p>

            <p><strong>2. Duração do contrato</strong><br>
            Este contrato tem uma duração inicial de 3 meses, com renovação automática ao final de cada período, caso nenhuma das partes se manifeste contrária à renovação.</p>

            <p><strong>3. Valor e pagamento</strong><br>
            O valor mensal para a prestação dos serviços de auxílio escolar é de 24.900,00 Kz (Vinte e quatro mil e novecentos kwanzas), com pagamento a ser efetuado até o último dia de cada mês. Caso o pagamento seja efetuado com atraso superior a 10 dias, será acrescido uma taxa de juros de 10% sobre o valor total na conta do banco bai nº 282309786 10 001, iban nº 0040.0000.8230.9786.1016.6.</p>

            <p><strong>4. Responsabilidade pela prestação dos serviços</strong><br>
            O Centro compromete-se a designar o melhor professor domiciliar disponível, adequado às necessidades do(a) aluno(a). Caso o(a) responsável pelo aluno(a) considere que o professor designado não atende às expectativas, poderá solicitar a substituição do profissional, sendo esta substituição realizada sem custos adicionais para o cliente.</p>

            <p><strong>5. Responsabilidade do professor</strong><br>
            Caso o professor seja responsável por qualquer ato de má conduta dentro da residência do cliente (como roubo, agressão ou qualquer outro comportamento inadequado), ele será responsabilizado, sendo passível de penalização legal e/ou extrajudicial, conforme a gravidade do ato. O Centro se compromete a agir rapidamente, tomando as devidas providências.</p>

            <p><strong>10. Outras disposições</strong><br>
            Este contrato é regido pelas leis da República de Angola e qualquer questão não prevista nas cláusulas acima será resolvida de acordo com a legislação vigente.</p>

            <p><strong>ATT:</strong><br>
            Este contrato foi formulado para garantir que ambas as partes estejam cientes das suas responsabilidades e obrigações, assim como as condições de prestação dos serviços. A estrutura é clara e direta, visando a transparência e a boa relação entre o centro e os pais.</p>

            <!-- Ícone de copiar IBAN -->
            <p><strong>IBAN:</strong> 0040.0000.8230.9786.1016.6 <span class="icon-copy" onclick="copyIBAN()">📝 Copiar</span></p>
        </div>

        <script>
            function copyIBAN() {
                const iban = "0040.0000.8230.9786.1016.6";
                navigator.clipboard.writeText(iban).then(() => {
                    alert("IBAN copiado!");
                });
            }

            function gerarPdf() {
                window.location.href = "/gerar-pdf-aluno";  // A rota para gerar o PDF do aluno
            }
        </script>
    </body>
    </html>
    """
    
    with open("templates/info-alunos.html", "w", encoding="utf-8") as f:
        f.write(conteudo_html)

@app.get("/gerar-pdf-aluno")
async def gerar_pdf_aluno():
    aluno = {"nome_completo": "João Silva", "idade": 20, "morada": "Rua 123", "disciplinas": "Matemática"}
    file_path = "aluno.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)
    
    # Adicionando conteúdo ao PDF
    c.drawString(100, 750, f"Nome: {aluno['nome_completo']}")
    c.drawString(100, 730, f"Idade: {aluno['idade']}")
    c.drawString(100, 710, f"Morada: {aluno['morada']}")
    c.drawString(100, 690, f"Disciplinas: {aluno['disciplinas']}")
    
    c.save()
    
    return FileResponse(file_path, filename="aluno.pdf", media_type="application/pdf")

# Rotas dos Alunos

@app.get("/cadastro-aluno", response_class=HTMLResponse)
async def form_aluno(request: Request):
    return templates.TemplateResponse("dados-aluno.html", {"request": request})

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
    disciplinas: str = Form(""),
    outra_disciplina: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    localizacao = f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
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
        "localizacao": localizacao
    }
    alunos = carregar_alunos()
    alunos.append(novo_aluno)
    salvar_alunos(alunos)
    gerar_html_alunos()
    # Redireciona para a página inicial com a mensagem de sucesso
    return templates.TemplateResponse("dados-aluno.html", {
        "request": request,
        "mensagem_sucesso": "Inscrição feita com sucesso!"
    })

@app.get("/info-alunos.html", response_class=HTMLResponse)
async def mostrar_alunos(request: Request):
    alunos = carregar_alunos()
    return templates.TemplateResponse("info-alunos.html", {"request": request, "alunos": alunos})

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
    
@app.post("/excluir-aluno/{nome_completo}")
async def excluir_aluno(nome_completo: str):
    alunos = carregar_alunos()
    alunos = [a for a in alunos if a["nome_completo"] != nome_completo]
    salvar_alunos(alunos)
    gerar_html_alunos()
    return RedirectResponse(url="/info-alunos.html", status_code=303)

@app.get("/editar-aluno/{nome_completo}", response_class=HTMLResponse)
async def editar_aluno_form(nome_completo: str, request: Request):
    alunos = carregar_alunos()
    aluno = next((a for a in alunos if a["nome_completo"] == nome_completo), None)
    if not aluno:
        return HTMLResponse("Aluno não encontrado", status_code=404)
    return templates.TemplateResponse("editar-aluno.html", {"request": request, "aluno": aluno})

@app.post("/editar-aluno/{nome_completo}")
async def editar_aluno(
    request: Request,
    nome_completo: str,
    data_nascimento: str = Form(...),
    idade: int = Form(...),
    nome_pai: str = Form(...),
    nome_mae: str = Form(...),
    morada: str = Form(...),
    referencia: str = Form(...),
    disciplinas: str = Form(""),
    outra_disciplina: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form("")
):
    alunos = carregar_alunos()
    for i, a in enumerate(alunos):
        if a["nome_completo"] == nome_completo:
            alunos[i] = {
                "nome_completo": nome_completo,
                "data_nascimento": data_nascimento,
                "idade": idade,
                "nome_pai": nome_pai,
                "nome_mae": nome_mae,
                "morada": morada,
                "referencia": referencia,
                "disciplinas": disciplinas,
                "outra_disciplina": outra_disciplina,
                "localizacao": f"{latitude}, {longitude}" if latitude and longitude else "Não fornecida"
            }
            break
    salvar_alunos(alunos)
    gerar_html_alunos()
    return RedirectResponse(url="/info-alunos.html", status_code=303)  
    
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
