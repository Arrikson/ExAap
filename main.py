from starlette.status import HTTP_303_SEE_OTHER
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse
from fastapi import FastAPI, Form, Request, UploadFile, File, Body, Query
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
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone







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

@app.get("/onlineaula", response_class=HTMLResponse)
async def get_online_aula(request: Request):
    return templates.TemplateResponse("onlineaula.html", {"request": request})

@app.get("/onlineaula/{nome_aluno}", response_class=HTMLResponse)
async def exibir_online_aula(request: Request, nome_aluno: str):
    return templates.TemplateResponse("onlineaula.html", {
        "request": request,
        "nome_aluno": nome_aluno
    })

@app.get("/professores_online", response_class=HTMLResponse)
async def get_cadastro(request: Request):
    return templates.TemplateResponse("professores_online.html", {"request": request, "success": False})

@app.post("/professores_online", response_class=HTMLResponse)
async def post_cadastro(
    request: Request,
    nome_completo: str = Form(...),
    nome_mae: str = Form(...),
    nome_pai: str = Form(...),
    bilhete: str = Form(...),
    provincia: str = Form(...),
    municipio: str = Form(...),
    bairro: str = Form(...),
    residencia: str = Form(...),
    ponto_referencia: str = Form(...),
    localizacao: str = Form(...),
    telefone: str = Form(...),
    telefone_alternativo: str = Form(""),
    email: str = Form(...),
    nivel_ensino: str = Form(...),
    ano_faculdade: str = Form(""),
    area_formacao: str = Form(...),
    senha: str = Form(...)
):
    dados = {
        "nome_completo": nome_completo,
        "nome_mae": nome_mae,
        "nome_pai": nome_pai,
        "bilhete": bilhete,
        "provincia": provincia,
        "municipio": municipio,
        "bairro": bairro,
        "residencia": residencia,
        "ponto_referencia": ponto_referencia,
        "localizacao": localizacao,
        "telefone": telefone,
        "telefone_alternativo": telefone_alternativo,
        "email": email,
        "nivel_ensino": nivel_ensino,
        "ano_faculdade": ano_faculdade,
        "area_formacao": area_formacao,
        "senha": senha
    }

    db.collection("professores_online").add(dados)
    return RedirectResponse(url="/login_prof", status_code=303)

@app.get("/login_prof", response_class=HTMLResponse)
async def login_prof_get(request: Request):
    return templates.TemplateResponse("login_prof.html", {"request": request, "erro": None})
    

@app.post("/login_prof", response_class=HTMLResponse)
async def login_prof_post(
    request: Request,
    nome_completo: str = Form(...),
    senha: str = Form(...)
):
    professores_ref = db.collection("professores_online").where("nome_completo", "==", nome_completo).stream()

    for prof in professores_ref:
        dados = prof.to_dict()
        if dados.get("senha") == senha:
            email = dados.get("email")
            # ✅ Redirecionar para o perfil usando o e-mail na query string
            return RedirectResponse(url=f"/perfil_prof?email={email}", status_code=303)

    # ❌ Se não encontrou ou senha incorreta
    return templates.TemplateResponse("login_prof.html", {
        "request": request,
        "erro": "Nome completo ou senha incorretos."
    })


@app.get("/perfil_prof", response_class=HTMLResponse)
async def get_perfil_prof(request: Request, email: str):
    """
    Exibe o perfil do professor com base no email fornecido.
    Esse email normalmente virá da sessão de login ou como query param após login.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado"})

    prof_data = prof_doc.to_dict()
    prof_data["id"] = prof_doc.id  # armazenar ID do documento para atualização posterior
    return templates.TemplateResponse("perfil_prof.html", {"request": request, "professor": prof_data})


@app.post("/perfil_prof", response_class=HTMLResponse)
async def post_perfil_prof(
    request: Request,
    email: str = Form(...),
    descricao: str = Form(...)
):
    """
    Atualiza apenas o campo "descricao" do professor logado.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado para atualização."})

    # Atualizar o campo descrição
    db.collection("professores_online").document(prof_doc.id).update({
        "descricao": descricao
    })

    # Redireciona de volta ao perfil com confirmação
    return RedirectResponse(url=f"/perfil_prof?email={email}", status_code=303)


