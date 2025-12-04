"""
Sistema de Mapeamento de Pontos de Ônibus - Maceió/AL
VERSÃO 2.0: Com validação de seções ATIVAS no PDF
Autor: Sistema de Mapeamento
Data: 2024
"""

import pdfplumber
import pandas as pd
import folium
import re
from pathlib import Path
from folium import plugins

# ============================================================================
# CONFIGURAÇÕES DO SISTEMA
# ============================================================================

# Coordenadas do centro de Maceió
MACEIO_CENTRO = [-9.6498, -35.7089]

# Limites geográficos de Maceió (validação)
LIMITES_MACEIO = {
    'lat_min': -9.8,
    'lat_max': -9.4,
    'lon_min': -35.9,
    'lon_max': -35.6
}

# Cores para cada empresa
CORES_EMPRESAS = {
    'Real': '#FF0000',        # Vermelho
    'SaoFrancisco': '#0000FF', # Azul
    'CidadeMaceio': '#FFFF00'  # Amarelo
}

# Configuração dos PDFs a serem processados
PDFS_PARA_PROCESSAR = [
    {
        'caminho': 'pontos_real.pdf',
        'empresa': 'Real',
        'cor': CORES_EMPRESAS['Real']
    },
    {
        'caminho': 'empresa_saoFran.pdf',
        'empresa': 'SaoFrancisco', 
        'cor': CORES_EMPRESAS['SaoFrancisco']
    },
    {
        'caminho': 'pontos_Maceio.pdf',
        'empresa': 'CidadeMaceio',
        'cor': CORES_EMPRESAS['CidadeMaceio']
    }
]

# ============================================================================
# FUNÇÕES DE EXTRACÇÃO COM VALIDAÇÃO "ATIVO"
# ============================================================================

def validar_secao_ativa(texto_secao):
    """
    Valida se uma seção do PDF está marcada como ATIVA.
    
    Procura pelo padrão:
    "Ativo:" seguido de "Sim" (ou "Sim Sim" conforme mencionado)
    
    Parâmetros:
    -----------
    texto_secao : str
        Texto completo de uma seção do PDF
    
    Retorna:
    --------
    bool
        True se a seção está ativa, False caso contrário
    """
    # Padrões para encontrar "Ativo: Sim"
    padroes = [
        r'Ativo:\s*Sim\s+Sim',    # Ativo: Sim Sim (dois Sim)
        r'Ativo:\s*Sim',          # Ativo: Sim (um Sim)
        r'Ativo:\s*SIM',          # Ativo: SIM (maiúsculo)
        r'Ativo:\s*sim',          # Ativo: sim (minúsculo)
    ]
    
    for padrao in padroes:
        if re.search(padrao, texto_secao, re.IGNORECASE):
            return True
    
    return False

def extrair_secoes_pdf(texto_completo):
    """
    Divide o texto do PDF em seções baseado em marcadores.
    
    Parâmetros:
    -----------
    texto_completo : str
        Texto completo extraído do PDF
    
    Retorna:
    --------
    list
        Lista de strings, cada uma é uma seção
    """
    # Padrão para identificar início de nova seção
    # Procura por "Atendimento Principal:" ou "Linha:"
    padrao_inicio_secao = r'(?:Atendimento Principal:|Linha:)'
    
    # Divide o texto em seções
    secoes = re.split(padrao_inicio_secao, texto_completo)
    
    # A primeira parte geralmente é cabeçalho/pré-texto
    # Adiciona o marcador de volta ao início de cada seção
    secoes_validas = []
    for i, secao in enumerate(secoes):
        if i == 0:
            continue  # Pula o texto antes da primeira seção
        secoes_validas.append(secao.strip())
    
    return secoes_validas

