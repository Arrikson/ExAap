from starlette.status import HTTP_303_SEE_OTHER
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse
from fastapi import FastAPI, Form, Request, UploadFile, File, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
import os
import json
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from fpdf import FPDF



import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFESSORES_JSON = os.path.join(BASE_DIR, "professores.json")
ALUNOS_JSON = os.path.join(BASE_DIR, "alunos.json")

# Inicialização do Firebase com variável de ambiente
firebase_json = os.environ.get("FIREBASE_KEY")
if firebase_json and not firebase_admin._apps:
    firebase_info = json.loads(firebase_json)
    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def carregar_professores_local():
    if os.path.exists(PROFESSORES_JSON):
        with open(PROFESSORES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_professores_local(professores):
    with open(PROFESSORES_JSON, "w", encoding="utf-8") as f:
        json.dump(professores, f, ensure_ascii=False, indent=4)

def carregar_professores_firebase():
    return [doc.to_dict() for doc in db.collection("professores").stream()]

def salvar_professor_firebase(professor: dict):
    bi = professor.get("bi")
    if bi:
        db.collection("professores").document(bi).set(professor)

def excluir_professor_firebase(bi: str):
    db.collection("professores").document(bi).delete()

def gerar_html_professores():
    professores = carregar_professores_local()
    conteudo = """
    <!DOCTYPE html><html lang="pt"><head><meta charset="UTF-8">
    <title>Professores Registrados</title><link rel="stylesheet" href="/static/style.css">
    <style>body{font-family:Arial,sans-serif;background:#f8f9fa;padding:20px;}h1{text-align:center;color:#343a40;}
    table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 0 10px rgba(0,0,0,0.1);margin-top:20px;}
    th,td{padding:12px;border:1px solid #dee2e6;text-align:left;}th{background:#343a40;color:#fff;}
    tr:nth-child(even){background:#f1f1f1;}img{max-width:80px;border-radius:8px;}</style></head><body>
    <h1>Lista de Professores Registrados</h1><table>
    <tr><th>Foto</th><th>Nome</th><th>Idade</th><th>Pai</th><th>Mãe</th><th>Morada</th>
    <th>Referência</th><th>BI</th><th>Email</th><th>Telefone</th><th>Localização</th></tr>
    """
    for p in professores:
        foto = f'<img src="{p.get("doc_foto","")}" alt="Foto">' if p.get("doc_foto") else "N/A"
        conteudo += f"""<tr><td>{foto}</td><td>{p.get('nome','')}</td><td>{p.get('idade','')}</td>
        <td>{p.get('nome_pai','')}</td><td>{p.get('nome_mae','')}</td><td>{p.get('morada_atual','')}</td>
        <td>{p.get('ponto_referencia','')}</td><td>{p.get('bi','')}</td><td>{p.get('email','')}</td>
        <td>{p.get('telefone','')}</td><td>{p.get('localizacao','')}</td></tr>"""
    conteudo += "</table></body></html>"
    with open("templates/pro-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo)

# Carrega inicial
if not os.path.exists(PROFESSORES_JSON):
    salvar_professores_local([])
gerar_html_professores()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/criar-conta", response_class=HTMLResponse)
async def criar_conta(request: Request):
    return templates.TemplateResponse("criar-conta.html", {"request": request})


@app.post("/criar-conta")
async def criar_conta_post(
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...)
):
    # Coleção: alunos_sabilider
    dados = {
        "nome": nome,
        "email": email,
        "senha": senha,
        "data_criacao": datetime.utcnow().isoformat()
    }
    db.collection("alunos_sabilider").add(dados)
    return RedirectResponse(url="/criar-conta", status_code=303)

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
    professores = carregar_professores_local()
    return templates.TemplateResponse("info-p.html", {"request": request, "professores": professores})

@app.post("/excluir-professor/{bi}")
async def excluir_professor(bi: str):
    profs = carregar_professores_local()
    profs = [p for p in profs if p.get("bi") != bi]
    salvar_professores_local(profs)
    excluir_professor_firebase(bi)
    gerar_html_professores()
    return RedirectResponse(url="/info-p.html", status_code=303)

@app.get("/editar-professor/{bi}", response_class=HTMLResponse)
async def editar_professor_form(bi: str, request: Request):
    profs = carregar_professores_local()
    professor = next((p for p in profs if p.get("bi") == bi), None)
    if not professor:
        return HTMLResponse("Professor não encontrado", status_code=404)
    return templates.TemplateResponse("editar-professor.html", {"request": request, "professor": professor})

@app.get("/dados-professor.html", response_class=HTMLResponse)
async def dados_professor(request: Request):
    return templates.TemplateResponse("dados-professor.html", {"request": request})

@app.post("/api/professores", response_class=JSONResponse)
async def receber_professor_api(professor: dict = Body(...)):
    profs = carregar_professores_local()
    profs.append(professor)
    salvar_professores_local(profs)
    gerar_html_professores()
    salvar_professor_firebase(professor)
    return {"message": "Professor registrado com sucesso"}

@app.get("/api/professores")
async def listar_professores():
    return JSONResponse(content=carregar_professores_local())

@app.get("/api/firebase-professores")
async def listar_professores_firebase():
    return JSONResponse(content=carregar_professores_firebase())

@app.post("/registrar-professor", response_class=HTMLResponse)
async def registrar_professor(
    request: Request,
    nome: str = Form(...), idade: str = Form(...), nome_pai: str = Form(...),
    nome_mae: str = Form(...), morada_atual: str = Form(...), ponto_referencia: str = Form(...),
    bi: str = Form(...), disciplinas: List[str] = Form([]), outras_disciplinas: Optional[str] = Form(""),
    telefone: str = Form(...), email: str = Form(...), latitude: str = Form(...),
    longitude: str = Form(...), doc_foto: UploadFile = File(...), doc_pdf: UploadFile = File(...)
):
    os.makedirs("static/docs", exist_ok=True)
    foto_path = f"static/docs/{doc_foto.filename}"
    pdf_path = f"static/docs/{doc_pdf.filename}"
    with open(foto_path, "wb") as buff: shutil.copyfileobj(doc_foto.file, buff)
    with open(pdf_path, "wb") as buff: shutil.copyfileobj(doc_pdf.file, buff)

    novo = {
        "nome": nome, "idade": idade, "nome_pai": nome_pai, "nome_mae": nome_mae,
        "morada_atual": morada_atual, "ponto_referencia": ponto_referencia, "bi": bi,
        "disciplinas": disciplinas, "outras_disciplinas": outras_disciplinas,
        "telefone": telefone, "email": email,
        "localizacao": f"Latitude: {latitude}, Longitude: {longitude}",
        "doc_foto": "/" + foto_path, "doc_pdf": "/" + pdf_path
    }

    profs = carregar_professores_local()
    profs.append(novo)
    salvar_professores_local(profs)
    gerar_html_professores()
    salvar_professor_firebase(novo)
    return RedirectResponse(url="/pro-info.html", status_code=303)

@app.get("/gerar-pdf", response_class=FileResponse)
async def gerar_pdf():
    professores = carregar_professores_local()
    os.makedirs("static/docs", exist_ok=True)
    pdf_path = "static/docs/lista_professores.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 80

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 50, "Novos alunos Registrados")
    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 30, f"Data: {data_hoje}")

    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import Image as RLImage

    for i, p in enumerate(professores):
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.darkblue)
        c.drawString(50, y, f"{i+1}. {p.get('nome','Sem nome')}")
        y -= 20
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)

        for label, valor in [
            ("Idade", p.get("idade","")), ("Nome do Pai", p.get("nome_pai","")),
            ("Nome da Mãe", p.get("nome_mae","")), ("Morada Atual", p.get("morada_atual","")),
            ("Ponto de Referência", p.get("ponto_referencia","")), ("BI", p.get("bi","")),
            ("Disciplinas", ", ".join(p.get("disciplinas",[]))), ("Outras Disciplinas", p.get("outras_disciplinas","")),
            ("Telefone", p.get("telefone","")), ("Email", p.get("email","")),
            ("Localização", p.get("localizacao",""))
        ]:
            if valor:
                c.drawString(60, y, f"{label}: {valor}")
                y -= 15

        foto = p.get("doc_foto","").lstrip("/")
        if foto and os.path.exists(foto):
            try:
                c.drawImage(foto, width-6.5*cm, y-5*cm, width=5.5*cm, height=5.5*cm)
            except:
                c.drawString(60, y, "Erro ao carregar imagem.")
        y -= 100
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.line(50, y, width-50, y)
        y -= 30
        if y < 150:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width/2, height-50, "Novos Professores Registrados")
            c.setFont("Helvetica", 10)
            c.drawRightString(width-50, height-30, f"Data: {data_hoje}")

    c.save()
    return FileResponse(pdf_path, media_type="application/pdf", filename="lista_professores.pdf")

