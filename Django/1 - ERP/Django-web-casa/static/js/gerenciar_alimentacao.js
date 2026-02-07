/*
 * static/js/gerenciar_alimentacao.js
 * Versão 5.4 - Refatorado com Event Delegation (Zero erros de editor)
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Gerenciador de Alimentação Iniciado v5.4");

    // Variável de estado do carrinho
    let carrinhoEstoque = [];

    // ========================================================================
    // 1. CARREGAMENTO DE DADOS (GET)
    // ========================================================================

    function carregarMenu(filtro) {
        const container = document.getElementById('tabela-alimentos-container');
        if (!window.URLS_ALIMENTACAO || !container) return;

        const url = `${window.URLS_ALIMENTACAO.TABELA_ALIMENTOS}?filtro=${filtro}`;

        fetch(url)
            .then(response => response.text())
            .then(html => {
                container.innerHTML = html;
            })
            .catch(err => {
                console.error('Erro ao carregar menu:', err);
                container.innerHTML = '<div class="alert alert-danger">Erro ao carregar dados.</div>';
            });
    }

    function carregarDiario(dataSemana = null) {
        const container = document.getElementById('tabela-historico-container');
        if (!window.URLS_ALIMENTACAO || !container) return;

        const filtroEl = document.getElementById('filtro-tipo-refeicao');
        const filtroTipo = filtroEl ? filtroEl.value : 'TODOS';
        
        let url = `${window.URLS_ALIMENTACAO.TABELA_HISTORICO}?tipo_refeicao=${filtroTipo}`;
        if (dataSemana) {
            url += `&semana=${dataSemana}`;
        }

        fetch(url)
            .then(response => response.text())
            .then(html => {
                container.innerHTML = html;
            })
            .catch(err => console.error('Erro ao carregar diário:', err));
    }

    // ========================================================================
    // 2. LISTENERS DE FILTROS (Inputs e Selects)
    // ========================================================================

    // Filtro de Alimentos (Radio Buttons)
    // O HTML deve ter inputs com name="filtroAlimento" e value="TODOS", "SAUDAVEL", etc.
    const radiosFiltro = document.querySelectorAll('input[name="filtroAlimento"]');
    radiosFiltro.forEach(radio => {
        radio.addEventListener('change', function() {
            // Usa o value do input ou um data-filtro
            const filtro = this.value || this.dataset.filtro || 'todos';
            carregarMenu(filtro);
        });
    });

    // Filtro de Tipo de Refeição (Select)
    const selectFiltroRefeicao = document.getElementById('filtro-tipo-refeicao');
    if (selectFiltroRefeicao) {
        selectFiltroRefeicao.addEventListener('change', function() {
            carregarDiario();
        });
    }

    // ========================================================================
    // 3. CARRINHO DE ESTOQUE (Lógica Local)
    // ========================================================================

    const btnAddEstoque = document.querySelector('button[onclick="adicionarAoCarrinhoEstoque()"]') || document.getElementById('btn-add-estoque');
    // Nota: Se você ainda usa onclick no HTML para este botão, remova e use id="btn-add-estoque"
    
    // Listener para Adicionar ao Carrinho (Se o botão tiver ID ou classe específica)
    // Para compatibilidade, procuramos pelo botão dentro do container do estoque
    const containerEstoque = document.getElementById('pills-estoque');
    if (containerEstoque) {
        containerEstoque.addEventListener('click', function(e) {
            // Verifica se clicou no botão de adicionar (ícone ou botão)
            if (e.target.closest('.btn-success') && e.target.closest('.input-group') === null) {
                // Lógica de adicionar
                adicionarAoCarrinho();
            }
        });
    }

    function adicionarAoCarrinho() {
        const selectItem = document.getElementById('select_item_estoque');
        const inputQtd = document.getElementById('input_qtd_estoque');
        const selectLocal = document.getElementById('select_localizacao_estoque');
        
        if (!selectItem.value || !inputQtd.value || parseFloat(inputQtd.value) <= 0) {
            alert("Selecione um item e uma quantidade válida.");
            return;
        }

        const optionItem = selectItem.options[selectItem.selectedIndex];
        const optionLocal = selectLocal.options[selectLocal.selectedIndex];
        const saldoAtual = parseFloat(optionItem.dataset.saldo);
        const qtdDesejada = parseFloat(inputQtd.value);

        if (qtdDesejada > saldoAtual) {
            alert(`Saldo insuficiente! Disponível: ${saldoAtual}`);
            return;
        }

        carrinhoEstoque.push({
            id: selectItem.value,
            nome: optionItem.text,
            local_nome: optionLocal.text,
            quantidade: qtdDesejada,
            unidade: optionItem.dataset.unidade
        });

        inputQtd.value = '';
        selectItem.value = '';
        document.getElementById('info_saldo_estoque').innerHTML = '';
        
        atualizarListaVisual();
    }

    function atualizarListaVisual() {
        const lista = document.getElementById('lista_itens_consumo');
        const aviso = document.getElementById('aviso_lista_vazia');
        const inputJson = document.getElementById('itens_estoque_json');
        
        if(!lista) return;
        lista.innerHTML = '';
        
        if (carrinhoEstoque.length === 0) {
            if(aviso) {
                lista.appendChild(aviso);
                aviso.style.display = 'block';
            }
            if(inputJson) inputJson.value = '';
            return;
        }
        
        if(aviso) aviso.style.display = 'none';

        carrinhoEstoque.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center bg-white';
            
            // Criação segura do HTML sem onclick inline
            li.innerHTML = `
                <div>
                    <i class="fas fa-box text-success me-2"></i>
                    <strong>${item.nome}</strong>
                    <span class="text-muted ms-1">(${item.quantidade} ${item.unidade})</span>
                    <div class="text-muted" style="font-size: 0.7rem;">De: ${item.local_nome}</div>
                </div>
                <button type="button" class="btn btn-link text-danger p-0 js-btn-remover-carrinho" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            lista.appendChild(li);
        });

        if(inputJson) inputJson.value = JSON.stringify(carrinhoEstoque);
    }

    // Listener para Remover do Carrinho (Event Delegation na lista)
    const listaCarrinho = document.getElementById('lista_itens_consumo');
    if (listaCarrinho) {
        listaCarrinho.addEventListener('click', function(e) {
            const btnRemover = e.target.closest('.js-btn-remover-carrinho');
            if (btnRemover) {
                const index = btnRemover.dataset.index;
                carrinhoEstoque.splice(index, 1);
                atualizarListaVisual();
            }
        });
    }

    // Listener para Select de Localização (Carregar Itens)
    const selectLocalizacao = document.getElementById('select_localizacao_estoque');
    if (selectLocalizacao) {
        selectLocalizacao.addEventListener('change', function() {
            carregarItensDoEstoque();
        });
    }

    // Listener para Select de Item (Mostrar Saldo)
    const selectItemEstoque = document.getElementById('select_item_estoque');
    if (selectItemEstoque) {
        selectItemEstoque.addEventListener('change', function() {
            const option = this.options[this.selectedIndex];
            const divInfo = document.getElementById('info_saldo_estoque');
            const spanUnidade = document.getElementById('span_unidade_medida');

            if (option.value) {
                const saldo = option.dataset.saldo;
                const unidade = option.dataset.unidade;
                if(spanUnidade) spanUnidade.textContent = unidade;
                if(divInfo) divInfo.innerHTML = `<i class="fas fa-info-circle me-1"></i>Disp: <strong>${saldo} ${unidade}</strong>`;
            } else {
                if(spanUnidade) spanUnidade.textContent = 'UN';
                if(divInfo) divInfo.innerHTML = '';
            }
        });
    }

    function carregarItensDoEstoque() {
        const localId = document.getElementById('select_localizacao_estoque').value;
        const selectItem = document.getElementById('select_item_estoque');
        
        selectItem.innerHTML = '<option value="">Carregando...</option>';
        selectItem.disabled = true;

        if (!localId) {
            selectItem.innerHTML = '<option value="">Aguardando local...</option>';
            return;
        }

        const url = window.URLS_ALIMENTACAO.API_ITENS.replace('0', localId);

        fetch(url)
            .then(res => res.json())
            .then(data => {
                selectItem.innerHTML = '<option value="">Selecione o Produto...</option>';
                selectItem.disabled = false;

                if (data.length === 0) {
                    selectItem.innerHTML = '<option value="">Nenhum alimento aqui</option>';
                    return;
                }

                data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.id;
                    option.textContent = item.nome;
                    option.dataset.saldo = item.saldo;
                    option.dataset.unidade = item.unidade;
                    selectItem.appendChild(option);
                });
            })
            .catch(err => {
                console.error("Erro itens:", err);
                selectItem.innerHTML = '<option value="">Erro ao buscar itens</option>';
            });
    }


    // ========================================================================
    // 4. AÇÕES GERAIS (EDITAR / EXCLUIR) - EVENT DELEGATION
    // ========================================================================
    
    document.body.addEventListener('click', function(e) {
        
        // --- AÇÃO: NAVEGAÇÃO DE SEMANAS (Novo) ---
        const btnNav = e.target.closest('.js-nav-semana');
        if (btnNav) {
            const dataAlvo = btnNav.dataset.date;
            carregarDiario(dataAlvo);
            return; // Para execução aqui
        }

        // --- AÇÃO: EDITAR ALIMENTO ---
        const btnEditAlimento = e.target.closest('.js-btn-editar-alimento');
        if (btnEditAlimento) {
            editarAlimento(btnEditAlimento.dataset.id);
        }

        // --- AÇÃO: EXCLUIR ALIMENTO ---
        const btnDelAlimento = e.target.closest('.js-btn-excluir-alimento');
        if (btnDelAlimento) {
            excluirAlimento(btnDelAlimento.dataset.id);
        }

        // --- AÇÃO: EDITAR REFEIÇÃO ---
        const btnEditRefeicao = e.target.closest('.js-btn-editar-refeicao');
        if (btnEditRefeicao) {
            editarRefeicao(btnEditRefeicao.dataset.id);
        }

        // --- AÇÃO: EXCLUIR REFEIÇÃO ---
        const btnDelRefeicao = e.target.closest('.js-btn-excluir-refeicao');
        if (btnDelRefeicao) {
            excluirRefeicao(btnDelRefeicao.dataset.id);
        }
    });

    // Função interna: Editar Alimento
    function editarAlimento(id) {
        const url = window.URLS_ALIMENTACAO.GET_ALIMENTO_JSON.replace('0', id);
        fetch(url).then(r => r.json()).then(data => {
            const form = document.getElementById('formAlimento');
            document.getElementById('alimento_id').value = data.id;
            
            const setVal = (sel, val) => { const el = form.querySelector(`[name="${sel}"]`); if (el) el.value = val; };
            
            setVal('nome', data.nome);
            setVal('classificacao', data.classificacao);
            setVal('calorias', data.calorias);

            const toggle = document.getElementById('toggleTabelaNutricional');
            const area = document.getElementById('area-nutricional');
            
            if (data.tem_nutricao) {
                toggle.checked = true;
                area.classList.remove('d-none');
                setVal('proteinas', data.proteinas);
                setVal('carboidratos', data.carboidratos);
                setVal('gorduras_totais', data.gorduras_totais);
                setVal('acucares', data.acucares);
                setVal('sodio', data.sodio);
                setVal('fibras', data.fibras);
            } else {
                toggle.checked = false;
                area.classList.add('d-none');
            }

            const modal = new bootstrap.Modal(document.getElementById('modalAlimento'));
            modal.show();
        });
    }

    // Função interna: Excluir Alimento
    function excluirAlimento(id) {
        if (!confirm('Remover este item do menu?')) return;
        const url = window.URLS_ALIMENTACAO.EXCLUIR_ALIMENTO.replace('0', id);
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).then(res => res.json()).then(data => {
            if (data.success) carregarMenu('todos');
            else alert('Erro ao excluir.');
        });
    }

    // Função interna: Editar Refeição
    function editarRefeicao(id) {
        const url = window.URLS_ALIMENTACAO.GET_REFEICAO_JSON.replace('0', id);
        fetch(url).then(r => r.json()).then(data => {
            const form = document.getElementById('formRefeicao');
            form.reset();
            document.getElementById('refeicao_id').value = data.id;
            form.querySelector('[name="data"]').value = data.data;
            form.querySelector('[name="tipo"]').value = data.tipo;
            
            const desc = form.querySelector('[name="descricao_adicional"]');
            if(desc) desc.value = data.descricao_adicional || '';

            // Select Multiple
            const sel = form.querySelector('[name="alimentos"]');
            if (sel) {
                Array.from(sel.options).forEach(o => o.selected = false);
                if (data.alimentos) {
                    data.alimentos.forEach(idAlimento => {
                        const op = sel.querySelector(`option[value="${idAlimento}"]`);
                        if(op) op.selected = true;
                    });
                }
            }

            // Reseta carrinho e aba
            carrinhoEstoque = [];
            atualizarListaVisual();
            const tabManual = document.getElementById('pills-manual-tab');
            if(tabManual) new bootstrap.Tab(tabManual).show();

            const modal = new bootstrap.Modal(document.getElementById('modalRefeicao'));
            modal.show();
        });
    }

    // Função interna: Excluir Refeição
    function excluirRefeicao(id) {
        if (!confirm('Apagar registro? Itens de estoque serão devolvidos.')) return;
        const url = window.URLS_ALIMENTACAO.EXCLUIR_REFEICAO.replace('0', id);
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).then(res => res.json()).then(data => {
            if (data.success) {
                carregarDiario();
                if (typeof Swal !== 'undefined') Swal.fire('Sucesso', data.message, 'success');
            } else {
                alert('Erro: ' + data.message);
            }
        });
    }


    // ========================================================================
    // 5. INICIALIZAÇÃO E SUBMITS
    // ========================================================================

    // Carregamento Inicial
    if (typeof window.URLS_ALIMENTACAO !== 'undefined') {
        carregarMenu('todos');
        carregarDiario();
        // Se tiver dashboard, chama aqui
        if (typeof carregarDashboard === 'function') carregarDashboard();
    }

    // Toggle Nutricional
    const toggleNutri = document.getElementById('toggleTabelaNutricional');
    const areaNutri = document.getElementById('area-nutricional');
    if (toggleNutri && areaNutri) {
        toggleNutri.addEventListener('change', function() {
            if (this.checked) {
                areaNutri.classList.remove('d-none');
                areaNutri.classList.add('animate__animated', 'animate__fadeIn');
            } else {
                areaNutri.classList.add('d-none');
                areaNutri.classList.remove('animate__animated', 'animate__fadeIn');
            }
        });
    }

    // Listener do Botão "Nova Refeição"
    const btnNovaRefeicao = document.getElementById('btnRegistrarHoje');
    if (btnNovaRefeicao) {
        btnNovaRefeicao.addEventListener('click', function() {
            const form = document.getElementById('formRefeicao');
            if (form) {
                form.reset();
                form.querySelector('[name="data"]').value = new Date().toISOString().split('T')[0];
                document.getElementById('refeicao_id').value = '';
                
                carrinhoEstoque = [];
                atualizarListaVisual();
                
                const tabManual = document.getElementById('pills-manual-tab');
                if(tabManual) new bootstrap.Tab(tabManual).show();
            }
            new bootstrap.Modal(document.getElementById('modalRefeicao')).show();
        });
    }

    // Submit dos Forms (Genérico)
    ['formAlimento', 'formRefeicao'].forEach(formId => {
        const form = document.getElementById(formId);
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                salvarDados(this, formId === 'formAlimento' ? 'modalAlimento' : 'modalRefeicao', () => {
                    if (formId === 'formAlimento') carregarMenu('todos');
                    else carregarDiario();
                    // Atualiza Dashboard se existir
                    if (typeof carregarDashboard === 'function') carregarDashboard();
                });
            });
        }
    });

    // Função de Salvar Genérica
    function salvarDados(form, modalId, callbackSucesso) {
        const url = form.action;
        const formData = new FormData(form);
        const btnSubmit = form.querySelector('button[type="submit"]');
        let textoOriginal = '';

        if (btnSubmit) {
            textoOriginal = btnSubmit.innerHTML;
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';
        }

        fetch(url, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const modalEl = document.getElementById(modalId);
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) modalInstance.hide();
                
                form.reset();
                const idInput = form.querySelector('input[type="hidden"][name$="_id"]');
                if (idInput) idInput.value = '';

                if (typeof Swal !== 'undefined') {
                    Swal.fire({ icon: 'success', title: 'Sucesso!', text: data.message, timer: 1500, showConfirmButton: false });
                }
                if (callbackSucesso) callbackSucesso();
            } else {
                console.error(data.errors);
                let msg = 'Erro de validação.';
                try {
                    const firstField = Object.keys(data.errors)[0];
                    msg = `${firstField.toUpperCase()}: ${data.errors[firstField][0].message || data.errors[firstField][0]}`;
                } catch(e) {}
                alert(msg);
            }
        })
        .catch(err => {
            console.error('Erro:', err);
            alert('Erro de conexão.');
        })
        .finally(() => {
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = textoOriginal;
            }
        });
    }

    // Helper de Cookie CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});