def extrair_coordenadas_pdf_com_ativo(pdf_path, empresa_nome):
    """
    Extrai coordenadas de um PDF, filtrando apenas seções ATIVAS.
    
    Parâmetros:
    -----------
    pdf_path : str
        Caminho do arquivo PDF
    empresa_nome : str
        Nome da empresa
    
    Retorna:
    --------
    pd.DataFrame
        DataFrame com pontos APENAS de seções ativas
    """
    print(f"\n{'='*60}")
    print(f"📊 PROCESSANDO: {pdf_path}")
    print(f"🏢 EMPRESA: {empresa_nome}")
    print(f"{'='*60}")
    
    dados = []
    total_secoes = 0
    secoes_ativas = 0
    secoes_inativas = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extrai texto de TODAS as páginas
            texto_completo = ""
            for pagina_num, pagina in enumerate(pdf.pages, 1):
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
            
            if not texto_completo:
                print("⚠️ Nenhum texto encontrado no PDF")
                return pd.DataFrame()
            
            # Divide o PDF em seções
            secoes = extrair_secoes_pdf(texto_completo)
            total_secoes = len(secoes)
            
            print(f"📑 Total de seções encontradas: {total_secoes}")
            
            # Processa cada seção
            for idx, secao in enumerate(secoes, 1):
                print(f"\n  🔍 Analisando seção {idx}/{total_secoes}...")
                
                # Valida se a seção está ATIVA
                if validar_secao_ativa(secao):
                    secoes_ativas += 1
                    print(f"    ✅ SEÇÃO ATIVA - Extraindo pontos...")
                    
                    # Extrai coordenadas desta seção ativa
                    pontos_secao = extrair_coordenadas_secao(secao, empresa_nome, idx)
                    
                    if pontos_secao:
                        dados.extend(pontos_secao)
                        print(f"    📍 {len(pontos_secao)} pontos extraídos desta seção")
                    else:
                        print(f"    ⚠️ Nenhum ponto válido encontrado nesta seção ativa")
                else:
                    secoes_inativas += 1
                    print(f"    ❌ SEÇÃO INATIVA - Ignorando...")
            
            # Cria DataFrame
            if dados:
                df = pd.DataFrame(dados, columns=[
                    'empresa', 'codigo', 'endereco', 
                    'latitude', 'longitude', 'pagina', 'secao'
                ])
                
                # Remove duplicatas baseadas em coordenadas
                df = df.drop_duplicates(subset=['latitude', 'longitude'])
                
                # Estatísticas
                print(f"\n{'='*60}")
                print(f"📈 RESULTADO FINAL:")
                print(f"   Total de seções: {total_secoes}")
                print(f"   Seções ATIVAS: {secoes_ativas}")
                print(f"   Seções INATIVAS: {secoes_inativas}")
                print(f"   Pontos válidos extraídos: {len(df)}")
                print(f"{'='*60}")
                
                return df
            else:
                print("⚠️ Nenhum ponto válido encontrado em seções ativas")
                return pd.DataFrame()
                
    except Exception as e:
        print(f"❌ ERRO ao processar PDF: {e}")
        return pd.DataFrame()

def extrair_coordenadas_secao(texto_secao, empresa_nome, num_secao):
    """
    Extrai coordenadas de uma seção específica do PDF.
    
    Parâmetros:
    -----------
    texto_secao : str
        Texto de uma seção do PDF
    empresa_nome : str
        Nome da empresa
    num_secao : int
        Número da seção
    
    Retorna:
    --------
    list
        Lista de dicionários com pontos encontrados
    """
    pontos = []
    
    # Padrões para encontrar coordenadas
    padroes_coordenadas = [
        # Padrão 1: -9,53802 -35,78683 (vírgula como separador decimal)
        r'(-?\d{1,2}[,.]\d+)\s+(-?\d{1,2}[,.]\d+)',
        
        # Padrão 2: -9.53802 -35.78683 (ponto como separador decimal)
        r'(-?\d{1,2}\.\d+)\s+(-?\d{1,2}\.\d+)'
    ]
    
    # Procura por todas as coordenadas no texto da seção
    for padrao in padroes_coordenadas:
        matches = re.findall(padrao, texto_secao)
        
        for match in matches:
            try:
                lat_str, lon_str = match
                
                # Converte para float (substitui vírgula por ponto se necessário)
                lat = float(lat_str.replace(',', '.'))
                lon = float(lon_str.replace(',', '.'))
                
                # Valida se está dentro dos limites de Maceió
                if (LIMITES_MACEIO['lat_min'] < lat < LIMITES_MACEIO['lat_max'] and
                    LIMITES_MACEIO['lon_min'] < lon < LIMITES_MACEIO['lon_max']):
                    
                    # Tenta extrair código do ponto (ex: PN987, PP52)
                    codigo = extrair_codigo_ponto(texto_secao, lat, lon)
                    
                    # Tenta extrair endereço (pega contexto antes da coordenada)
                    endereco = extrair_endereco(texto_secao, lat_str, lon_str)
                    
                    ponto = {
                        'empresa': empresa_nome,
                        'codigo': codigo,
                        'endereco': endereco[:100],  # Limita a 100 caracteres
                        'latitude': lat,
                        'longitude': lon,
                        'pagina': 1,  # Como estamos processando texto completo, usamos 1
                        'secao': num_secao
                    }
                    
                    pontos.append(ponto)
                    
            except (ValueError, TypeError) as e:
                continue  # Ignora coordenadas que não podem ser convertidas
    
    return pontos

