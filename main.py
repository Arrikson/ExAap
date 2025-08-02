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
import re
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import unquote
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
    

class VinculoIn(BaseModel):
    professor_email: str
    aluno_nome: str

def vinculo_existe(prof_email: str, aluno_nome: str) -> bool:
    prof_normalizado = prof_email.strip().lower()
    aluno_normalizado = aluno_nome.strip().lower()

    docs = db.collection('alunos_professor') \
             .where("professor", "==", prof_normalizado) \
             .where("aluno", "==", aluno_normalizado) \
             .limit(1).stream()

    return next(docs, None) is not None

@app.post('/vincular-aluno', status_code=201)
async def vincular_aluno(item: VinculoIn):
    try:
        prof = item.professor_email.strip().lower()
        aluno_nome_input = item.aluno_nome.strip().lower()

        # Buscar todos os alunos e comparar nome normalizado
        alunos = db.collection("alunos").stream()
        aluno_doc = None
        for doc in alunos:
            dados = doc.to_dict()
            nome_banco = dados.get("nome", "").strip().lower()
            if nome_banco == aluno_nome_input:
                aluno_doc = doc
                break

        if not aluno_doc:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        if vinculo_existe(prof, aluno_nome_input):
            raise HTTPException(status_code=409, detail="Vínculo já existe")

        dados_aluno = aluno_doc.to_dict()
        for campo in ['senha', 'telefone', 'localizacao']:
            dados_aluno.pop(campo, None)

        # Criação do documento com o campo horario vazio
        db.collection('alunos_professor').add({
            'professor': prof,
            'aluno': aluno_nome_input,
            'dados_aluno': dados_aluno,
            'vinculado_em': datetime.now(timezone.utc).isoformat(),
            'online': True,
            'notificacao': False,
            'aulas_dadas': 0,
            'total_aulas': 24,
            'aulas': [],
            'horario': {}  # Campo novo
        })

        # Atualiza o campo vinculado no documento do aluno
        db.collection("alunos").document(aluno_doc.id).update({
            "vinculado": True
        })

        return {"message": "Vínculo criado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print('Erro interno ao vincular aluno:', e)
        return JSONResponse(
            status_code=500,
            content={'detail': 'Erro interno ao criar vínculo. Verifique os dados e tente novamente.'}
        )

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

    # Lista apenas os alunos que ainda não estão vinculados
    alunos = db.collection('alunos') \
               .where('disciplina', '==', area) \
               .where('vinculado', '==', False).stream()

    disponiveis = []
    for aluno in alunos:
        aluno_data = aluno.to_dict()
        disponiveis.append({
            'nome': aluno_data.get('nome', ''),
            'disciplina': aluno_data.get('disciplina', '')
        })

    return disponiveis

@app.get('/meus-alunos/{prof_email}')
async def meus_alunos(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip()).stream()

        alunos = []
        for doc in docs:
            data = doc.to_dict()
            dados_aluno = data.get('dados_aluno', {})
            aluno = {
                'nome': dados_aluno.get('nome', ''),
                'disciplina': dados_aluno.get('disciplina', ''),
                'bairro': dados_aluno.get('bairro', ''),
                'municipio': dados_aluno.get('municipio', ''),
                'provincia': dados_aluno.get('provincia', ''),
                'nome_pai': dados_aluno.get('nome_pai', ''),
                'nome_mae': dados_aluno.get('nome_mae', ''),
                'outra_disciplina': dados_aluno.get('outra_disciplina', ''),
                'vinculado_em': data.get('vinculado_em', '')
            }
            alunos.append(aluno)

        return JSONResponse(content=alunos)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'detail': 'Erro ao buscar alunos vinculados', 'erro': str(e)}
        )


@app.get("/meus-alunos-status/{prof_email}")
async def meus_alunos_status(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip()).stream()

        alunos = []
        for doc in docs:
            d = doc.to_dict()
            dados = d.get('dados_aluno', {})
            nome_aluno = dados.get('nome', d.get('aluno'))

            # Verificar status real na coleção "alunos"
            aluno_query = db.collection("alunos").where("nome", "==", nome_aluno).limit(1).stream()
            aluno_doc = next(aluno_query, None)

            online = False
            if aluno_doc and aluno_doc.exists:
                aluno_data = aluno_doc.to_dict()
                online = aluno_data.get("online", False)

            alunos.append({
                'nome': nome_aluno,
                'disciplina': dados.get('disciplina'),
                'online': online
            })

        return alunos

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao buscar status dos alunos", "erro": str(e)})


@app.get("/alunos-status-completo/{prof_email}")
async def alunos_status_completo(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip()).stream()

        alunos = []
        for doc in docs:
            data = doc.to_dict()
            nome = data.get("aluno")

            # Buscar o documento na coleção "alunos"
            aluno_query = db.collection("alunos").where("nome", "==", nome).limit(1).stream()
            aluno_doc = next(aluno_query, None)

            if aluno_doc and aluno_doc.exists:
                aluno_data = aluno_doc.to_dict()
                alunos.append({
                    "nome": nome,
                    "online": aluno_data.get("online", False),
                    "last_seen": aluno_data.get("last_seen", "Desconhecido")
                })
            else:
                alunos.append({
                    "nome": nome,
                    "online": False,
                    "last_seen": "Desconhecido"
                })

        return alunos

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao buscar status dos alunos", "erro": str(e)})


