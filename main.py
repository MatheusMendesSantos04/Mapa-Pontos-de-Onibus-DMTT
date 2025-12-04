"""
SISTEMA DE MAPEAMENTO DE PONTOS DE ÔNIBUS - MACEIÓ/AL
Usando FOLIUM para mapas interativos profissionais
Versão: 2.0 - Com mapa base real do OpenStreetMap
"""

import pandas as pd
import pdfplumber
import re
import folium
from folium import plugins
from pathlib import Path

# ============ CONFIGURAÇÕES ============
CORES_EMPRESAS = {
    'Real': '#FF0000',           # Vermelho
    'SaoFrancisco': '#0000FF',   # Azul
    'CidadeMaceio': '#FFFF00'    # Amarelo
}

# Coordenadas do centro de Maceió
MACEIO_CENTRO = [-9.6498, -35.7089]

# ============ EXTRAÇÃO DE DADOS DOS PDFs ============
def extrair_coordenadas_pdf(pdf_path, empresa_nome):
    """
    Extrai coordenadas geográficas dos PDFs
    """
    print(f"\n📊 PROCESSANDO: {Path(pdf_path).name}")
    
    dados = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina_num, pagina in enumerate(pdf.pages):
                texto = pagina.extract_text()
                if not texto:
                    continue
                
                linhas = texto.split('\n')
                
                for linha_num, linha in enumerate(linhas):
                    linha = linha.strip()
                    
                    # Padrões de coordenadas
                    padroes = [
                        r'(-?\d{1,2}[,.]\d+)\s+(-?\d{1,2}[,.]\d+)',  # -9,12345 -35,67890
                        r'(-?\d{1,2}\.\d+)\s+(-?\d{1,2}\.\d+)'        # -9.12345 -35.67890
                    ]
                    
                    for padrao in padroes:
                        matches = re.findall(padrao, linha)
                        
                        for lat_str, lon_str in matches:
                            try:
                                lat = float(lat_str.replace(',', '.'))
                                lon = float(lon_str.replace(',', '.'))
                                
                                # Validar coordenadas de Maceió
                                if -9.8 < lat < -9.4 and -35.9 < lon < -35.6:
                                    
                                    # Procurar código do ponto
                                    codigo = "DESCONHECIDO"
                                    codigos_encontrados = re.findall(r'([A-Z]{2,}\d+)', linha)
                                    
                                    if codigos_encontrados:
                                        codigo = codigos_encontrados[0]
                                    elif linha_num > 0:
                                        linha_anterior = linhas[linha_num - 1]
                                        codigos_ant = re.findall(r'([A-Z]{2,}\d+)', linha_anterior)
                                        if codigos_ant:
                                            codigo = codigos_ant[0]
                                    
                                    dados.append({
                                        'empresa': empresa_nome,
                                        'codigo': codigo,
                                        'endereco': linha[:100],
                                        'latitude': lat,
                                        'longitude': lon,
                                        'pagina': pagina_num + 1
                                    })
                                    
                                    print(f"  ✅ {codigo} → ({lat:.5f}, {lon:.5f})")
                                    
                            except Exception:
                                continue
    
    except Exception as e:
        print(f"  ❌ Erro ao processar PDF: {e}")
    
    if dados:
        df = pd.DataFrame(dados)
        df = df.drop_duplicates(subset=['latitude', 'longitude'])
        
        # Salvar CSV
        csv_file = f"dados_{empresa_nome}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n  📈 RESULTADO: {len(df)} pontos extraídos")
        print(f"  💾 Salvo em: {csv_file}")
        
        return df
    else:
        print(f"  ⚠️  Nenhum ponto encontrado!")
        return pd.DataFrame()