def extrair_codigo_ponto(texto_secao, lat, lon):
    """
    Tenta extrair o código do ponto (ex: PN987) próximo à coordenada.
    """
    # Padrão para códigos de ponto (ex: PN987, PP52, BR6, PONTO123)
    padroes_codigo = [
        r'([A-Z]{2,}\d+)',          # PN987, PP52
        r'(PONTO\s*\d+)',           # PONTO 123
        r'(PP\s*\d+)',              # PP 52
        r'(PN\s*\d+)',              # PN 987
    ]
    
    for padrao in padroes_codigo:
        matches = re.findall(padrao, texto_secao)
        if matches:
            return matches[0].replace(' ', '')  # Remove espaços
    
    return f"Ponto_{int(lat*10000)}_{int(lon*10000)}"  # Código gerado

def extrair_endereco(texto_secao, lat_str, lon_str):
    """
    Tenta extrair endereço próximo à coordenada.
    """
    # Procura o contexto antes da coordenada
    padrao_coord = re.escape(f"{lat_str} {lon_str}")
    match = re.search(f'(.{{0,100}}){padrao_coord}', texto_secao)
    
    if match:
        contexto = match.group(1).strip()
        # Remove números e caracteres especiais do início
        contexto_limpo = re.sub(r'^[\d\s\-\.]+', '', contexto)
        if contexto_limpo:
            return contexto_limpo
    
    return "Endereço não identificado"

# ============================================================================
# FUNÇÕES DE MAPEAMENTO (MANTIDAS DO CÓDIGO ANTERIOR)
# ============================================================================