@app.get("/meus-dados")
async def meus_dados(email: str = Query(...)):
    prof_ref = db.collection("professores_online").where("email", "==", email).limit(1).stream()
    prof_doc = next(prof_ref, None)

    if not prof_doc:
        return {"erro": "Professor não encontrado"}

    return prof_doc.to_dict()

@app.get("/meus-alunos")
async def meus_alunos(email: str = Query(...)):
    # Aqui será feita consulta real no futuro
    return {
        "professor": email,
        "alunos": [
            {"nome": "João Pedro", "disciplina": "Matemática"},
            {"nome": "Ana Carla", "disciplina": "Física"},
            {"nome": "Luís Miguel", "disciplina": "Química"}
        ]
    }

@app.get("/aulas-dia")
async def aulas_dadas_no_dia(email: str = Query(...)):
    # Em produção, puxar do Firebase a agenda desse professor
    return {
        "professor": email,
        "data": "2025-06-08",
        "aulas": ["Matemática 10º Ano", "Física 11º Ano"],
        "quantidade": 2
    }

@app.get("/aulas-semana")
async def aulas_dadas_na_semana(email: str = Query(...)):
    return {
        "professor": email,
        "semana": "03 a 08 de Junho",
        "aulas": ["Matemática", "Física", "Química", "Inglês"],
        "quantidade": 7
    }

@app.get("/aulas-mes")
async def aulas_dadas_no_mes(email: str = Query(...)):
    return {
        "professor": email,
        "mes": "Junho",
        "quantidade": 28,
        "resumo": "Aulas ministradas com regularidade nas 4 semanas."
    }


@app.get("/aula_online", response_class=HTMLResponse)
async def get_aula_online(request: Request, email: str):
    """
    Renderiza a página da aula online (inonline.html) com o nome da disciplina.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado."})

    prof_data = prof_doc.to_dict()

    nome_disciplina = prof_data.get("formado_em", "Aula")
    professor_nome = prof_data.get("nome", "Professor")

    return templates.TemplateResponse("inonline.html", {
        "request": request,
        "nome_disciplina": nome_disciplina,
        "professor_nome": professor_nome,
        "email": email
    })


@app.get("/sala_virtual", response_class=HTMLResponse)
async def sala_virtual(request: Request, email: str):
    """
    Página da sala de aula online do professor.
    O professor será identificado pelo email enviado via query string.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado para criar a sala."})

    prof_data = prof_doc.to_dict()
    prof_data["id"] = prof_doc.id

    return templates.TemplateResponse("inonline.html", {
        "request": request,
        "professor": prof_data
    })


@app.post("/aceitar_aluno")
async def aceitar_aluno(
    email_prof: str = Form(...),
    email_aluno: str = Form(...),
    nome_aluno: str = Form(...)
):
    """
    Marca um aluno como aprovado para entrar na aula do professor.
    Atualiza a coleção 'aulas_ativas' no Firestore.
    """
    aula_ref = db.collection("aulas_ativas").document(email_prof)
    aula_doc = aula_ref.get()

    if not aula_doc.exists:
        return JSONResponse({"erro": "Aula não encontrada."}, status_code=404)

    aula_data = aula_doc.to_dict()
    pendentes = aula_data.get("alunos_pendentes", [])
    aprovados = aula_data.get("alunos_aprovados", [])

    # Remove o aluno da lista de pendentes
    pendentes = [a for a in pendentes if a["email"] != email_aluno]

    # Adiciona na lista de aprovados
    aprovados.append({"nome": nome_aluno, "email": email_aluno})

    # Atualiza o Firestore
    aula_ref.update({
        "alunos_pendentes": pendentes,
        "alunos_aprovados": aprovados
    })

    return JSONResponse({"mensagem": "Aluno aprovado com sucesso."})

@app.post("/verificar_aluno")
async def verificar_aluno(request: Request):
    dados = await request.json()
    nome = dados.get("nome")
    senha = dados.get("senha")

    with open("alunos.json", "r") as f:
        alunos = json.load(f)

    for aluno in alunos:
        if aluno["nome"] == nome and aluno["senha"] == senha:
            return {"ok": True}
    return JSONResponse(status_code=403, content={"erro": "Nome ou senha incorretos."})


