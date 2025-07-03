from flask import Flask, render_template, request, redirect, url_for, Response, session, flash
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
app.secret_key = 'chave-secreta-para-o-portal-proxy-final'

# --- CONFIGURAÇÃO CENTRAL DOS SISTEMAS ---
SISTEMAS = {
    'guaruja_t2_cliente': {
        'id': 'guaruja_t2_cliente',
        'nome_exibicao': 'Guarujá T2 - Cliente',
        'host': 'https://clientes.novvsgj2.movecta.com.br'
    },
    'guaruja_t2_frota': {
        'id': 'guaruja_t2_frota',
        'nome_exibicao': 'Guarujá T2 - Frota',
        'host': 'https://frotas.novvsgj2.movecta.com.br'
    },
    # --- Guarujá T1 ---
    'guaruja_t1_portal_atual': {
        'id': 'guaruja_t1_portal_atual',
        'nome_exibicao': 'Guarujá T1 - Portal Atual',
        'host': 'https://portal.movecta.com.br',
        'login_path': '/owa/lf_acesso.login' # URL de login específica
    },
    'guaruja_t1_clientes': {
        'id': 'guaruja_t1_clientes',
        'nome_exibicao': 'Guarujá T1 - Clientes (Novo )',
        'host': 'https://clientes.novvsg1.movecta.com.br',
        'login_path': '/login' # Assumindo /login, se não for, ajuste
    },
    'guaruja_t1_frotas': {
        'id': 'guaruja_t1_frotas',
        'nome_exibicao': 'Guarujá T1 - Frotas (Novo )',
        'host': 'https://frotas.novvsg1.movecta.com.br',
        'login_path': '/login' # Assumindo /login, se não for, ajuste
    },

    # --- Guarujá T2 ---
    'guaruja_t2_portal_atual': {
        'id': 'guaruja_t2_portal_atual',
        'nome_exibicao': 'Guarujá T2 - Portal Atual',
        'host': 'https://portal.movecta.com.br',
        'login_path': '/owat2/lf_acesso.login2' # URL de login específica
    },
    'guaruja_t2_clientes': {
        'id': 'guaruja_t2_clientes',
        'nome_exibicao': 'Guarujá T2 - Clientes (Novo )',
        'host': 'https://clientes.novvsgj2.movecta.com.br',
        'login_path': '/login'
    },
    'guaruja_t2_frotas': {
        'id': 'guaruja_t2_frotas',
        'nome_exibicao': 'Guarujá T2 - Frotas (Novo )',
        'host': 'https://frotas.novvsgj2.movecta.com.br',
        'login_path': '/login'
    },

    # --- Itajaí ---
    'itajai_wmasnet': {
        'id': 'itajai_wmasnet',
        'nome_exibicao': 'Itajaí - WMASNET',
        'host': 'http://wmasnet.localfrio.com.br',
        'login_path': '/wmasnet/'
    },
    'itajai_clientes': {
        'id': 'itajai_clientes',
        'nome_exibicao': 'Itajaí - Clientes',
        'host': 'https://clientes.novvsitj.movecta.com.br',
        'login_path': '/login'
    },
    'itajai_frotas': {
        'id': 'itajai_frotas',
        'nome_exibicao': 'Itajaí - Frotas',
        'host': 'https://frotas.novvsitj.movecta.com.br',
        'login_path': '/login'
    },

    # --- Suata ---
    'suata_portal': {
        'id': 'suata_portal',
        'nome_exibicao': 'Suata - Portal',
        'host': 'https://portalsuata.movecta.com.br',
        'login_path': '/portal/modules.php'
    },
    'suata_clientes': {
        'id': 'suata_clientes',
        'nome_exibicao': 'Suata - Clientes',
        'host': 'https://clientes.novvssua.movecta.com.br',
        'login_path': '/login'
    },
    'suata_frotas': {
        'id': 'suata_frotas',
        'nome_exibicao': 'Suata - Frotas',
        'host': 'https://frotas.novvssua.movecta.com.br',
        'login_path': '/login'
    },

    # --- Atlântico ---
    'atlantico_portal': {
        'id': 'atlantico_portal',
        'nome_exibicao': 'Atlântico - Portal',
        'host': 'https://portalsuata.movecta.com.br',
        'login_path': '/atl/modules.php'
    },
    'atlantico_clientes': {
        'id': 'atlantico_clientes',
        'nome_exibicao': 'Atlântico - Clientes',
        'host': 'https://clientes.novvsatl.movecta.com.br',
        'login_path': '/login'
    },
    'atlantico_frotas': {
        'id': 'atlantico_frotas',
        'nome_exibicao': 'Atlântico - Frotas',
        'host': 'https://frotas.novvsatl.movecta.com.br',
        'login_path': '/login'
    },
}