def criar_mapa_folium(df, empresa_nome, output_file):
    """
    Cria um mapa HTML interativo com os pontos de UMA empresa.
    """
    if df.empty:
        print(f"⚠️ Nenhum dado para {empresa_nome}. Mapa não criado.")
        return None
    
    print(f"\n🗺️ CRIANDO MAPA INDIVIDUAL: {empresa_nome}")
    print(f"   📍 Total de pontos no mapa: {len(df)}")
    
    # Cria o mapa centrado em Maceió
    mapa = folium.Map(
        location=MACEIO_CENTRO,
        zoom_start=12,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Adiciona plugin de tela cheia
    plugins.Fullscreen().add_to(mapa)
    
    # Cor da empresa
    cor = CORES_EMPRESAS.get(empresa_nome, '#808080')  # Cinza se não encontrado
    
    # Adiciona cada ponto ao mapa
    for _, ponto in df.iterrows():
        # Cria popup HTML
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="color: {cor}; margin: 5px 0;">{ponto['empresa']}</h4>
            <hr style="margin: 5px 0;">
            <b>Código:</b> {ponto['codigo']}<br>
            <b>Latitude:</b> {ponto['latitude']:.5f}<br>
            <b>Longitude:</b> {ponto['longitude']:.5f}<br>
            <b>Seção:</b> {ponto['secao']}<br>
            <hr style="margin: 5px 0;">
            <small><b>Endereço:</b><br>{ponto['endereco']}</small>
        </div>
        """
        
        # Cria marcador circular
        folium.CircleMarker(
            location=[ponto['latitude'], ponto['longitude']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{ponto['codigo']} - {ponto['empresa']}",
            color='white',
            fillColor=cor,
            fillOpacity=0.8,
            weight=2
        ).add_to(mapa)
    
    # Adiciona legenda
    legenda_html = f"""
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        width: 180px; 
        height: auto;
        background-color: white;
        border: 2px solid grey;
        border-radius: 5px;
        padding: 10px;
        font-size: 14px;
        z-index: 9999;
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
    ">
        <h4 style="margin-top: 0;">{empresa_nome}</h4>
        <hr>
        <b>Total de Pontos:</b> {len(df)}<br>
        <b>Cor:</b> <span style="color: {cor}">●</span><br>
        <small><i>Clique nos pontos para detalhes</i></small>
    </div>
    """
    
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    
    # Salva o mapa
    mapa.save(output_file)
    print(f"   ✅ Mapa salvo: {output_file}")
    
    return mapa

def criar_mapa_consolidado(lista_dfs, output_file_html, output_file_csv):
    """
    Cria um mapa HTML consolidado com TODAS as empresas.
    """
    print(f"\n{'='*60}")
    print("🗺️ CRIANDO MAPA CONSOLIDADO COM TODAS EMPRESAS")
    print(f"{'='*60}")
    
    # Combina todos os DataFrames
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    if df_consolidado.empty:
        print("⚠️ Nenhum dado para consolidar. Mapa não criado.")
        return None
    
    # Salva CSV consolidado
    df_consolidado.to_csv(output_file_csv, index=False, encoding='utf-8-sig')
    print(f"📁 CSV consolidado salvo: {output_file_csv}")
    print(f"📍 Total de pontos no consolidado: {len(df_consolidado)}")
    
    # Cria o mapa
    mapa = folium.Map(
        location=MACEIO_CENTRO,
        zoom_start=12,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Plugin tela cheia
    plugins.Fullscreen().add_to(mapa)
    
    # Cria grupos para cada empresa (para controle de camadas)
    grupos = {}
    
    for empresa in CORES_EMPRESAS.keys():
        grupos[empresa] = folium.FeatureGroup(name=empresa)
    
    # Adiciona pontos ao mapa
    empresas_no_mapa = set()
    
    for _, ponto in df_consolidado.iterrows():
        empresa = ponto['empresa']
        empresas_no_mapa.add(empresa)
        
        cor = CORES_EMPRESAS.get(empresa, '#808080')
        
        # Popup HTML
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="color: {cor}; margin: 5px 0;">{empresa}</h4>
            <hr style="margin: 5px 0;">
            <b>Código:</b> {ponto['codigo']}<br>
            <b>Latitude:</b> {ponto['latitude']:.5f}<br>
            <b>Longitude:</b> {ponto['longitude']:.5f}<br>
            <b>Seção:</b> {ponto['secao']}<br>
            <hr style="margin: 5px 0;">
            <small><b>Endereço:</b><br>{ponto['endereco']}</small>
        </div>
        """
        
        # Cria marcador
        marker = folium.CircleMarker(
            location=[ponto['latitude'], ponto['longitude']],
            radius=7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{ponto['codigo']} - {empresa}",
            color='white',
            fillColor=cor,
            fillOpacity=0.8,
            weight=1.5
        )
        
        marker.add_to(grupos[empresa])
    
    # Adiciona grupos ao mapa
    for empresa, grupo in grupos.items():
        grupo.add_to(mapa)
    
    # Adiciona controle de camadas
    folium.LayerControl(collapsed=False).add_to(mapa)
    
    # Estatísticas por empresa
    stats_html = ""
    for empresa in sorted(empresas_no_mapa):
        count = len(df_consolidado[df_consolidado['empresa'] == empresa])
        cor = CORES_EMPRESAS.get(empresa, '#808080')
        stats_html += f"""
        <tr>
            <td style="padding: 2px 5px;">
                <span style="color: {cor}; font-size: 20px;">●</span>
            </td>
            <td style="padding: 2px 5px;">{empresa}</td>
            <td style="padding: 2px 5px; text-align: right;">{count}</td>
        </tr>
        """
    
    # Legenda consolidada
    legenda_html = f"""
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        width: 220px; 
        height: auto;
        background-color: white;
        border: 2px solid grey;
        border-radius: 5px;
        padding: 10px;
        font-size: 14px;
        z-index: 9999;
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
    ">
        <h4 style="margin-top: 0;">MACEIÓ - TODAS EMPRESAS</h4>
        <hr>
        <b>Total de Pontos:</b> {len(df_consolidado)}<br>
        <b>Pontos por Empresa:</b>
        <table style="width: 100%; margin-top: 5px;">
            {stats_html}
        </table>
        <hr>
        <small><i>Use o controle no canto superior direito para ligar/desligar empresas</i></small>
    </div>
    """
    
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    
    # Salva o mapa
    mapa.save(output_file_html)
    print(f"🗺️ Mapa consolidado salvo: {output_file_html}")
    print(f"{'='*60}")
    
    return mapa, df_consolidado

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """
    Função principal que orquestra todo o processo.
    """
    print("🚀 INICIANDO SISTEMA DE MAPEAMENTO COM VALIDAÇÃO 'ATIVO'")
    print("=" * 60)
    
    todos_dfs = []
    
    # Processa cada PDF
    for config in PDFS_PARA_PROCESSAR:
        pdf_path = config['caminho']
        empresa = config['empresa']
        
        # Verifica se o arquivo existe
        if not Path(pdf_path).exists():
            print(f"❌ Arquivo não encontrado: {pdf_path}")
            continue
        
        # Extrai dados do PDF (com validação de seções ativas)
        df = extrair_coordenadas_pdf_com_ativo(pdf_path, empresa)
        
        if not df.empty:
            # Salva CSV individual
            csv_file = f"dados_{empresa}_ATIVOS.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"💾 Dados salvos: {csv_file}")
            
            # Cria mapa individual
            html_file = f"mapa_{empresa}_ATIVOS_FOLIUM.html"
            criar_mapa_folium(df, empresa, html_file)
            
            # Adiciona à lista para consolidação
            todos_dfs.append(df)
        else:
            print(f"⚠️ Nenhum ponto ativo encontrado para {empresa}")
    
    # Cria mapa consolidado se houver dados
    if todos_dfs:
        criar_mapa_consolidado(
            todos_dfs,
            "mapa_TODAS_EMPRESAS_ATIVAS_FOLIUM.html",
            "mapa_TODAS_EMPRESAS_ATIVAS_FOLIUM.csv"
        )
    
    print("\n" + "=" * 60)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print("=" * 60)
    
    # Resumo final
    print("\n📋 RESUMO DOS ARQUIVOS GERADOS:")
    print("-" * 40)
    
    arquivos_gerados = []
    
    for config in PDFS_PARA_PROCESSAR:
        empresa = config['empresa']
        csv_file = f"dados_{empresa}_ATIVOS.csv"
        html_file = f"mapa_{empresa}_ATIVOS_FOLIUM.html"
        
        if Path(csv_file).exists():
            arquivos_gerados.append(csv_file)
        if Path(html_file).exists():
            arquivos_gerados.append(html_file)
    
    arquivos_gerados.extend([
        "mapa_TODAS_EMPRESAS_ATIVAS_FOLIUM.html",
        "mapa_TODAS_EMPRESAS_ATIVAS_FOLIUM.csv"
    ])
    
    for arquivo in arquivos_gerados:
        if Path(arquivo).exists():
            tamanho = Path(arquivo).stat().st_size / 1024  # Tamanho em KB
            print(f"📄 {arquivo} ({tamanho:.1f} KB)")
    
    print("\n🎯 Para visualizar os mapas:")
    print("   1. Abra qualquer arquivo .html no navegador")
    print("   2. Clique nos pontos para ver detalhes")
    print("   3. Use zoom e arraste para navegar")

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    # Instalação das dependências necessárias
    print("🔧 Verificando dependências...")
    
    try:
        import pdfplumber
        import pandas as pd
        import folium
        print("✅ Todas as dependências estão instaladas")
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("\n📦 Instale as dependências com:")
        print("   pip install folium pandas pdfplumber")
        exit(1)
    
    # Executa o sistema
    main()