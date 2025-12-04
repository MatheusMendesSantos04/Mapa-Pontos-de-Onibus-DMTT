import pdfplumber
import re

def analisar_pdf(pdf_path):
    print(f"\n🔍 ANALISANDO: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Analisar apenas as 3 primeiras páginas
        for pagina_num in range(min(3, len(pdf.pages))):
            pagina = pdf.pages[pagina_num]
            texto = pagina.extract_text()
            
            print(f"\n📄 Página {pagina_num + 1}:")
            print("-" * 50)
            
            # Mostrar apenas 20 primeiras linhas
            linhas = texto.split('\n')
            for i, linha in enumerate(linhas[:20]):
                print(f"{i+1:3}: {linha}")
            
            print("-" * 50)
            
            # Procurar padrões específicos
            padroes = [
                r'(-?\d{1,2}[,.]\d+)\s+(-?\d{1,2}[,.]\d+)',  # Coordenadas
                r'[A-Z]{2}\d+',  # Códigos como PN987
                r'Endereço.*Latitude',  # Cabeçalho da tabela
            ]
            
            for padrao in padroes:
                encontrados = re.findall(padrao, texto)
                if encontrados:
                    print(f"Padrão '{padrao}': {len(encontrados)} encontrados")
                    print(f"Exemplo: {encontrados[:3]}")

# Testar com UM PDF primeiro

analisar_pdf("empresa_saoFran.pdf")