@app.route('/' )
def index():
    """Exibe a página de login inicial."""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    """
    Recebe as credenciais, tenta logar em todos os sistemas via requests
    e redireciona para o portal com os resultados.
    """
    username = request.form['username']
    password = request.form['password']
    
    sistemas_logados = []
    sessoes_proxy = {}

    print("Iniciando login em massa via proxy...")
    for system_id, config in SISTEMAS.items():
        print(f"--- Tentando login em: {config['nome_exibicao']} ---")
        
        login_path = config.get('login_path', '/login')
        login_url = urljoin(config['host'], login_path)
        
        payload = {'username': username, 'password': password}
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0'})

        try:
            resp = s.post(login_url, data=payload, allow_redirects=True, timeout=15)
            
            if resp.status_code == 200 and login_path not in resp.url:
                print(f"✅ Sucesso para {system_id}")
                sistemas_logados.append(config)
                sessoes_proxy[system_id] = s.cookies.get_dict()
            else:
                print(f"❌ Falha para {system_id} (Status: {resp.status_code}, URL final: {resp.url})")
        except requests.exceptions.RequestException as e:
            print(f"❌ Falha de conexão ou timeout para {system_id}: {e}")
            continue

    if not sistemas_logados:
        flash("Falha no login para todos os sistemas. Verifique as credenciais e a conexão.")
        return redirect(url_for('index'))
    
    session['sessoes_proxy'] = sessoes_proxy
    
    return render_template('portal.html', sistemas_logados=sistemas_logados)