@app.put("/atualizar-status/{aluno_nome}/{status}")
async def atualizar_status_online(aluno_nome: str, status: bool):
    try:
        query = db.collection("alunos") \
                  .where("nome", "==", aluno_nome.strip()).stream()

        atualizado = False
        for doc in query:
            doc.reference.update({
                "online": status,
                "last_seen": datetime.now(timezone.utc).isoformat()
            })
            atualizado = True

        if not atualizado:
            raise HTTPException(status_code=404, detail="Aluno não encontrado na coleção 'alunos'")

        return {"message": f"Status do aluno '{aluno_nome}' atualizado para {status}"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao atualizar status", "erro": str(e)})

@app.get("/buscar-professor/{nome_aluno}")
async def buscar_professor(nome_aluno: str):
    try:
        query = db.collection("alunos_professor") \
                  .where("aluno", "==", nome_aluno.strip()) \
                  .limit(1).stream()
        doc = next(query, None)

        if not doc:
            return JSONResponse(status_code=404, content={"professor": None, "disciplina": None})

        data = doc.to_dict()
        professor_email = data.get("professor")

        if not professor_email:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_query = db.collection("professores_online") \
                       .where("email", "==", professor_email.strip()) \
                       .limit(1).stream()
        prof_doc = next(prof_query, None)

        if not prof_doc:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_data = prof_doc.to_dict()
        return {
            "professor": prof_data.get("nome_completo", "Desconhecido"),
            "disciplina": prof_data.get("area_formacao", "Desconhecida")
        }

    except Exception as e:
        print("Erro ao buscar professor:", e)
        return JSONResponse(status_code=500, content={"detail": "Erro interno ao buscar professor"})

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

from firebase_admin import firestore

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

    with open(foto_path, "wb") as buff:
        shutil.copyfileobj(doc_foto.file, buff)

    with open(pdf_path, "wb") as buff:
        shutil.copyfileobj(doc_pdf.file, buff)

    novo = {
        "nome": nome,
        "idade": idade,
        "nome_pai": nome_pai,
        "nome_mae": nome_mae,
        "morada_atual": morada_atual,
        "ponto_referencia": ponto_referencia,
        "bi": bi,
        "disciplinas": disciplinas,
        "outras_disciplinas": outras_disciplinas,
        "telefone": telefone,
        "email": email,
        "localizacao": f"Latitude: {latitude}, Longitude: {longitude}",
        "doc_foto": "/" + foto_path,
        "doc_pdf": "/" + pdf_path
    }

    # Salvar localmente
    profs = carregar_professores_local()
    profs.append(novo)
    salvar_professores_local(profs)
    gerar_html_professores()

    # Salvar na coleção antiga
    salvar_professor_firebase(novo)

    # ✅ Também salvar na nova coleção "professores_online2"
    db = firestore.client()
    db.collection("professores_online2").document(email).set(novo)

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
    nome_normalizado = nome.strip().lower()

    existente = alunos_ref.where("nome_normalizado", "==", nome_normalizado).get()

    if existente:
        return templates.TemplateResponse("cadastro-aluno.html", {
            "request": request,
            "erro": "Este nome já está cadastrado. Tente outro."
        })

    aluno_id = str(uuid.uuid4())
    dados = {
        "nome": nome,
        "nome_normalizado": nome_normalizado,  # ← campo adicionado
        "nome_mae": nome_mae,
        "nome_pai": nome_pai,
        "senha": senha,
        "provincia": provincia,
        "municipio": municipio,
        "bairro": bairro,
        "localizacao": {
            "latitude": latitude,
            "longitude": longitude
        },
        "telefone": telefone,
        "disciplina": disciplina,
        "outra_disciplina": outra_disciplina,
        "online": False,
        "notificacao": False,
        "vinculado": False,
        "horario": {}  # Campo novo, inicialmente vazio
    }

    db.collection("alunos").document(aluno_id).set(dados)

    return RedirectResponse(url="/login?sucesso=1", status_code=HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def exibir_login(request: Request, sucesso: int = 0):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "sucesso": sucesso,
        "erro": None
    })

@app.post("/login")
async def login(request: Request, nome: str = Form(...), senha: str = Form(...)):
    alunos_ref = db.collection("alunos")

    # Normaliza os valores digitados
    nome_digitado = nome.strip().lower()
    senha_digitada = senha.strip().lower()

    # Busca todos os alunos para fazer comparação segura
    alunos = alunos_ref.stream()

    for aluno in alunos:
        dados = aluno.to_dict()
        nome_banco = dados.get("nome", "").strip().lower()
        senha_banco = dados.get("senha", "").strip().lower()

        if nome_banco == nome_digitado and senha_banco == senha_digitada:
            aluno.reference.update({"online": True})
            return RedirectResponse(url=f"/perfil/{dados.get('nome')}", status_code=303)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "erro": "Nome de usuário ou senha inválidos",
        "sucesso": 0
    })


from starlette.status import HTTP_303_SEE_OTHER

@app.get("/perfil/{nome}", response_class=HTMLResponse) 
async def perfil(request: Request, nome: str):
    aluno_ref = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_ref:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    doc = aluno_ref[0]
    aluno = doc.to_dict()

    # Atualiza status online com timestamp
    db.collection("alunos").document(doc.id).update({
        "online": True,
        "ultimo_ping": datetime.utcnow().isoformat()
    })

    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "aluno": aluno,
    })

from slugify import slugify


def slug(texto):
    return slugify(texto.strip().lower())


def professor_possui_alunos(prof_email: str) -> bool:
    prof_email = prof_email.strip().lower()
    docs = db.collection('alunos_professor') \
             .where('professor', '==', prof_email) \
             .limit(1).stream()
    return next(docs, None) is not None


def buscar_professor_por_email(email: str):
    email = email.strip().lower()
    professores = db.collection("professores_online2") \
                    .where("email", "==", email) \
                    .limit(1).stream()
    for prof in professores:
        return prof.to_dict()
    return None

# ✅ Verifica se o vínculo entre aluno e professor existe
def vinculo_existe(prof_email: str, aluno_nome: str) -> Optional[dict]:
    prof_email = prof_email.strip().lower()
    aluno_nome = aluno_nome.strip().lower()

    docs = db.collection("alunos_professor") \
             .where("professor", "==", prof_email) \
             .where("aluno", "==", aluno_nome) \
             .limit(1).stream()
    return next(docs, None)


@app.get("/sala_virtual_professor", response_class=HTMLResponse)
async def get_sala_virtual_professor(
    request: Request,
    email: Optional[str] = Query(default=None),
    aluno: Optional[str] = Query(default=None)
):
    if not email:
        return HTMLResponse("<h2 style='color:red'>Erro: email não fornecido na URL.</h2>", status_code=400)

    try:
        email = email.strip().lower()
        aluno_normalizado = aluno.strip().lower() if aluno else None

        # 🔍 Busca o documento do professor
        doc_ref = db.collection("professores_online2").document(email)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Professor não encontrado.")

        professor = doc.to_dict()

        # 🧪 Valida vínculo com o aluno, se fornecido
        if aluno:
            # Buscar todos os documentos do professor na coleção alunos_professor
            docs = db.collection('alunos_professor') \
                .where('professor', '==', email).stream()

            vinculo_encontrado = False
            for d in docs:
                data = d.to_dict()
                dados_aluno = data.get("dados_aluno", {})
                nome_no_banco = dados_aluno.get("nome", "").strip().lower()
                if nome_no_banco == aluno_normalizado:
                    vinculo_encontrado = True
                    break

            if not vinculo_encontrado:
                return HTMLResponse(
                    "<h2 style='color:red'>Vínculo entre professor e aluno não encontrado.</h2>",
                    status_code=403
                )

        # 🔑 Gera ID da sala
        def slug(texto):
            return slugify(texto)

        sala_id = f"{slug(email)}-{slug(aluno_normalizado)}" if aluno else slug(email)

        return templates.TemplateResponse("sala_virtual_professor.html", {
            "request": request,
            "email": email,
            "aluno": aluno,
            "professor": professor,
            "sala_id": sala_id
        })

    except Exception as e:
        return HTMLResponse(f"<h2 style='color:red'>Erro ao abrir sala do professor: {str(e)}</h2>", status_code=500)