@app.get("/sala_aluno", response_class=HTMLResponse)
async def exibir_sala_virtual_aluno(request: Request):
    return templates.TemplateResponse("sala_virtual_aluno.html", {"request": request})


@app.post("/solicitar_entrada")
async def solicitar_entrada(
    email_aluno: str = Form(...),
    nome_aluno: str = Form(...),
    peer_id_aluno: str = Form(...),
    id_professor: str = Form(...)
):
    # Aqui você pode registrar a solicitação em memória, JSON ou banco
    solicitacoes.append({
        "email": email_aluno,
        "nome": nome_aluno,
        "peer_id": peer_id_aluno,
        "id_professor": id_professor
    })
    
    print(f"Solicitação recebida de {nome_aluno} ({email_aluno}) para aula {id_professor}")
    
    # Simulação de aprovação imediata (em produção, o professor aprovaria manualmente)
    return JSONResponse(content={"autorizado": True})

# Modelo de entrada para criar vínculo
class VinculoIn(BaseModel):
    professor_email: str
    aluno_nome: str  # Usar nome para buscar o aluno na coleção

def vinculo_existe(prof_email: str, aluno_nome: str) -> bool:
    prof_email = prof_email.strip()
    aluno_nome = aluno_nome.strip()

    docs = db.collection('alunos_professor') \
             .where('professor', '==', prof_email) \
             .where('aluno', '==', aluno_nome) \
             .limit(1).stream()
    return next(docs, None) is not None
    
# Lista alunos disponíveis para um professor
@app.get('/alunos-disponiveis/{prof_email}')
async def alunos_disponiveis(prof_email: str):
    prof_docs = db.collection('professores_online') \
                  .where('email', '==', prof_email.strip()).limit(1).stream()
    prof = next(prof_docs, None)
    if not prof:
        raise HTTPException(status_code=404, detail='Professor não encontrado')
    
    prof_data = prof.to_dict()
    area = prof_data.get('area_formacao', '').strip()
    if not area:
        return []

    alunos = db.collection('alunos') \
               .where('disciplina', '==', area).stream()

    disponiveis = []
    for aluno in alunos:
        aluno_data = aluno.to_dict()
        nome = aluno_data.get('nome', '').strip()
        if nome and not vinculo_existe(prof_email.strip(), nome):
            disponiveis.append({
                'nome': nome,
                'disciplina': aluno_data.get('disciplina', '').strip()
            })
    return disponiveis

@app.post('/vincular-aluno', status_code=201)
async def vincular_aluno(item: VinculoIn):
    try:
        if vinculo_existe(item.professor_email, item.aluno_nome):
            raise HTTPException(status_code=409, detail='Vínculo já existe')

        # Buscar aluno pelo nome
        aluno_docs = db.collection('alunos') \
                       .where('nome', '==', item.aluno_nome.strip()) \
                       .limit(1).stream()
        aluno_doc = next(aluno_docs, None)

        if not aluno_doc:
            raise HTTPException(status_code=404, detail='Aluno não encontrado')

        dados_aluno = aluno_doc.to_dict()

        # Remove os campos sensíveis
        campos_excluir = ['senha', 'telefone', 'localizacao']
        for campo in campos_excluir:
            dados_aluno.pop(campo, None)

        # Criar o vínculo com informações completas do aluno e nome do professor
        db.collection('alunos_professor').add({
            'professor': item.professor_email.strip(),
            'aluno': item.aluno_nome.strip(),
            'dados_aluno': dados_aluno,
            'vinculado_em': datetime.now(timezone.utc).isoformat()
        })

        return {'message': 'Vínculo criado com sucesso'}

    except HTTPException as http_err:
        # Retorna erro HTTP como JSON (já tratado)
        raise http_err

    except Exception as e:
        # Registra erro no terminal para debug
        print('Erro interno ao vincular aluno:', e)

        # Retorna erro 500 com mensagem JSON válida
        return JSONResponse(
            status_code=500,
            content={'detail': 'Erro interno ao criar vínculo. Verifique os dados e tente novamente.'}
        )