@app.get("/cadastro-aluno", response_class=HTMLResponse)
async def exibir_formulario(request: Request):
    return templates.TemplateResponse("cadastro-aluno.html", {"request": request, "erro": None})

@app.post("/cadastro-aluno")
async def cadastrar_aluno(
    request: Request,
    nome: str = Form(...),
    nome_mae: str = Form(...),
    nome_pai: str = Form(...),
    senha: str = Form(...),
    provincia: str = Form(...),
    municipio: str = Form(...),
    bairro: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    telefone: str = Form(...),
    disciplina: str = Form(...),
    outra_disciplina: str = Form(None)
):
    alunos_ref = db.collection("alunos")
    existente = alunos_ref.where("nome", "==", nome).get()

    if existente:
        return templates.TemplateResponse("cadastro-aluno.html", {
            "request": request,
            "erro": "Este nome já está cadastrado. Tente outro."
        })

    aluno_id = str(uuid.uuid4())
    dados = {
        "nome": nome,
        "nome_mae": nome_mae,
        "nome_pai": nome_pai,
        "senha": senha,
        "provincia": provincia,
        "municipio": municipio,
        "bairro": bairro,
        "localizacao": {"latitude": latitude, "longitude": longitude},
        "telefone": telefone,
        "disciplina": disciplina,
        "outra_disciplina": outra_disciplina
    }
    db.collection("alunos").document(aluno_id).set(dados)
    return RedirectResponse(url="/login?sucesso=1", status_code=HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
async def exibir_login(request: Request, sucesso: int = 0):
    return templates.TemplateResponse("login.html", {"request": request, "sucesso": sucesso, "erro": None})

@app.post("/login")
async def login(request: Request, nome: str = Form(...), senha: str = Form(...)):
    alunos = db.collection("alunos").where("nome", "==", nome).where("senha", "==", senha).get()
    if alunos:
        return RedirectResponse(url=f"/perfil/{nome}", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {"request": request, "erro": "Nome de usuário ou senha inválidos", "sucesso": 0})

@app.get("/perfil/{nome}", response_class=HTMLResponse)
async def perfil(request: Request, nome: str):
    aluno_ref = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_ref:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
    aluno = aluno_ref[0].to_dict()
    return templates.TemplateResponse("perfil.html", {"request": request, "aluno": aluno})

@app.post("/alterar-senha/{nome}")
async def alterar_senha(
    request: Request,
    nome: str,
    senha_antiga: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    aluno_docs = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_docs:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    aluno_ref = aluno_docs[0].reference
    aluno_data = aluno_docs[0].to_dict()

    if senha_antiga != aluno_data.get("senha"):
        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "aluno": aluno_data,
            "erro_senha": "Senha antiga incorreta!"
        })

    if nova_senha != confirmar_senha:
        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "aluno": aluno_data,
            "erro_senha": "As novas senhas não coincidem!"
        })

    aluno_ref.update({"senha": nova_senha})
    aluno_data["senha"] = nova_senha  # para manter os dados atualizados na recarga

    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "aluno": aluno_data,
        "sucesso_senha": "Senha alterada com sucesso!"
    })