@app.get("/sala_virtual_aluno", response_class=HTMLResponse)
async def get_sala_virtual_aluno(
    request: Request,
    email: Optional[str] = Query(default=None),
    aluno: Optional[str] = Query(default=None)
):
    if not email or not aluno:
        return HTMLResponse("<h2 style='color:red'>Erro: Parâmetros faltando.</h2>", status_code=400)

    email_normalizado = email.strip().lower()
    aluno_normalizado = aluno.strip().lower()

    # Verifica se o aluno está vinculado ao professor
    aluno_data = vinculo_existe(email_normalizado, aluno_normalizado)
    if not aluno_data:
        return HTMLResponse("<h2 style='color:red'>Aluno não encontrado ou não vinculado ao professor.</h2>", status_code=403)

    # Verifica se o professor existe
    professor = buscar_professor_por_email(email_normalizado)
    if not professor:
        return HTMLResponse("<h2 style='color:red'>Professor não encontrado.</h2>", status_code=404)

    return templates.TemplateResponse("sala_virtual_aluno.html", {
        "request": request,
        "aluno": aluno.strip(),  # Mantemos o nome original para exibir corretamente no HTML
        "professor": email_normalizado
    })


@app.get("/sala_virtual_aluno/{sala}")
async def redirecionar_para_sala_aluno(sala: str):
    decoded = unquote(sala)

    if "-" not in decoded or decoded.count("-") < 1:
        return HTMLResponse(
            "<h2 style='color:red'>Formato inválido: esperado 'email-do-professor-nome-do-aluno'</h2>",
            status_code=400
        )

    try:
        professor_email, aluno_nome = decoded.split("-", 1)
    except Exception as e:
        return HTMLResponse(f"<h2 style='color:red'>Erro ao processar os dados da sala: {str(e)}</h2>", status_code=400)

    return RedirectResponse(
        url=f"/sala_virtual_aluno?email={professor_email}&aluno={aluno_nome}"
    )


def vinculo_existe(prof_email: str, aluno_nome: str) -> dict:
    """
    Verifica se o aluno está vinculado ao professor (normalizando os dados dos dois lados).
    """
    prof_email = prof_email.strip().lower()
    aluno_nome = aluno_nome.strip().lower()

    try:
        docs = db.collection("alunos_professor") \
                 .where("professor", "==", prof_email) \
                 .stream()

        for doc in docs:
            data = doc.to_dict()
            nome_banco = data.get("aluno", "").strip().lower()

            if nome_banco == aluno_nome:
                return data

        return None
    except Exception as e:
        print(f"❌ Erro ao verificar vínculo: {e}")
        return None

@app.post("/solicitar_entrada")
async def solicitar_entrada(
    nome_aluno: str = Form(...),
    senha_aluno: str = Form(...),
    peer_id_aluno: str = Form(...),
    id_professor: str = Form(...)
):
    try:
        aluno_info = vinculo_existe(id_professor, nome_aluno)

        if not aluno_info:
            return JSONResponse(
                status_code=403,
                content={"autorizado": False, "motivo": "Aluno não está vinculado ao professor."}
            )

        if aluno_info.get("senha") != senha_aluno:
            return JSONResponse(
                status_code=403,
                content={"autorizado": False, "motivo": "Senha incorreta."}
            )

        print(f"✅ Solicitação autorizada: {nome_aluno} para professor {id_professor} com PeerID {peer_id_aluno}")
        return JSONResponse(content={"autorizado": True})

    except Exception as e:
        print(f"Erro ao verificar solicitação: {e}")
        return JSONResponse(
            status_code=500,
            content={"autorizado": False, "erro": "Erro interno ao verificar vínculo."}
        )

@app.get("/logout/{nome}")
async def logout(nome: str):
    db = firestore.client()
    alunos_ref = db.collection("alunos")
    query = alunos_ref.where("nome", "==", nome).stream()
    for aluno in query:
        aluno.reference.update({"online": False})
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    
@app.post("/logout")
async def logout(request: Request):
    data = await request.json()
    nome = data.get("nome")
    db = firestore.client()
    alunos_ref = db.collection("alunos")
    query = alunos_ref.where("nome", "==", nome).stream()
    for aluno in query:
        aluno.reference.update({"online": False})
    return RedirectResponse(url="/", status_code=303)

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


@app.post("/ping-online")
async def ping_online(payload: dict = Body(...)):
    nome = payload.get("nome")
    if not nome:
        return {"status": "erro", "mensagem": "Nome não fornecido"}

    aluno_ref = db.collection("alunos").where("nome", "==", nome).get()
    if aluno_ref:
        doc = aluno_ref[0]
        db.collection("alunos").document(doc.id).update({
            "online": True,
            "ultimo_ping": datetime.utcnow().isoformat()
        })
        return {"status": "ok"}
    else:
        return {"status": "erro", "mensagem": "Aluno não encontrado"}

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
        "senha": senha,
        "online": True
    }

    # ✅ Coleção original (mantém como está)
    db.collection("professores_online").add(dados)

    # ✅ Nova coleção: professores_online2 com email como ID
    try:
        db.collection("professores_online2").document(email).set(dados)
        print(f"✅ Salvo em professores_online2 com ID {email}")
    except Exception as e:
        print(f"❌ Erro ao salvar em professores_online2: {e}")

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

            # Atualiza o campo 'online' para True
            db.collection("professores_online").document(prof.id).update({
                "online": True
            })

            return RedirectResponse(url=f"/perfil_prof?email={email}", status_code=303)

    # ❌ Se não encontrou ou senha incorreta
    return templates.TemplateResponse("login_prof.html", {
        "request": request,
        "erro": "Nome completo ou senha incorretos."
    })

@app.post("/logout_prof", response_class=HTMLResponse)
async def logout_prof(request: Request, email: str = Form(...)):
    professores_ref = db.collection("professores_online").where("email", "==", email).stream()

    for prof in professores_ref:
        db.collection("professores_online").document(prof.id).update({
            "online": False
        })
        break  # só precisa atualizar um documento

    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

