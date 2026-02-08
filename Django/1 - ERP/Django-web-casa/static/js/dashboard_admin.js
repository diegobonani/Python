/*
 * dashboard_admin.js
 * Lógica para carregar os cards e modais do Dashboard Administrativo
 * Versão Final - Com Event Delegation e Drill-down de Histórico
 */

document.addEventListener("DOMContentLoaded", function() {
    console.log("Dashboard Admin JS Iniciado.");

    // =========================================================
    // 1. CONFIGURAÇÃO DO SELECT2 (Filtros)
    // =========================================================
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('#filtro-dashboard').select2({
            placeholder: "Filtrar por Usuário, Pet ou Casa...",
            allowClear: true,
            width: '100%'
        });
    }

    // =========================================================
    // 2. ATUALIZAÇÃO DOS CONTADORES (CARDS)
    // =========================================================
    const btnFiltrar = document.getElementById('btn-filtrar-dashboard');
    
    if (btnFiltrar) {
        btnFiltrar.addEventListener('click', function() {
            atualizarDashboard();
        });
    }

    function getSelecaoAtual() {
        if (typeof $ !== 'undefined') {
            return $('#filtro-dashboard').val() || [];
        } else {
            const select = document.getElementById('filtro-dashboard');
            return Array.from(select.selectedOptions).map(opt => opt.value);
        }
    }

    function atualizarDashboard() {
        const selecao = getSelecaoAtual();
        const btn = document.getElementById('btn-filtrar-dashboard');
        
        const textoOriginal = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Atualizando...';

        const url = new URL(window.DASHBOARD_URLS.UPDATE_COUNTS, window.location.origin);
        selecao.forEach(val => url.searchParams.append('selecao[]', val));

        fetch(url)
            .then(res => res.json())
            .then(data => {
                atualizarTexto('count-usuarios', data.total_usuarios);
                atualizarTexto('count-itens-estoque', data.total_itens_estoque);
                atualizarTexto('count-lancamentos-financeiros', 'R$ ' + data.saldo_financeiro);
                atualizarTexto('count-tarefas-rotina', data.total_tarefas_rotina);
                
                if (data.media_calorias) {
                    atualizarTexto('count-alimentacao', data.media_calorias);
                }
            })
            .catch(err => console.error("Erro ao atualizar counts:", err))
            .finally(() => {
                btn.disabled = false;
                btn.innerHTML = textoOriginal;
            });
    }

    function atualizarTexto(id, valor) {
        const el = document.getElementById(id);
        if (el) {
            el.style.opacity = 0;
            setTimeout(() => {
                el.innerText = valor;
                el.style.opacity = 1;
            }, 200);
        }
    }

    // =========================================================
    // 3. LOGICA DOS MODAIS PRINCIPAIS (CARREGAMENTO AJAX)
    // =========================================================

    function carregarModal(modalId, corpoId, urlPartial) {
        const modalEl = document.getElementById(modalId);
        if (!modalEl) {
            console.error(`[ERRO] Modal não encontrado no HTML: ID '${modalId}'`);
            return;
        }

        modalEl.addEventListener('show.bs.modal', function () {
            const container = document.getElementById(corpoId);
            if (!container) return;

            // Verificação de segurança da URL
            if (!urlPartial || urlPartial.trim() === "") {
                console.error(`[ERRO] URL indefinida para o modal: ${modalId}.`);
                container.innerHTML = '<div class="alert alert-danger">Erro de configuração: URL não definida.</div>';
                return;
            }

            const selecao = getSelecaoAtual();

            // Estado de carregamento
            container.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <div class="spinner-border text-info" role="status"></div>
                    <p class="mt-2 small">Buscando dados no servidor...</p>
                </div>
            `;

            const url = new URL(urlPartial, window.location.origin);
            selecao.forEach(val => url.searchParams.append('selecao[]', val));

            console.log(`[DEBUG] Fetching URL: ${url.toString()}`);

            fetch(url)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
                    return response.text();
                })
                .then(html => {
                    container.innerHTML = html;
                })
                .catch(err => {
                    console.error(`[ERRO CRÍTICO] Falha ao carregar modal ${modalId}:`, err);
                    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar: ${err.message}</div>`;
                });
        });
    }

    // --- Inicializa os Listeners dos Modais Principais ---
    if (window.DASHBOARD_URLS) {
        carregarModal('modalUsuarios', 'corpoModalUsuarios', window.DASHBOARD_URLS.PARTIAL_USUARIOS);
        carregarModal('modalEstoque', 'corpoModalEstoque', window.DASHBOARD_URLS.PARTIAL_ESTOQUE);
        carregarModal('modalFinancas', 'corpoModalFinancas', window.DASHBOARD_URLS.PARTIAL_FINANCAS);
        carregarModal('modalRotinas', 'corpoModalRotinas', window.DASHBOARD_URLS.PARTIAL_ROTINAS);
        
        // Modal Alimentação (Geral)
        carregarModal('modalAlimentacao', 'corpoModalAlimentacao', window.DASHBOARD_URLS.PARTIAL_ALIMENTACAO);
    } else {
        console.error("DASHBOARD_URLS não definido no HTML.");
    }

    // =========================================================
    // 4. LÓGICA DO HISTÓRICO NUTRICIONAL (DRILL-DOWN)
    // =========================================================

    // Event Delegation: Detecta cliques no botão de histórico gerado dinamicamente
    // Isso substitui o onclick="" e evita erros no editor de código.
    document.body.addEventListener('click', function(event) {
        // Verifica se o elemento clicado (ou seu pai) tem a classe .js-btn-historico
        const btn = event.target.closest('.js-btn-historico');
        
        if (btn) {
            // Pega o ID do atributo data-user-id (convertido para camelCase: userId)
            const userId = btn.dataset.userId;
            
            if (userId) {
                abrirHistoricoUsuario(userId);
            } else {
                console.error("Botão de histórico encontrado, mas sem atributo data-user-id.");
            }
        }
    });

    function abrirHistoricoUsuario(userId) {
        console.log("Abrindo histórico do user ID:", userId);
        
        const modalEl = document.getElementById('modalHistoricoNutri');
        const container = document.getElementById('corpoModalHistorico');
        
        if(!modalEl || !container) {
            console.error("Modal de histórico (modalHistoricoNutri) não encontrado no HTML.");
            return;
        }

        // 1. Abre o modal (usa getInstance para evitar duplicidade ou cria novo)
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
        
        // 2. Estado de Carregamento
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-info" role="status"></div>
                <p class="mt-2 text-muted small">Carregando histórico do usuário...</p>
            </div>
        `;

        // 3. Monta URL
        if (!window.DASHBOARD_URLS.HISTORICO_USUARIO) {
            container.innerHTML = '<div class="alert alert-danger">URL de histórico não definida.</div>';
            return;
        }

        // Substitui o placeholder '0' pelo ID real do usuário
        const url = window.DASHBOARD_URLS.HISTORICO_USUARIO.replace('0', userId);
        
        // 4. Fetch
        fetch(url)
            .then(r => {
                if(!r.ok) throw new Error("Erro HTTP: " + r.status);
                return r.text();
            })
            .then(html => {
                container.innerHTML = html;
            })
            .catch(err => {
                container.innerHTML = `<div class="alert alert-danger">Erro: ${err.message}</div>`;
                console.error(err);
            });
    }

});