# ============ CRIAR MAPA FOLIUM INDIVIDUAL ============
def criar_mapa_folium(df, empresa_nome, output_file):
    """
    Cria mapa interativo com Folium (igual à imagem de referência)
    """
    if df.empty:
        print(f"  ⚠️  Sem dados para {empresa_nome}")
        return
    
    print(f"\n🗺️  CRIANDO MAPA: {output_file}")
    
    # Calcular centro do mapa
    lat_centro = df['latitude'].mean()
    lon_centro = df['longitude'].mean()
    
    # Criar mapa base
    mapa = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=12,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Adicionar tiles alternativos
    folium.TileLayer('CartoDB positron', name='CartoDB Claro').add_to(mapa)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Escuro').add_to(mapa)
    
    # Cor da empresa
    cor = CORES_EMPRESAS.get(empresa_nome, '#000000')
    
    # Adicionar marcadores
    for idx, ponto in df.iterrows():
        # Popup com informações
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="color: {cor}; margin: 0;">{empresa_nome}</h4>
            <hr style="margin: 5px 0;">
            <b>Código:</b> {ponto['codigo']}<br>
            <b>Lat:</b> {ponto['latitude']:.5f}<br>
            <b>Lon:</b> {ponto['longitude']:.5f}<br>
            <small>{ponto['endereco'][:80]}</small>
        </div>
        """
        
        folium.CircleMarker(
            location=[ponto['latitude'], ponto['longitude']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{ponto['codigo']}",
            color='white',
            fillColor=cor,
            fillOpacity=0.8,
            weight=2
        ).add_to(mapa)
    
    # Adicionar legenda
    legenda_html = f"""
    <div style="position: fixed; 
                top: 10px; right: 10px; 
                background-color: white; 
                border: 2px solid grey; 
                border-radius: 5px;
                padding: 10px;
                font-family: Arial;
                z-index: 9999;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: {cor};">{empresa_nome}</h4>
        <p style="margin: 5px 0;"><b>Total de pontos:</b> {len(df)}</p>
        <p style="margin: 5px 0;"><b>Região:</b> Maceió/AL</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    
    # Adicionar controle de camadas
    folium.LayerControl().add_to(mapa)
    
    # Adicionar plugin de tela cheia
    plugins.Fullscreen().add_to(mapa)
    
    # Salvar
    mapa.save(output_file)
    print(f"  ✅ Mapa salvo: {output_file}")
    print(f"  📍 {len(df)} pontos no mapa")
    
    return mapa

# ============ CRIAR MAPA CONSOLIDADO ============
def criar_mapa_consolidado(lista_dfs, output_file):
    """
    Cria mapa com todas as empresas juntas
    """
    print(f"\n🌍 CRIANDO MAPA CONSOLIDADO: {output_file}")
    
    # Juntar todos os dados
    df_total = pd.concat(lista_dfs, ignore_index=True)
    
    if df_total.empty:
        print("  ⚠️  Nenhum dado para consolidar!")
        return
    
    # Calcular centro
    lat_centro = df_total['latitude'].mean()
    lon_centro = df_total['longitude'].mean()
    
    # Criar mapa
    mapa = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=12,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Adicionar tiles
    folium.TileLayer('CartoDB positron').add_to(mapa)
    folium.TileLayer('CartoDB dark_matter').add_to(mapa)
    
    # Criar grupos de camadas por empresa
    grupos = {}
    for empresa in df_total['empresa'].unique():
        grupos[empresa] = plugins.FeatureGroupSubGroup(
            folium.FeatureGroup(name=empresa).add_to(mapa),
            name=empresa
        )
        grupos[empresa].add_to(mapa)
    
    # Adicionar pontos por empresa
    for empresa in df_total['empresa'].unique():
        df_empresa = df_total[df_total['empresa'] == empresa]
        cor = CORES_EMPRESAS.get(empresa, '#000000')
        
        for _, ponto in df_empresa.iterrows():
            popup_html = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4 style="color: {cor}; margin: 0;">{empresa}</h4>
                <hr style="margin: 5px 0;">
                <b>Código:</b> {ponto['codigo']}<br>
                <b>Coordenadas:</b><br>
                {ponto['latitude']:.5f}, {ponto['longitude']:.5f}
            </div>
            """
            
            folium.CircleMarker(
                location=[ponto['latitude'], ponto['longitude']],
                radius=7,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{empresa}: {ponto['codigo']}",
                color='white',
                fillColor=cor,
                fillOpacity=0.7,
                weight=2
            ).add_to(grupos[empresa])
    
    # Legenda consolidada
    legenda_items = ""
    for empresa, cor in CORES_EMPRESAS.items():
        count = len(df_total[df_total['empresa'] == empresa])
        if count > 0:
            legenda_items += f"""
            <div style="margin: 5px 0;">
                <span style="background-color: {cor}; 
                             width: 15px; height: 15px; 
                             display: inline-block; 
                             border-radius: 50%;
                             border: 2px solid white;"></span>
                <b>{empresa}:</b> {count} pontos
            </div>
            """
    
    legenda_html = f"""
    <div style="position: fixed; 
                top: 10px; right: 10px; 
                background-color: white; 
                border: 2px solid grey; 
                border-radius: 5px;
                padding: 15px;
                font-family: Arial;
                z-index: 9999;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0;">TODAS AS EMPRESAS</h4>
        {legenda_items}
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0;"><b>Total Geral:</b> {len(df_total)} pontos</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    
    # Controles
    folium.LayerControl(collapsed=False).add_to(mapa)
    plugins.Fullscreen().add_to(mapa)
    
    # Salvar
    mapa.save(output_file)
    print(f"  ✅ Mapa consolidado salvo!")
    print(f"  📊 Total: {len(df_total)} pontos de {len(df_total['empresa'].unique())} empresas")
    
    # Salvar CSV consolidado
    csv_file = output_file.replace('.html', '.csv')
    df_total.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"  💾 CSV consolidado: {csv_file}")