@app.get("/meus-dados")
async def meus_dados(email: str = Query(...)):
    prof_ref = db.collection("professores_online").where("email", "==", email).limit(1).stream()
    prof_doc = next(prof_ref, None)

    if not prof_doc:
        return {"erro": "Professor não encontrado"}

    return prof_doc.to_dict()

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


@app.get("/professor-do-aluno/{nome_aluno}")
async def obter_professor_do_aluno(nome_aluno: str):
    try:
        # Buscar o documento do aluno na coleção "alunos_professor"
        alunos_ref = db.collection("alunos_professor")
        query = alunos_ref.where("aluno", "==", nome_aluno.strip()).limit(1).stream()
        aluno_doc = next(query, None)

        if not aluno_doc:
            raise HTTPException(status_code=404, detail="Aluno não vinculado a nenhum professor.")

        dados = aluno_doc.to_dict()
        professor_email = dados.get("professor")

        if not professor_email:
            raise HTTPException(status_code=404, detail="Email do professor não encontrado.")

        # Verificar se o professor está online na coleção "professores_online"
        prof_online_ref = db.collection("professores_online").where("email", "==", professor_email).limit(1).stream()
        prof_doc = next(prof_online_ref, None)

        online_status = False
        if prof_doc:
            online_status = prof_doc.to_dict().get("online", False)

        return JSONResponse(content={
            "professor": professor_email,
            "online": online_status
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meu-professor-status/{nome_aluno}")
async def meu_professor_status(nome_aluno: str):
    try:
        # Normalizar nome do aluno (como em /vincular-aluno)
        nome_aluno_input = nome_aluno.strip().lower()

        # Procurar o aluno na coleção "alunos"
        alunos_ref = db.collection("alunos").stream()
        aluno_doc = None
        for doc in alunos_ref:
            dados = doc.to_dict()
            nome_banco = dados.get("nome", "").strip().lower()
            if nome_banco == nome_aluno_input:
                aluno_doc = doc
                break

        if not aluno_doc:
            return JSONResponse(content={
                "professor": "Aluno não encontrado",
                "online": False
            }, status_code=404)

        # Verificar vínculo na coleção "alunos_professor"
        vinculo_ref = db.collection("alunos_professor") \
                        .where("aluno", "==", nome_aluno_input) \
                        .limit(1) \
                        .stream()
        vinculo_doc = next(vinculo_ref, None)

        if not vinculo_doc:
            return JSONResponse(content={
                "professor": "Nenhum professor vinculado",
                "online": False
            }, status_code=404)

        dados_vinculo = vinculo_doc.to_dict()
        professor_nome = dados_vinculo.get("professor", "Professor não especificado")
        online_status = dados_vinculo.get("online", False)

        return JSONResponse(content={
            "professor": professor_nome,
            "online": online_status
        }, status_code=200)

    except Exception as e:
        print("Erro ao obter status do professor:", e)
        return JSONResponse(content={
            "erro": f"Erro interno: {str(e)}"
        }, status_code=500)


@app.post("/iniciar-aula")
async def iniciar_aula(payload: dict):
    aluno = payload.get("aluno", "").strip().lower()
    professor = payload.get("professor", "").strip().lower()
    sala = payload.get("sala", "")

    db.collection("chamadas_ao_vivo").document(aluno).set({
        "aluno": aluno,
        "professor": professor,
        "sala": sala,
        "status": "pendente",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {"mensagem": "Chamada enviada ao aluno"}

# 🔸 Verificar vínculo do aluno com o professor
@app.post('/verificar-vinculo')
async def verificar_vinculo(dados: dict):
    prof_email = dados.get('professor_email', '').strip().lower()
    aluno_nome = dados.get('aluno_nome', '').strip().lower()
    senha = dados.get('senha', '').strip()

    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email).stream()

        aluno_encontrado = False
        for doc in docs:
            data = doc.to_dict()
            dados_aluno = data.get('dados_aluno', {})
            nome_salvo = dados_aluno.get('nome', '').strip().lower()
            if nome_salvo == aluno_nome:
                aluno_encontrado = True
                break

        if not aluno_encontrado:
            raise HTTPException(status_code=404, detail="Vínculo com este aluno não encontrado.")

        aluno_docs = db.collection('alunos') \
                       .where('nome', '==', aluno_nome) \
                       .where('senha', '==', senha) \
                       .limit(1).stream()
        aluno_doc = next(aluno_docs, None)
        if not aluno_doc:
            raise HTTPException(status_code=403, detail="Senha incorreta.")

        return {"message": "Aluno autorizado."}

    except HTTPException:
        raise
    except Exception as e:
        print("Erro ao verificar vínculo:", e)
        raise HTTPException(status_code=500, detail="Erro interno.")

# 🔸 Verificar vínculo e professor do aluno
class VerificarAlunoInput(BaseModel):
    aluno_nome: str
    senha: str

@app.post("/verificar-aluno-vinculo")
async def verificar_aluno_vinculo(data: VerificarAlunoInput):
    try:
        aluno_nome = data.aluno_nome.strip().lower()
        senha = data.senha.strip()

        aluno_docs = db.collection('alunos') \
            .where('nome', '==', aluno_nome) \
            .limit(1).stream()

        aluno_doc = next(aluno_docs, None)
        if not aluno_doc:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        aluno_data = aluno_doc.to_dict()
        if aluno_data.get("senha") != senha:
            raise HTTPException(status_code=401, detail="Senha incorreta.")

        vinculo_docs = db.collection('alunos_professor') \
            .where('aluno', '==', aluno_nome) \
            .limit(1).stream()

        vinculo_doc = next(vinculo_docs, None)
        if not vinculo_doc:
            raise HTTPException(status_code=404, detail="Nenhum vínculo encontrado com professor.")

        vinculo_data = vinculo_doc.to_dict()
        professor_email = vinculo_data.get("professor", "").strip().lower()

        prof_docs = db.collection('professores_online') \
            .where('email', '==', professor_email) \
            .limit(1).stream()

        prof_doc = next(prof_docs, None)
        professor_nome = prof_doc.to_dict().get("nome_completo", "Professor") if prof_doc else "Professor"

        return {
            "professor_email": professor_email,
            "professor_nome": professor_nome
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Erro interno:", e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno ao verificar vínculo do aluno."}
        )

class NotificacaoRequest(BaseModel):
    aluno: str

@app.post("/ativar-notificacao")
async def ativar_notificacao(data: NotificacaoRequest):
    try:
        aluno_nome = data.aluno.strip().lower()

        # Buscar o documento do aluno na coleção alunos_professor
        docs = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno_nome) \
                 .limit(1).stream()
        doc = next(docs, None)

        if not doc:
            return JSONResponse(
                content={"msg": f"Aluno '{aluno_nome}' não encontrado."},
                status_code=404
            )

        db.collection("alunos_professor").document(doc.id).update({"notificacao": True})
        return {"msg": f"Notificação ativada para o aluno '{aluno_nome}'."}

    except Exception as e:
        return JSONResponse(
            content={"msg": f"Erro ao ativar notificação: {str(e)}"},
            status_code=500
        )


class AlunoInfo(BaseModel):
    aluno: str

@app.post("/desativar-notificacao")
async def desativar_notificacao(info: AlunoInfo):
    try:
        aluno = info.aluno.strip().lower()

        docs = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno) \
                 .limit(1).stream()

        doc = next(docs, None)

        if not doc:
            return JSONResponse(
                content={"status": "erro", "mensagem": "Aluno não encontrado"},
                status_code=404
            )

        doc.reference.update({"notificacao": False})
        return {"status": "ok", "mensagem": "Notificação desativada"}

    except Exception as e:
        return JSONResponse(
            content={"status": "erro", "mensagem": f"Erro ao desativar notificação: {str(e)}"},
            status_code=500
        )


