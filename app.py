from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'monitor_web_secret_key'  # Necessário para flash messages

# Armazenamento em memória para as URLs monitoradas
monitored_urls = {}

def get_page_content(url):
    """Obtém o conteúdo de texto de uma página web."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Levanta exceção para status codes de erro
        
        # Usar BeautifulSoup para extrair apenas o texto visível
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remover scripts, estilos e outros elementos não visíveis
        for script in soup(["script", "style", "meta", "link"]):
            script.extract()
            
        # Obter o texto visível
        text = soup.get_text()
        
        # Normalizar espaços em branco
        text = ' '.join(text.split())
        
        return text
    except Exception as e:
        return f"Erro ao acessar a página: {str(e)}"

def calculate_hash(content):
    """Calcula o hash SHA-256 do conteúdo."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def is_valid_url(url):
    """Verifica se a URL é válida."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@app.route('/', methods=['GET'])
def index():
    """Página inicial com formulário e lista de URLs monitoradas."""
    return render_template('index.html', urls=monitored_urls)

@app.route('/add', methods=['POST'])
def add_url():
    """Adiciona uma nova URL para monitoramento."""
    url = request.form.get('url', '').strip()
    
    if not url:
        flash('Por favor, informe uma URL.', 'danger')
        return redirect(url_for('index'))
    
    if not is_valid_url(url):
        flash('URL inválida. Por favor, informe uma URL completa (ex: https://exemplo.com).', 'danger')
        return redirect(url_for('index'))
    
    if url in monitored_urls:
        flash(f'A URL {url} já está sendo monitorada.', 'warning')
        return redirect(url_for('index'))
    
    try:
        # Obter o conteúdo inicial da página
        content = get_page_content(url)
        content_hash = calculate_hash(content)
        
        # Armazenar informações da URL
        monitored_urls[url] = {
            'initial_content': content,
            'initial_hash': content_hash,
            'current_hash': content_hash,
            'last_check': datetime.now(),
            'changed': False,
            'error': None
        }
        
        flash(f'URL {url} adicionada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar URL: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/check/<path:url>')
def check_url(url):
    """Verifica se houve alterações em uma URL específica."""
    if url not in monitored_urls:
        flash(f'URL {url} não encontrada.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Obter o conteúdo atual da página
        content = get_page_content(url)
        current_hash = calculate_hash(content)
        
        # Atualizar informações da URL
        monitored_urls[url]['current_hash'] = current_hash
        monitored_urls[url]['last_check'] = datetime.now()
        monitored_urls[url]['changed'] = (current_hash != monitored_urls[url]['initial_hash'])
        monitored_urls[url]['error'] = None
        
        status = 'alterada' if monitored_urls[url]['changed'] else 'sem alterações'
        flash(f'URL {url} verificada com sucesso! Status: {status}', 'success')
    except Exception as e:
        monitored_urls[url]['error'] = str(e)
        flash(f'Erro ao verificar URL: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/remove/<path:url>')
def remove_url(url):
    """Remove uma URL do monitoramento."""
    if url in monitored_urls:
        del monitored_urls[url]
        flash(f'URL {url} removida do monitoramento.', 'success')
    else:
        flash(f'URL {url} não encontrada.', 'danger')
    
    return redirect(url_for('index'))

@app.template_filter('format_datetime')
def format_datetime(value):
    """Formata um objeto datetime para exibição."""
    if value:
        return value.strftime('%d/%m/%Y %H:%M:%S')
    return ''

if __name__ == '__main__':
    app.run(debug=True)