# ============ FUNÇÃO PRINCIPAL ============
def main():
    """
    Execução principal do sistema
    """
    print("="*80)
    print("🗺️  SISTEMA DE MAPEAMENTO COM FOLIUM - PONTOS DE ÔNIBUS MACEIÓ/AL")
    print("="*80)
    
    # Configuração das empresas
    empresas = [
        ('Real', 'pontos_real.pdf'),
        ('SaoFrancisco', 'empresa_saoFran.pdf'),
        ('CidadeMaceio', 'pontos_Maceio.pdf')
    ]
    
    todos_dados = []
    
    # Processar cada empresa
    for empresa_nome, arquivo_pdf in empresas:
        print(f"\n{'='*60}")
        print(f"📌 EMPRESA: {empresa_nome}")
        print(f"{'='*60}")
        
        if Path(arquivo_pdf).exists():
            # Extrair dados do PDF
            df = extrair_coordenadas_pdf(arquivo_pdf, empresa_nome)
            
            if not df.empty:
                todos_dados.append(df)
                
                # Criar mapa individual em HTML
                html_file = f'mapa_{empresa_nome}_FOLIUM.html'
                criar_mapa_folium(df, empresa_nome, html_file)
                
                print(f"\n  ✅ Mapa HTML interativo criado!")
                print(f"  🌐 Abra no navegador: {html_file}")
            else:
                print(f"  ⚠️  Pulando {empresa_nome} - sem dados válidos")
        else:
            print(f"  ❌ Arquivo não encontrado: {arquivo_pdf}")
    
    # Criar mapa consolidado
    if todos_dados:
        print(f"\n{'='*80}")
        print("🌍 GERANDO MAPA CONSOLIDADO COM TODAS AS EMPRESAS")
        print(f"{'='*80}")
        
        criar_mapa_consolidado(todos_dados, 'mapa_TODAS_EMPRESAS_FOLIUM.html')
    
    # Resumo final
    print(f"\n{'='*80}")
    print("🎉 PROCESSAMENTO CONCLUÍDO!")
    print(f"{'='*80}")
    
    print("\n📂 ARQUIVOS GERADOS:")
    for empresa_nome, _ in empresas:
        html_file = f'mapa_{empresa_nome}_FOLIUM.html'
        if Path(html_file).exists():
            print(f"  ✅ {html_file}")
    
    if Path('mapa_TODAS_EMPRESAS_FOLIUM.html').exists():
        print(f"  ✅ mapa_TODAS_EMPRESAS_FOLIUM.html")
    
    print("\n💡 COMO USAR:")
    print("  1. Abra os arquivos .html no seu navegador")
    print("  2. Clique nos pontos para ver detalhes")
    print("  3. Use os controles no canto para trocar camadas")
    print("  4. Botão de tela cheia disponível")
    print("  5. Mapas são totalmente interativos!")

# ============ EXECUTAR ============
if __name__ == "__main__":
    main()