# utils.py

import json

# Função para carregar os dados dos professores a partir de um arquivo JSON
def carregar_professores(caminho_arquivo="professores.json"):
    try:
        # Tenta abrir o arquivo JSON e carregar os dados
        with open(caminho_arquivo, "r") as file:
            professores = json.load(file)
        return professores  # Retorna a lista de professores
    except FileNotFoundError:
        print(f"O arquivo {caminho_arquivo} não foi encontrado.")
        return []  # Retorna uma lista vazia se o arquivo não for encontrado
    except json.JSONDecodeError:
        print(f"O arquivo {caminho_arquivo} não está no formato correto.")
        return []  # Retorna uma lista vazia se houver erro de leitura do JSON