@app.post("/verificar-notificacao")
async def verificar_notificacao(request: Request):
    try:
        dados = await request.json()
        nome_aluno = str(dados.get("aluno", "")).strip().lower()

        if not nome_aluno:
            return JSONResponse(content={"erro": "Nome do aluno não fornecido"}, status_code=400)

        query = db.collection("alunos_professor") \
                  .where("aluno", "==", nome_aluno) \
                  .limit(1).stream()

        doc = next(query, None)

        if not doc:
            return JSONResponse(
                content={"notificacao": False, "mensagem": "Aluno não encontrado"},
                status_code=404
            )

        dados_aluno = doc.to_dict()
        notificacao = dados_aluno.get("notificacao", False)
        professor_email = dados_aluno.get("professor", "")

        return JSONResponse(content={
            "notificacao": notificacao,
            "professor_email": professor_email
        })

    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)


from fastapi import Request
from fastapi.responses import JSONResponse

@app.post("/registrar-chamada")
async def registrar_chamada(request: Request):
    try:
        dados = await request.json()
        aluno_raw = dados.get("aluno")
        professor_raw = dados.get("professor")

        if not aluno_raw or not professor_raw:
            return JSONResponse(content={"erro": "Dados incompletos"}, status_code=400)

        # Normalização
        aluno_normalizado = str(aluno_raw).strip().lower().replace(" ", "")
        professor_normalizado = str(professor_raw).strip().lower()
        nome_sala = f"{professor_normalizado.replace(' ', '_')}-{aluno_normalizado}"

        # Verificar vínculo
        vinculo_docs = db.collection("alunos_professor") \
                         .where("professor", "==", professor_normalizado) \
                         .stream()

        vinculo_encontrado = False
        for doc in vinculo_docs:
            data = doc.to_dict()
            aluno_db = data.get("aluno", "").strip().lower().replace(" ", "")
            if aluno_db == aluno_normalizado:
                vinculo_encontrado = True
                break

        if not vinculo_encontrado:
            return JSONResponse(
                content={"erro": "Vínculo entre professor e aluno não encontrado."},
                status_code=403
            )

        # Verificar ou criar o documento de chamada
        doc_ref = db.collection("chamadas_ao_vivo").document(aluno_normalizado)
        doc = doc_ref.get()

        if not doc.exists:
            # 🔧 Se não existir, cria automaticamente com status 'aceito'
            doc_ref.set({
                "aluno": aluno_normalizado,
                "professor": professor_normalizado,
                "status": "aceito",
                "sala": nome_sala
            }, merge=True)

            return JSONResponse(
                content={
                    "mensagem": "Conexão autorizada - documento criado.",
                    "sala": nome_sala
                },
                status_code=200
            )

        # Verificar status existente
        dados_atuais = doc.to_dict() or {}
        status_atual = dados_atuais.get("status", "")

        if status_atual == "aceito":
            doc_ref.set({
                "aluno": aluno_normalizado,
                "professor": professor_normalizado,
                "sala": nome_sala
            }, merge=True)

            return JSONResponse(
                content={
                    "mensagem": "Conexão autorizada com status 'aceito'.",
                    "sala": nome_sala
                },
                status_code=200
            )

        elif status_atual == "pendente":
            return JSONResponse(
                content={"erro": "Aguardando o aluno aceitar a chamada..."},
                status_code=403
            )

        elif status_atual == "recusado":
            return JSONResponse(
                content={"erro": "O aluno recusou a chamada."},
                status_code=403
            )

        else:
            return JSONResponse(
                content={"erro": f"Status de chamada desconhecido: '{status_atual}'"},
                status_code=403
            )

    except Exception as e:
        print(f"❌ ERRO AO REGISTRAR CHAMADA: {str(e)}")
        return JSONResponse(
            content={"erro": f"Erro interno ao registrar chamada: {str(e)}"},
            status_code=500
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/verificar-transmissao/{professor_email}/{aluno_nome}")
def verificar_transmissao(professor_email: str, aluno_nome: str):
    professor_id = professor_email.strip().lower()
    aluno_id = aluno_nome.strip().lower().replace(" ", "_")

    doc_ref = db.collection("chamadas_ao_vivo").document(aluno_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Chamada não encontrada")

    dados = doc.to_dict()
    if dados.get("professor") != professor_id:
        raise HTTPException(status_code=400, detail="Professor não corresponde")

    status = dados.get("status", "")
    if status == "aceito":
        return {"status": "ok", "sala": f"{professor_id}-{aluno_id}"}
    elif status == "pendente":
        return {"status": "aguardando"}
    elif status == "rejeitado":
        return {"status": "rejeitado"}
    else:
        return {"status": "desconhecido"}

@app.post("/definir-status-ok")
def definir_status_ok(dados: dict):
    aluno = dados.get("aluno")
    if not aluno:
        raise HTTPException(status_code=400, detail="Aluno não informado")

    aluno_id = aluno.strip().lower().replace(" ", "_")
    ref = db.collection("chamadas_ao_vivo").document(aluno_id)
    ref.set({"status": "aceito"}, merge=True)

    return {"msg": "Status definido como aceito"}

@app.get("/verificar-status/{aluno_nome}")
def verificar_status(aluno_nome: str):
    try:
        if not aluno_nome:
            return JSONResponse(content={"erro": "Aluno não especificado"}, status_code=400)

        aluno_id = aluno_nome.strip().lower().replace(" ", "_")
        ref = db.collection("chamadas_ao_vivo").document(aluno_id)
        doc = ref.get()

        if doc.exists:
            status = doc.to_dict().get("status", "pendente")
            if status == "pendente":
                ref.update({"status": "aceito"})
                status = "aceito"
            return {"status": status}
        else:
            return {"status": "nao_encontrado"}

    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)

@app.post("/enviar-id-aula")
async def enviar_id_aula(request: Request):
    dados = await request.json()
    peer_id = dados.get("peer_id")
    email_professor = dados.get("email")
    nome_aluno_raw = dados.get("aluno")

    if not peer_id or not email_professor or not nome_aluno_raw:
        return JSONResponse(status_code=400, content={"erro": "Dados incompletos"})

    try:
        nome_aluno = nome_aluno_raw.strip().lower().replace(" ", "")
        doc_ref = db.collection("alunos").document(nome_aluno)
        doc_ref.set({
            "id_chamada": peer_id,
            "professor_chamada": email_professor.strip().lower()
        }, merge=True)

        return JSONResponse(content={"status": "ID enviado com sucesso"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.get("/buscar-id-professor")
async def buscar_id_professor(aluno: str):
    try:
        aluno_normalizado = aluno.strip().lower().replace(" ", "")
        doc_ref = db.collection("alunos").document(aluno_normalizado)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            return {"peer_id": data.get("id_chamada")}
        else:
            return {"peer_id": None}
    except Exception as e:
        return {"erro": str(e)}

from datetime import datetime
from fastapi import Body, HTTPException

@app.post("/registrar-aula")
async def registrar_aula(data: dict = Body(...)):
    try:
        professor = data.get("professor", "").strip().lower()
        aluno = data.get("aluno", "").strip().lower()

        if not professor or not aluno:
            raise HTTPException(status_code=400, detail="Dados incompletos")

        query = db.collection("alunos_professor") \
                  .where("professor", "==", professor) \
                  .where("aluno", "==", aluno) \
                  .limit(1).stream()

        doc = next(query, None)
        if not doc:
            raise HTTPException(status_code=404, detail="Vínculo não encontrado")

        doc_ref = db.collection("alunos_professor").document(doc.id)
        doc_data = doc.to_dict()
        aulas_anteriores = doc_data.get("aulas_dadas", 0)
        lista_aulas = doc_data.get("aulas", [])

        agora = datetime.now()
        nova_aula = {
            "data": agora.strftime("%Y-%m-%d"),
            "horario": agora.strftime("%H:%M")
        }

        doc_ref.update({
            "aulas_dadas": aulas_anteriores + 1,
            "aulas": lista_aulas + [nova_aula]
        })

        return {
            "mensagem": f"✅ Aula registrada com sucesso (total: {aulas_anteriores + 1})",
            "nova_aula": nova_aula
        }

    except Exception as e:
        print("Erro ao registrar aula:", e)
        raise HTTPException(status_code=500, detail="Erro ao registrar aula")

@app.get("/teste", response_class=HTMLResponse)
async def exibir_teste(request: Request):
    return templates.TemplateResponse("teste.html", {"request": request})
    
@app.post("/ver-aulas")
async def ver_aulas(request: Request):
    try:
        dados = await request.json()
        aluno_raw = dados.get("aluno", "")
        if not aluno_raw:
            return JSONResponse(content={"erro": "Nome do aluno ausente"}, status_code=400)

        aluno_normalizado = str(aluno_raw).strip().lower().replace(" ", "")

        db_firestore = firestore.client()
        query = db_firestore.collection("alunos_professor").stream()

        aluno_encontrado = None
        for doc in query:
            dados_doc = doc.to_dict()
            aluno_db = dados_doc.get("aluno", "").strip().lower().replace(" ", "")
            if aluno_db == aluno_normalizado:
                aluno_encontrado = dados_doc
                break

        if not aluno_encontrado:
            return JSONResponse(content={"erro": "Aluno não encontrado"}, status_code=404)

        aulas = aluno_encontrado.get("aulas", [])
        total_dadas = aluno_encontrado.get("aulas_dadas", 0)
        total_previstas = aluno_encontrado.get("total_aulas", 24)
        restantes = max(0, total_previstas - total_dadas)

        return JSONResponse(content={
            "aulas_dadas": total_dadas,
            "restantes": restantes,
            "aulas": aulas
        })

    except Exception as e:
        print("Erro ao buscar aulas:", e)
        return JSONResponse(content={"erro": str(e)}, status_code=500)


@app.get("/listar-alunos")
async def listar_alunos():
    alunos_ref = db.collection("alunos").stream()
    alunos = []

    for doc in alunos_ref:
        dados = doc.to_dict()
        nome = dados.get("nome", "")
        disciplina = dados.get("disciplina", "")
        online = dados.get("online", False)
        vinculado = dados.get("vinculado", False)
        alunos.append({
            "nome": nome,
            "disciplina": disciplina,
            "online": online,
            "vinculado": vinculado
        })

    return alunos

@app.get("/listar-professores-online")
async def listar_professores_online():
    professores = db.collection("professores_online").stream()
    lista = []

    for prof in professores:
        dados = prof.to_dict()
        lista.append({
            "email": dados.get("email", ""),
            "nome": dados.get("nome_completo", ""),  # Novo campo incluído
            "online": dados.get("online", False)
        })

    return lista

@app.get("/listar-chamadas")
async def listar_chamadas():
    chamadas_ref = db.collection("chamadas_ao_vivo").stream()
    lista = []

    for ch in chamadas_ref:
        dados = ch.to_dict()
        lista.append({
            "aluno": dados.get("aluno", ""),
            "professor": dados.get("professor", ""),
            "status": dados.get("status", "")
        })

    return lista


@app.get("/relatorio-aulas")
async def relatorio_aulas():
    relatorio_ref = db.collection("alunos_professor").stream()
    resultado = []

    for doc in relatorio_ref:
        dados = doc.to_dict()
        resultado.append({
            "professor": dados.get("professor", ""),
            "aluno": dados.get("aluno", ""),
            "aulas_dadas": dados.get("aulas_dadas", 0)
        })

    return resultado

@app.get("/alunos-nao-vinculados")
async def listar_alunos_nao_vinculados():
    try:
        alunos_ref = db.collection("alunos") \
                       .where("vinculado", "==", False) \
                       .stream()

        alunos_disponiveis = []
        for doc in alunos_ref:
            dados = doc.to_dict()
            alunos_disponiveis.append({
                "nome": dados.get("nome", ""),
                "disciplina": dados.get("disciplina", ""),
                "bairro": dados.get("bairro", ""),
                "provincia": dados.get("provincia", ""),
                "online": dados.get("online", False)
            })

        return JSONResponse(content=alunos_disponiveis)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"erro": "Erro ao buscar alunos não vinculados", "detalhes": str(e)}
        )


@app.post("/remover-aluno")
async def remover_aluno(request: Request):
    dados = await request.json()
    nome_raw = dados.get("nome", "")
    nome = str(nome_raw).strip()

    if not nome:
        return JSONResponse(content={"erro": "Nome do aluno ausente"}, status_code=400)

    print("🔍 Nome recebido:", nome)

    db = firestore.client()
    docs = db.collection("alunos").where("nome", "==", nome).stream()
    achou = False

    for doc in docs:
        print("📌 Documento encontrado:", doc.id)
        doc.reference.delete()
        achou = True

    if achou:
        return {"mensagem": f"Aluno {nome} removido com sucesso"}
    else:
        print("⚠️ Nenhum aluno encontrado com esse nome.")
        return JSONResponse(content={"erro": "Aluno não encontrado"}, status_code=404)


@app.post("/remover-professor")
async def remover_professor(request: Request):
    dados = await request.json()
    email_raw = dados.get("email", "")
    email = str(email_raw).strip().lower()

    if not email:
        return JSONResponse(content={"erro": "Email do professor ausente"}, status_code=400)

    print("🔍 Email recebido:", email_raw)
    print("🔍 Email normalizado:", email)

    db = firestore.client()
    docs = db.collection("professores_online").where("email", "==", email).stream()
    achou = False

    for doc in docs:
        print("📌 Documento encontrado:", doc.id)
        doc.reference.delete()
        achou = True

    # Também remove da coleção professores_online2, onde o email é o ID
    try:
        db.collection("professores_online2").document(email).delete()
        print("🗑️ Removido de professores_online2")
    except Exception as e:
        print("⚠️ Erro ao remover de professores_online2:", e)

    if achou:
        return {"mensagem": f"Professor {email_raw} removido com sucesso"}
    else:
        return JSONResponse(content={"erro": "Professor não encontrado"}, status_code=404)


@app.post("/enviar-mensagem-professor")
async def enviar_mensagem_professor(request: Request):
    dados = await request.json()
    destino = dados.get("email", "").strip().lower()
    texto = dados.get("mensagem", "").strip()

    if not destino or not texto:
        return {"erro": "Email e mensagem são obrigatórios"}

    db_firestore = firestore.client()
    doc_ref = db_firestore.collection("mensagens_professores").document(destino)

    # Buscar mensagens anteriores (se existirem)
    doc = doc_ref.get()
    mensagens = doc.to_dict().get("mensagens", []) if doc.exists else []

    # Adicionar nova mensagem com data
    nova_mensagem = {
        "texto": texto,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    mensagens.append(nova_mensagem)

    # Atualizar no Firestore
    doc_ref.set({"mensagens": mensagens})

    return {"mensagem": "Mensagem enviada com sucesso"}

@app.get("/mensagens-professor/{email}")
async def mensagens_professor(email: str):
    email = email.strip().lower()
    db_firestore = firestore.client()
    doc_ref = db_firestore.collection("mensagens_professores").document(email)
    doc = doc_ref.get()
    if doc.exists:
        return {"mensagens": doc.to_dict().get("mensagens", [])}
    return {"mensagens": []}

@app.post("/aulas_do_dia")
async def aulas_do_dia(request: Request):
    try:
        dados = await request.json()
        professor_email = dados.get("professor_email", "").strip().lower()

        if not professor_email:
            return JSONResponse(content={"erro": "E-mail do professor é obrigatório."}, status_code=400)

        dias_em_portugues = {
            "monday": "segunda-feira",
            "tuesday": "terça-feira",
            "wednesday": "quarta-feira",
            "thursday": "quinta-feira",
            "friday": "sexta-feira",
            "saturday": "sábado",
            "sunday": "domingo"
        }

        dia_em_ingles = datetime.now().strftime('%A').lower()
        dia_hoje = dias_em_portugues.get(dia_em_ingles)

        aulas_do_dia = []

        docs = db.collection("alunos_professor").where("professor", "==", professor_email).stream()

        for doc in docs:
            dados = doc.to_dict()
            aluno_nome = dados.get("aluno", "")
            horario = dados.get("horario", {})

            horarios_hoje = horario.get(dia_hoje, [])

            if horarios_hoje:
                aulas_do_dia.append({
                    "aluno": aluno_nome,
                    "horarios": horarios_hoje,
                    "preco": "Kz 1.250,00"
                })

        return JSONResponse(content={"aulas": aulas_do_dia})

    except Exception as e:
        print("Erro ao obter aulas do dia:", e)
        return JSONResponse(content={"erro": "Erro interno ao obter aulas do dia."}, status_code=500)

@app.post("/aulas_da_semana")
async def aulas_da_semana(request: Request):
    try:
        dados = await request.json()
        professor_email = dados.get("professor_email", "").strip().lower()

        if not professor_email:
            return JSONResponse(content={"erro": "E-mail do professor é obrigatório."}, status_code=400)

        dias_ordenados = [
            "segunda-feira", "terça-feira", "quarta-feira",
            "quinta-feira", "sexta-feira", "sábado", "domingo"
        ]

        aulas_semana = {dia: [] for dia in dias_ordenados}

        docs = db.collection("alunos_professor").where("professor", "==", professor_email).stream()

        for doc in docs:
            dados = doc.to_dict()
            aluno_nome = dados.get("aluno", "")
            horario = dados.get("horario", {})

            for dia, lista in horario.items():
                dia_formatado = dia.strip().lower()
                if dia_formatado in aulas_semana:
                    aulas_semana[dia_formatado].append({
                        "aluno": aluno_nome,
                        "horarios": lista,
                        "preco": "Kz 1.250,00"
                    })

        aulas_semana_filtrado = {
            dia.title(): lista for dia, lista in aulas_semana.items() if lista
        }

        return JSONResponse(content={"aulas": aulas_semana_filtrado})

    except Exception as e:
        print("Erro ao obter aulas da semana:", e)
        return JSONResponse(content={"erro": "Erro interno ao obter aulas da semana."}, status_code=500)

class HorarioEnvio(BaseModel):
    aluno_nome: str
    professor_email: str
    horario: dict

@app.post("/enviar-horario")
async def enviar_horario(request: Request):
    try:
        dados = await request.json()
        aluno_nome = dados.get("aluno_nome", "").strip().lower()
        professor_email = dados.get("professor_email", "").strip().lower()
        horario = dados.get("horario")  # dict esperado

        if not aluno_nome or not professor_email or not horario:
            return JSONResponse(status_code=400, content={"detail": "Dados incompletos."})

        doc_id = f"{aluno_nome}_{professor_email}"

        print(f"🟢 Vai gravar EM alunos → nome_normalizado: {aluno_nome} | Dados: {horario}")

        # ✅ Atualiza o campo 'horario' na coleção 'alunos' usando 'nome_normalizado'
        alunos_query = db.collection("alunos") \
            .where("nome_normalizado", "==", aluno_nome) \
            .limit(1) \
            .stream()

        aluno_found = False
        for aluno_doc in alunos_query:
            aluno_doc.reference.update({"horario": horario})
            aluno_found = True
            print(f"✅ Horário atualizado na coleção alunos → ID: {aluno_doc.id}")
            break

        if not aluno_found:
            print("⚠️ Aluno não encontrado na coleção alunos para atualizar horário.")

        # Atualizar também o campo horario na coleção alunos_professor
        query = db.collection("alunos_professor") \
            .where("professor", "==", professor_email) \
            .where("aluno", "==", aluno_nome) \
            .limit(1) \
            .stream()

        doc_found = False
        for doc in query:
            doc.reference.update({"horario": horario})
            doc_found = True
            print(f"✅ Horário também atualizado em alunos_professor → ID: {doc.id}")
            break

        if not doc_found:
            print("⚠️ Vínculo não encontrado na coleção alunos_professor para atualizar horário.")

        return {"mensagem": "Horário enviado e atualizado com sucesso."}

    except Exception as e:
        print("🔴 Erro ao enviar horário:", e)
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/ver-horario-aluno/{nome}")
async def ver_horario_aluno(nome: str):
    try:
        nome = nome.strip()
        query = db.collection("alunos").where("nome", "==", nome).limit(1).stream()
        for doc in query:
            dados = doc.to_dict()
            if "horario" in dados:
                return {"horario": dados["horario"]}
            else:
                return {"erro": "Horário não encontrado para este aluno."}
        return {"erro": "Aluno não encontrado."}
    except Exception as e:
        return {"erro": f"Erro ao buscar horário: {str(e)}"}
        
@app.get("/admin", response_class=HTMLResponse)
async def painel_admin(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

class EntradaItem(BaseModel):
    nome: str
    preco: float
    quantidade: int

class CustoItem(BaseModel):
    nome: str
    valor: float

class VendaItem(BaseModel):
    nome: str
    preco: float  # Preço de venda
    quantidade: int

# ROTA HTML
@app.get("/registro", response_class=HTMLResponse)
async def exibir_registro(request: Request):
    return templates.TemplateResponse("registro.html", {"request": request})

# ENTRADA DE PRODUTOS
@app.post("/registrar-entrada")
async def registrar_entrada(itens: List[EntradaItem]):
    total = 0
    for item in itens:
        subtotal = item.preco * item.quantidade
        total += subtotal

        # Verificar se o produto já existe
        produtos = db.collection("estoque").where("nome", "==", item.nome).limit(1).stream()
        produto_existente = next(produtos, None)

        if produto_existente:
            dados = produto_existente.to_dict()
            nova_qtd = dados["quantidade"] + item.quantidade
            db.collection("estoque").document(produto_existente.id).update({
                "quantidade": nova_qtd,
                "preco": item.preco  # Atualiza preço de custo se for diferente
            })
        else:
            db.collection("estoque").add({
                "nome": item.nome,
                "preco": item.preco,
                "quantidade": item.quantidade
            })

        db.collection("entradas").add({
            "nome": item.nome,
            "preco": item.preco,
            "quantidade": item.quantidade,
            "subtotal": subtotal
        })

    return {"status": "sucesso", "total_entrada": total}

# CUSTOS OPERACIONAIS
@app.post("/registrar-custo")
async def registrar_custo(custos: List[CustoItem]):
    total = 0
    for custo in custos:
        total += custo.valor
        db.collection("custos").add({
            "nome": custo.nome,
            "valor": custo.valor
        })
    return {"status": "sucesso", "total_custos": total}

# VENDA DE PRODUTOS
@app.post("/registrar-venda")
async def registrar_venda(vendas: List[VendaItem]):
    total_lucro = 0
    total_vendas = 0

    for venda in vendas:
        produto_ref = db.collection("estoque").where("nome", "==", venda.nome).limit(1).stream()
        produto = next(produto_ref, None)

        if not produto:
            return JSONResponse(status_code=404, content={"erro": f"Produto '{venda.nome}' não encontrado no estoque."})

        dados = produto.to_dict()
        preco_compra = dados["preco"]
        qtd_estoque = dados["quantidade"]

        if venda.quantidade > qtd_estoque:
            return JSONResponse(status_code=400, content={"erro": f"Quantidade insuficiente para o produto '{venda.nome}'."})

        lucro_unitario = venda.preco - preco_compra
        lucro_total = lucro_unitario * venda.quantidade
        total_lucro += lucro_total
        total_vendas += venda.preco * venda.quantidade

        # Subtrair do estoque
        nova_qtd = qtd_estoque - venda.quantidade
        db.collection("estoque").document(produto.id).update({
            "quantidade": nova_qtd
        })

        # Registrar venda
        db.collection("vendas").add({
            "nome": venda.nome,
            "preco_venda": venda.preco,
            "quantidade": venda.quantidade,
            "lucro_total": lucro_total
        })

    return {
        "status": "sucesso",
        "total_vendas": total_vendas,
        "lucro_total": total_lucro
    }

# LUCRO GERAL
@app.get("/calcular-lucro")
async def calcular_lucro():
    entradas = db.collection("entradas").stream()
    vendas = db.collection("vendas").stream()
    custos = db.collection("custos").stream()

    total_entrada = sum(e.to_dict().get("subtotal", 0) for e in entradas)
    total_venda = sum(v.to_dict().get("preco_venda", 0) * v.to_dict().get("quantidade", 0) for v in vendas)
    total_lucro = sum(v.to_dict().get("lucro_total", 0) for v in vendas)
    total_custos = sum(c.to_dict().get("valor", 0) for c in custos)

    lucro_liquido = total_lucro - total_custos

    return {
        "total_entrada": total_entrada,
        "total_vendas": total_venda,
        "total_lucro_bruto": total_lucro,
        "total_custos": total_custos,
        "lucro_liquido": lucro_liquido
    }