@app.post("/atualizar-perfil/{nome}")
async def atualizar_perfil(
    request: Request,
    nome: str,
    telefone: str = Form(...),
    bairro: str = Form(...),
    municipio: str = Form(...),
    provincia: str = Form(...),
    disciplina: str = Form(...),
    outra_disciplina: str = Form(None)
):
    aluno_docs = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_docs:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    aluno_ref = aluno_docs[0].reference
    dados_atuais = aluno_docs[0].to_dict()

    atualizacoes = {
        "telefone": telefone,
        "bairro": bairro,
        "municipio": municipio,
        "provincia": provincia,
        "disciplina": disciplina,
    }

    if outra_disciplina:
        disciplinas_existentes = dados_atuais.get("outras_disciplinas", [])
        disciplinas_existentes.append(outra_disciplina)
        atualizacoes["outras_disciplinas"] = disciplinas_existentes

    aluno_ref.update(atualizacoes)
    return RedirectResponse(url=f"/perfil/{nome}", status_code=HTTP_303_SEE_OTHER)

@app.get("/aulaonline", response_class=HTMLResponse)
async def aula_online(request: Request):
    return templates.TemplateResponse("onlineaula.html", {"request": request})

@app.post("/verificar-aluno")
async def verificar_aluno(
    nome_aluno: str = Form(...),
    senha: str = Form(...),
    professor_id: str = Form(...)
):
    try:
        # Simula verificação de senha – você pode melhorar isso futuramente
        # Aqui consideramos apenas o nome e a presença dele na lista
        ref = db.collection("lista_de_alunos").document(professor_id)
        doc = ref.get()

        if doc.exists and nome_aluno in doc.to_dict().get("alunos", []):
            return JSONResponse({"status": "autorizado", "mensagem": "Acesso liberado para aula."})
        else:
            return JSONResponse({"status": "nao_autorizado", "mensagem": "Faça a sua solicitação ao professor."})

    except Exception as e:
        return JSONResponse({"status": "erro", "mensagem": str(e)})

