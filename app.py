from flask import Flask, render_template, request, redirect, url_for, Response, session, flash
import requests
import requests.utils  # Importa a biblioteca de utilidades do requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
# É uma boa prática trocar a chave secreta ao fazer grandes mudanças
app.secret_key = 'chave-secreta-definitiva-para-o-portal'

# --- CONFIGURAÇÃO CENTRAL DOS SISTEMAS (sem alterações) ---
SISTEMAS = {

    'guaruja_t1_portal_atual': {'id': 'guaruja_t1_portal_atual', 'nome_exibicao': 'Guarujá T1 - Portal Atual', 'host': 'https://portal.movecta.com.br', 'login_path': '/owa/lf_acesso.login'},
    'guaruja_t1_clientes': {'id': 'guaruja_t1_clientes', 'nome_exibicao': 'Guarujá T1 - Clientes (Novo )', 'host': 'https://clientes.novvsg1.movecta.com.br', 'login_path': '/login'},
    'guaruja_t1_frotas': {'id': 'guaruja_t1_frotas', 'nome_exibicao': 'Guarujá T1 - Frotas (Novo )', 'host': 'https://frotas.novvsg1.movecta.com.br', 'login_path': '/login'},
    'guaruja_t2_portal_atual': {'id': 'guaruja_t2_portal_atual', 'nome_exibicao': 'Guarujá T2 - Portal Atual', 'host': 'https://portal.movecta.com.br', 'login_path': '/owat2/lf_acesso.login2'},
    'guaruja_t2_clientes': {'id': 'guaruja_t2_clientes', 'nome_exibicao': 'Guarujá T2 - Clientes (Novo )', 'host': 'https://clientes.novvsgj2.movecta.com.br', 'login_path': '/login'},
    'guaruja_t2_frotas': {'id': 'guaruja_t2_frotas', 'nome_exibicao': 'Guarujá T2 - Frotas (Novo )', 'host': 'https://frotas.novvsgj2.movecta.com.br', 'login_path': '/login'},
    'itajai_wmasnet': {'id': 'itajai_wmasnet', 'nome_exibicao': 'Itajaí - WMASNET', 'host': 'http://wmasnet.localfrio.com.br', 'login_path': '/wmasnet/'},
    'itajai_clientes': {'id': 'itajai_clientes', 'nome_exibicao': 'Itajaí - Clientes', 'host': 'https://clientes.novvsitj.movecta.com.br', 'login_path': '/login'},
    'itajai_frotas': {'id': 'itajai_frotas', 'nome_exibicao': 'Itajaí - Frotas', 'host': 'https://frotas.novvsitj.movecta.com.br', 'login_path': '/login'},
    'suata_portal': {'id': 'suata_portal', 'nome_exibicao': 'Suata - Portal', 'host': 'https://portalsuata.movecta.com.br', 'login_path': '/portal/modules.php'},
    'suata_clientes': {'id': 'suata_clientes', 'nome_exibicao': 'Suata - Clientes', 'host': 'https://clientes.novvssua.movecta.com.br', 'login_path': '/login'},
    'suata_frotas': {'id': 'suata_frotas', 'nome_exibicao': 'Suata - Frotas', 'host': 'https://frotas.novvssua.movecta.com.br', 'login_path': '/login'},
    'atlantico_portal': {'id': 'atlantico_portal', 'nome_exibicao': 'Atlântico - Portal', 'host': 'https://portalsuata.movecta.com.br', 'login_path': '/atl/modules.php'},
    'atlantico_clientes': {'id': 'atlantico_clientes', 'nome_exibicao': 'Atlântico - Clientes', 'host': 'https://clientes.novvsatl.movecta.com.br', 'login_path': '/login'},
    'atlantico_frotas': {'id': 'atlantico_frotas', 'nome_exibicao': 'Atlântico - Frotas', 'host': 'https://frotas.novvsatl.movecta.com.br', 'login_path': '/login'},
}

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form['username']
    password = request.form['password']
    sistemas_logados = []
    sessoes_proxy = {}

    for system_id, config in SISTEMAS.items():
        login_path = config.get('login_path', '/login')
        login_url = urljoin(config['host'], login_path)
        payload = {'username': username, 'password': password}
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0'})
        try:
            resp = s.post(login_url, data=payload, allow_redirects=True, timeout=15)
            if resp.ok and login_path not in resp.url:
                sistemas_logados.append(config)
                # Converte o cookiejar para um dicionário simples e seguro
                sessoes_proxy[system_id] = requests.utils.dict_from_cookiejar(s.cookies)
        except requests.exceptions.RequestException:
            continue

    if not sistemas_logados:
        flash("Falha no login. Verifique as credenciais e a conexão.")
        return redirect(url_for('index'))
    
    session['sessoes_proxy'] = sessoes_proxy
    session['sistemas_logados'] = sistemas_logados
    return redirect(url_for('portal'))