@app.route('/proxy/<system_id>/', defaults={'path': ''})
@app.route('/proxy/<system_id>/<path:path>', methods=['GET', 'POST'])
def proxy_request(system_id, path):
    """
    A rota de proxy que serve o conteúdo para o Iframe.
    """
    if 'sessoes_proxy' not in session or system_id not in session['sessoes_proxy']:
        return "Sessão expirada ou inválida. Por favor, faça o login novamente.", 401

    if system_id not in SISTEMAS:
        return "Sistema desconhecido.", 404

    target_host = SISTEMAS[system_id]['host']
    target_url = urljoin(target_host, path)
    cookies = session['sessoes_proxy'][system_id]
    
    try:
        if request.method == 'GET':
            resp = requests.get(target_url, cookies=cookies, params=request.args, stream=True, timeout=30)
        elif request.method == 'POST':
            resp = requests.post(target_url, cookies=cookies, data=request.form, stream=True, timeout=30)
        
        content_type = resp.headers.get('Content-Type', '').lower()
        
        if 'text/html' in content_type:
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove qualquer tag <base> existente para evitar conflitos
            if soup.head:
                for base_tag_existing in soup.head.find_all('base'):
                    base_tag_existing.decompose()

            # A URL base deve ser o caminho do proxy para o sistema atual,
            # garantindo que todas as URLs relativas sejam resolvidas corretamente.
            base_href = url_for('proxy_request', system_id=system_id, path='', _external=False)
            new_base_tag = soup.new_tag("base", href=base_href)
            
            if soup.head:
                soup.head.insert(0, new_base_tag)
            elif soup.html:
                soup.html.insert(0, new_base_tag)
            else:
                soup.body.insert(0, new_base_tag)
            
            # --- NOVO: Script de Interceptação de XHR/Fetch ---
            # Este script será injetado no HTML para reescrever URLs no lado do cliente.
            interceptor_script = f"""
            <script>
                (function() {{
                    const PROXY_BASE_URL = "{base_href}"; // Ex: /proxy/system_id/
                    const TARGET_HOST = "{target_host}"; // Ex: https://frotas.novvsitj.movecta.com.br

                    // Função para reescrever a URL
                    function rewriteUrl(originalUrl ) {{
                        // Se a URL já começa com o PROXY_BASE_URL, não faz nada
                        if (originalUrl.startsWith(PROXY_BASE_URL)) {{
                            return originalUrl;
                        }}

                        // Se a URL é absoluta e começa com o TARGET_HOST, remove o host e prefixa com PROXY_BASE_URL
                        if (originalUrl.startsWith(TARGET_HOST)) {{
                            const relativePath = originalUrl.substring(TARGET_HOST.length);
                            return PROXY_BASE_URL + relativePath.lstrip('/');
                        }}

                        // Se a URL começa com '/' (absoluta para o domínio atual), prefixa com PROXY_BASE_URL
                        if (originalUrl.startsWith('/')) {{
                            return PROXY_BASE_URL + originalUrl.substring(1);
                        }}
                        
                        // Para URLs relativas (sem / no início), a tag <base> já deve cuidar.
                        // Mas podemos adicionar uma camada de segurança se necessário.
                        // if (!originalUrl.includes('://')) {{
                        //     return PROXY_BASE_URL + originalUrl;
                        // }}

                        return originalUrl; // Retorna a URL original se nenhuma regra se aplicar
                    }}

                    // Intercepta XMLHttpRequest
                    const originalXhrOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
                        const rewrittenUrl = rewriteUrl(url);
                        // console.log('XHR Rewritten:', url, '->', rewrittenUrl);
                        originalXhrOpen.call(this, method, rewrittenUrl, async, user, password);
                    }};

                    // Intercepta window.fetch
                    const originalFetch = window.fetch;
                    window.fetch = function(input, init) {{
                        if (typeof input === 'string') {{
                            const rewrittenInput = rewriteUrl(input);
                            // console.log('Fetch Rewritten:', input, '->', rewrittenInput);
                            return originalFetch.call(this, rewrittenInput, init);
                        }}
                        // Se input não for string (ex: Request object), passa adiante
                        return originalFetch.call(this, input, init);
                    }};
                }})();
            </script>
            """
            # Adiciona o script de interceptação no head do documento
            if soup.head:
                soup.head.append(BeautifulSoup(interceptor_script, 'html.parser'))
            else: # Fallback se não houver head
                if soup.html:
                    soup.html.insert(0, BeautifulSoup(interceptor_script, 'html.parser'))
                else:
                    soup.body.insert(0, BeautifulSoup(interceptor_script, 'html.parser'))

            # A reescrita de URLs em tags HTML (a, link, img, form) continua sendo importante
            # para garantir que todas as referências no HTML sejam corretas.
            for tag, attr in [('a', 'href'), ('link', 'href'), ('script', 'src'), ('img', 'src'), ('form', 'action')]:
                for item in soup.find_all(tag):
                    if item.has_attr(attr):
                        original_url = item[attr]
                        # Verifica se a URL é absoluta e pertence ao host de destino
                        if original_url.startswith(target_host):
                            relative_path = original_url.replace(target_host, '').lstrip('/')
                            item[attr] = url_for('proxy_request', system_id=system_id, path=relative_path)
                        elif not original_url.startswith(('http://', 'https://', '//' )):
                            item[attr] = url_for('proxy_request', system_id=system_id, path=original_url.lstrip('/'))
            
            # Remove a reescrita de strings em scripts inline e atributos on*
            # A interceptação de XHR/Fetch deve lidar com isso de forma mais robusta.
            # for script_tag in soup.find_all('script'):
            #     if script_tag.string:
            #         original_script = script_tag.string
            #         modified_script = original_script
            #         # ... (remover as substituições de regex aqui) ...
            #         script_tag.string = modified_script
            
            # for tag in soup.find_all(True):
            #     for attr in tag.attrs:
            #         if attr.startswith('on') and isinstance(tag[attr], str):
            #             original_attr_value = tag[attr]
            #             modified_attr_value = original_attr_value
            #             # ... (remover as substituições de regex aqui) ...
            #             tag[attr] = modified_attr_value

            content = soup.prettify(encoding='utf-8')
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        
        return Response(content, resp.status_code, headers)

    except requests.exceptions.RequestException as e:
        return f"Erro ao acessar o recurso via proxy: {e}", 502

@app.route('/logout')
def logout():
    """Limpa a sessão do usuário e redireciona para a página de login."""
    session.clear()
    print("Sessão limpa. Usuário deslogado.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