@app.post("/verificar-aluno")
async def verificar_aluno(
    nome_aluno: str = Form(...),
    senha: str = Form(...),
    professor_id: str = Form(...)
):
    try:
        # Pega o documento da lista de alunos do professor
        ref_lista = db.collection("lista_de_alunos").document(professor_id)
        doc_lista = ref_lista.get()

        # Verifica se o aluno está na lista do professor
        if doc_lista.exists and nome_aluno in doc_lista.to_dict().get("alunos", []):
            # Pega os dados do aluno na coleção 'alunos'
            ref_aluno = db.collection("alunos").document(nome_aluno)
            doc_aluno = ref_aluno.get()

            if doc_aluno.exists:
                dados_aluno = doc_aluno.to_dict()
                senha_registrada = dados_aluno.get("senha")

                if senha == senha_registrada:
                    return JSONResponse({"status": "autorizado", "mensagem": "Acesso liberado para aula."})
                else:
                    return JSONResponse({"status": "erro", "mensagem": "Senha incorreta."})
            else:
                return JSONResponse({"status": "erro", "mensagem": "Aluno não encontrado no sistema."})
        else:
            return JSONResponse({"status": "nao_autorizado", "mensagem": "Você ainda não foi autorizado para essa aula."})

    except Exception as e:
        return JSONResponse({"status": "erro", "mensagem": str(e)})