@app.route('/portal')
def portal():
    if 'sistemas_logados' not in session:
        return redirect(url_for('index'))
    return render_template('portal.html', sistemas_logados=session['sistemas_logados'])

@app.route('/proxy/<system_id>/', defaults={'path': ''})
@app.route('/proxy/<system_id>/<path:path>', methods=['GET', 'POST'])
def proxy_request(system_id, path):
    """
    ROTA DE PROXY FINAL v12
    Remove a reescrita de JS no servidor e adiciona um interceptador para jQuery.ajax no cliente.
    """
    if 'sessoes_proxy' not in session or system_id not in session['sessoes_proxy']:
        return "Sessão expirada ou inválida.", 401

    target_host = SISTEMAS[system_id]['host']
    cookie_dict = session['sessoes_proxy'].get(system_id, {})
    cookies = requests.utils.cookiejar_from_dict(cookie_dict)
    
    query_params = request.query_string.decode('utf-8')
    full_target_url = urljoin(target_host, path)
    if query_params:
        full_target_url += f"?{query_params}"

    try:
        req_headers = {key: value for key, value in request.headers if key.lower() not in ['host', 'cookie', 'connection']}
        req_headers['Referer'] = target_host

        if request.method == 'GET':
            resp = requests.get(full_target_url, headers=req_headers, cookies=cookies, stream=True, timeout=30, allow_redirects=False)
        else: # POST
            resp = requests.post(full_target_url, headers=req_headers, cookies=cookies, data=request.form, files=request.files, stream=True, timeout=30, allow_redirects=False)
        
        updated_cookies = requests.utils.dict_from_cookiejar(resp.cookies)
        cookie_dict.update(updated_cookies)
        session['sessoes_proxy'][system_id] = cookie_dict
        session.modified = True
        
        if resp.status_code in [301, 302, 303, 307, 308]:
            original_location = resp.headers.get('Location', '/')
            new_location = url_for('proxy_request', system_id=system_id, path=original_location.lstrip('/'))
            return redirect(new_location, code=resp.status_code)

        content_type = resp.headers.get('Content-Type', '').lower()
        content_to_send = resp.content
        proxy_prefix = url_for('proxy_request', system_id=system_id, path='').rstrip('/')
        
        if 'text/html' in content_type:
            soup = BeautifulSoup(resp.content, 'html.parser')
            current_page_path = url_for('proxy_request', system_id=system_id, path=path)
            tags_to_rewrite = {'a': 'href', 'link': 'href', 'script': 'src', 'img': 'src', 'form': 'action'}
            for tag_name, attr in tags_to_rewrite.items():
                for tag in soup.find_all(tag_name, **{attr: True}):
                    original_url = tag[attr]
                    if urlparse(original_url).scheme or original_url.startswith(('//', '#', 'javascript:', 'data:', 'mailto:')): continue
                    if original_url.startswith('/'): tag[attr] = proxy_prefix + original_url
                    else: tag[attr] = urljoin(current_page_path, original_url)
            
            # --- INTERCEPTADOR FINAL COM CORREÇÃO PARA JQUERY ---
            interceptor_script = f"""
            <script>
                (function() {{
                    if (window.proxyInterceptorLoaded) return;
                    window.proxyInterceptorLoaded = true;

                    const PROXY_PREFIX = '{proxy_prefix}';

                    function rewriteUrl(originalUrl) {{
                        if (!originalUrl || (typeof originalUrl !== 'string') || (!originalUrl.startsWith('http') && originalUrl.indexOf(':') > -1)) return originalUrl;
                        const absoluteUrl = new URL(originalUrl, window.location.href);
                        if (absoluteUrl.origin !== window.location.origin) return originalUrl;
                        if (absoluteUrl.pathname.startsWith(PROXY_PREFIX)) return absoluteUrl.href;
                        absoluteUrl.pathname = PROXY_PREFIX + absoluteUrl.pathname;
                        return absoluteUrl.href;
                    }}

                    // --- PARTE 1 (NOVA E MAIS IMPORTANTE): Interceptador de jQuery.ajax ---
                    // Espera o jQuery carregar e então aplica a correção
                    function patchJQuery() {{
                        if (window.jQuery && window.jQuery.ajax) {{
                            let originalAjax = window.jQuery.ajax;
                            window.jQuery.ajax = function(arg1, arg2) {{
                                let settings = {{}};
                                if (typeof arg1 === 'string') {{
                                    settings.url = arg1;
                                    if (arg2) {{ settings = {{...settings, ...arg2}}; }}
                                }} else {{
                                    settings = arg1;
                                }}
                                
                                if (settings.url) {{
                                    settings.url = rewriteUrl(settings.url);
                                }}
                                
                                // Chama o ajax original com a URL corrigida
                                return originalAjax.call(this, settings);
                            }};
                        }}
                    }}
                    // Tenta aplicar a correção imediatamente e também depois que a página carregar
                    patchJQuery();
                    document.addEventListener('DOMContentLoaded', patchJQuery);

                    // --- PARTE 2: Interceptadores Padrão (continuam importantes) ---
                    const originalXhrOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function(method, url, ...args) {{ originalXhrOpen.call(this, method, rewriteUrl(url), ...args); }};
                    const originalFetch = window.fetch;
                    window.fetch = function(input, init) {{
                        let i = input instanceof Request ? new Request(rewriteUrl(input.url), {{...input}}) : rewriteUrl(input);
                        return originalFetch.call(this, i, init);
                    }};
                    document.addEventListener('click', function(event) {{
                        const link = event.target.closest('a');
                        if (!link || !link.href || event.ctrlKey || event.metaKey || event.shiftKey) return;
                        const rewrittenUrl = rewriteUrl(link.href);
                        if (rewrittenUrl !== link.href) {{ event.preventDefault(); window.location.href = rewrittenUrl; }}
                    }}, true);
                    document.addEventListener('submit', function(event) {{
                        const form = event.target;
                        form.action = rewriteUrl(new URL(form.action, window.location.href).href);
                    }}, true);

                }})();
            </script>
            """
            if soup.head: soup.head.insert(0, BeautifulSoup(interceptor_script, 'html.parser'))
            content_to_send = soup.prettify(encoding='utf-8')
        
        elif 'text/xml' in content_type:
            xml_text = resp.text
            modified_xml_text = xml_text.replace(target_host, proxy_prefix)
            content_to_send = modified_xml_text.encode('utf-8')
        
        # O bloco que reescrevia JS foi REMOVIDO pois era a abordagem errada.
            
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.headers.items() if name.lower() not in excluded_headers]
        return Response(content_to_send, resp.status_code, headers)

    except requests.exceptions.RequestException as e:
        return f"Erro de conexão com o sistema de destino: {e}", 502

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)