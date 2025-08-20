import datetime
from time import sleep
import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd
import datetime


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


def get_auth_header():
    return {'Authorization': f'Bearer {gerar_token()}'}


def listar_responsaveis():
    url = f"{API_BASE_URL}/tarefas/responsaveis"
    response = requests.get(url, headers=get_auth_header())
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
        response = requests.get(url, headers=get_auth_header())
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
        response = requests.get(url, headers=get_auth_header())
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


def determinar_status(tarefa):
    data_conclusao = tarefa.get('dataConclusao')
    data_acao = tarefa.get('dataAcao')
    data_atual = datetime.datetime.now().date()

    # 1º - Verifica se foi CONCLUÍDA (dataConclusao != null)
    if data_conclusao not in [None, '', 'null', 'NULL']:
        return 'Concluída'

    # 2º - Verifica se está ATRASADA ou PENDENTE
    if data_acao not in [None, '', 'null', 'NULL']:
        # Converte string para date se necessário
        if isinstance(data_acao, str):
            try:
                data_acao = datetime.fromisoformat(data_acao.replace('Z', '+00:00')).date()
            except:
                return 'Pendente'  # Se falhar na conversão

        # Compara as datas
        if isinstance(data_acao, datetime.date):
            if data_acao < data_atual:
                return 'Atrasada'
            elif data_acao > data_atual:
                return 'Pendente'

    # 3º - Default (quando não tem datas ou não conseguiu converter)
    return 'Pendente'


def formatar_data(data_string):
    if not data_string or data_string in [None, '', 'null', 'NULL']:
        return ''

    if isinstance(data_string, str):
        try:
            data_obj = datetime.fromisoformat(data_string.replace('Z', '+00:00'))
            return data_obj.strftime('%d/%m/%Y')
        except:
            return data_string
    return data_string



def get_tarefas_dataframe():
    usuarios = listar_responsaveis()
    print(f"Encontrados {len(usuarios)} usuários")

    usuarios_ignorar = [112751, 121001, 112752]  # IDs dos usuários que não trabalham mais

    todas_tarefas = []

    for usuario in usuarios:
        usuario_id = usuario.get('usuario')
        usuario_nome = usuario.get('nome')

        if usuario_id in usuarios_ignorar:
            print(f"Ignorando usuário: {usuario_nome} (ID: {usuario_id})")
            continue

        print(f"Buscando tarefas para: {usuario_nome} (ID: {usuario_id})")


        obrigacoes = listar_obrigacoes(usuario_id)
        for obrigacao in obrigacoes:
            if isinstance(obrigacao, dict):
                tarefa = obrigacao.copy()
                tarefa['usuario_id'] = usuario_id
                tarefa['usuario_nome'] = usuario_nome
                tarefa['tipo'] = 'Obrigacao'
                todas_tarefas.append(tarefa)


        solicitacoes = listar_solicitacoes(usuario_id)
        for solicitacao in solicitacoes:
            if isinstance(solicitacao, dict):
                tarefa = solicitacao.copy()
                tarefa['usuario_id'] = usuario_id
                tarefa['usuario_nome'] = usuario_nome
                tarefa['tipo'] = 'Solicitacao'
                todas_tarefas.append(tarefa)

    print(f"Total de tarefas encontradas: {len(todas_tarefas)}")


    dados_planilha = []

    for tarefa in todas_tarefas:
        status = determinar_status(tarefa)
        data_acao = formatar_data(tarefa.get('dataAcao', ''))
        data_conclusao = formatar_data(tarefa.get('dataConclusao', ''))
        data_vencimento = formatar_data(tarefa.get('dataVencimento', ''))

        dados_planilha.append({
            'ID': tarefa.get('id'),
            'Tipo': tarefa.get('tipo', ''),
            'Status': status,
            'Data_Acao': data_acao,
            'Data_Conclusao': data_conclusao,
            'Data_Vencimento': data_vencimento,
            'Responsavel_ID': tarefa.get('usuario_id'),
            'Responsavel_Nome': tarefa.get('usuario_nome', ''),
            'Data_Criacao': formatar_data(tarefa.get('dataCriacao', ''))
        })


    df = pd.DataFrame(dados_planilha)


    df = df.sort_values('Responsavel_Nome')

    return df


def tarefas_responsavel():
    df = get_tarefas_dataframe()

    if len(df) > 0:

        with pd.ExcelWriter('planilha_tarefas.xlsx', engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Tarefas', index=False)
        print("Planilha salva em 'planilha_tarefas.xlsx'")
    else:
        print("Nenhuma tarefa encontrada")

    return df



def main():

    return get_tarefas_dataframe()


if __name__ == '__main__':
    df = main()
    print(f"DataFrame criado com {len(df)} linhas")

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)

    print(df)


    # arquivo_excel = 'planilha_tarefas.xlsx'
    # with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
    #     df.to_excel(writer, sheet_name='Tarefas', index=False)
    # print(f"Planilha salva em '{arquivo_excel}'")