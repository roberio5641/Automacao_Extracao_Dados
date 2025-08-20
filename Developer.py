import datetime
from time import sleep
import requests
from dotenv import load_dotenv
import os
import json
import csv
from datetime import datetime

load_dotenv()

DB_CLIENT_ID = os.getenv("DB_CLIENT_ID")
DB_CLIENT_SECRET = os.getenv("DB_CLIENT_SECRET")

API_BASE_URL = "https://api.gclick.com.br"


def gerar_token():
    url = f"{API_BASE_URL}/oauth/token"
    payload = {
        'client_id': DB_CLIENT_ID,
        'client_secret': DB_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    Token = response.json().get('access_token')
    if not Token:
        raise ValueError('Token de acesso não encontrado na resposta da API')
    return Token


AUTH_HEADER = {'Authorization': f'Bearer {gerar_token()}'}


def listar_responsaveis():
    url = f"{API_BASE_URL}/tarefas/responsaveis"
    response = requests.get(url, headers=AUTH_HEADER)
    response.raise_for_status()
    data = response.json()
    usuarios_unicos = {}

    if isinstance(data, dict) and 'content' in data:
        responsaveis = data['content']
    elif isinstance(data, list):
        responsaveis = data
    else:
        return []

    for responsavel in responsaveis:
        if isinstance(responsavel, dict):
            usuario_id = responsavel.get('usuario')
            nome = responsavel.get('nome')
            if usuario_id and nome and usuario_id not in usuarios_unicos:
                usuarios_unicos[usuario_id] = {
                    'usuario': usuario_id,
                    'nome': nome,
                }
    return list(usuarios_unicos.values())


def listar_obrigacoes(usuario_id):
    obrigacoes = []
    page = 0
    size = 100

    while True:
        url = f"{API_BASE_URL}/tarefas?categoria=Obrigacao&responsaveisIds={usuario_id}&page={page}&size={size}"
        response = requests.get(url, headers=AUTH_HEADER)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and 'content' in data:
            content = data['content']
            obrigacoes.extend(content)

            if data.get('last', False) or len(content) == 0:
                break
            page += 1
        else:
            break

    return obrigacoes


def listar_solicitacoes(usuario_id):
    solicitacoes = []
    page = 0
    size = 100

    while True:
        url = f"{API_BASE_URL}/tarefas?categoria=Solicitacao&responsaveisIds={usuario_id}&page={page}&size={size}"
        response = requests.get(url, headers=AUTH_HEADER)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and 'content' in data:
            content = data['content']
            solicitacoes.extend(content)

            if data.get('last', False) or len(content) == 0:
                break
            page += 1
        else:
            break

    return solicitacoes


def gerar_planilha(todas_tarefas):
    if not todas_tarefas:
        print("Nenhuma tarefa para gerar planilha")
        return

    # Ordena as tarefas por responsável
    todas_tarefas.sort(key=lambda x: x.get('nome', ''))

    # Cria o arquivo CSV
    with open('planilha_tarefas.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Ação', 'Conclusão','Vencimento', 'Responsáveis', 'Título', 'Tipo', 'ID']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for tarefa in todas_tarefas:
            data_acao = tarefa.get('dataAcao', '')
            data_conclusao = tarefa.get('dataConclusao', '')
            data_vencimento = tarefa.get(tarefa.get('dataVencimento', ''))
            responsavel = tarefa.get('nome', '')
            tipo = tarefa.get('tipo', '')
            tarefa_id = tarefa.get('id', '')

            # Formata as datas se existirem
            if data_acao and isinstance(data_acao, str):
                try:
                    data_acao_obj = datetime.fromisoformat(data_acao.replace('Z', '+00:00'))
                    data_acao = data_acao_obj.strftime('%d/%m/%Y')
                except:
                    pass

            if data_conclusao and isinstance(data_conclusao, str):
                try:
                    data_conclusao_obj = datetime.fromisoformat(data_conclusao.replace('Z', '+00:00'))
                    data_conclusao = data_conclusao_obj.strftime('%d/%m/%Y')
                except:
                    pass

            if data_vencimento and isinstance(data_vencimento, str):
                try:
                    data_vencimento_obj = datetime.fromisoformat(data_vencimento.replace('Z', '+00:00'))
                    data_vencimento = data_vencimento_obj.strftime('%d/%m/%Y')
                except:
                    pass

            writer.writerow({
                'Ação': data_acao,
                'Conclusão': data_conclusao,
                'Vencimento' : data_vencimento,
                'Responsáveis': responsavel,
                'Tipo': tipo,
                'ID': tarefa_id
            })

    print("Planilha gerada em 'planilha_tarefas.csv'")


def tarefas_responsavel():
    usuarios = listar_responsaveis()
    print(f"Encontrados {len(usuarios)} usuários")

    usuarios_ignorar = [112750, 121001, 112752]  # IDs dos usuários que não trabalham mais

    todas_tarefas = []

    for usuario in usuarios:
        usuario_id = usuario.get('usuario')
        usuario_nome = usuario.get('nome')

        if usuario_id in usuarios_ignorar:
            print(f"\nIgnorando usuário: {usuario_nome} (ID: {usuario_id})")
            continue

        print(f"\nBuscando tarefas para: {usuario_nome} (ID: {usuario_id})")

        obrigacoes = listar_obrigacoes(usuario_id)
        print(f"Obrigações: {len(obrigacoes)}")

        solicitacoes = listar_solicitacoes(usuario_id)
        print(f"Solicitações: {len(solicitacoes)}")

        for obrigacao in obrigacoes:
            if isinstance(obrigacao, dict):
                tarefa = obrigacao.copy()
                tarefa['usuario'] = usuario_id
                tarefa['nome'] = usuario_nome
                tarefa['tipo'] = 'Obrigacao'
                todas_tarefas.append(tarefa)

        for solicitacao in solicitacoes:
            if isinstance(solicitacao, dict):
                tarefa = solicitacao.copy()
                tarefa['usuario'] = usuario_id
                tarefa['nome'] = usuario_nome
                tarefa['tipo'] = 'Solicitacao'
                todas_tarefas.append(tarefa)

    print(f"\nTotal de tarefas encontradas: {len(todas_tarefas)}")

    if todas_tarefas:
        with open('tarefas_usuario.json', 'w', encoding='UTF-8') as f:
            json.dump(todas_tarefas, f, indent=2, ensure_ascii=False, default=str)
        print("Resultados salvos em 'tarefas_usuario.json'")

        # Gera a planilha
        gerar_planilha(todas_tarefas)
    else:
        print("Nenhuma Tarefa encontrada")


def main():
    print("Inicializando...")
    tarefas_responsavel()


if __name__ == '__main__':
    main()