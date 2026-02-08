/**
 * STOCK MANAGER PRO - V26.25 (HISTORY FILTERS & GLOBAL FIX)
 * -------------------------------------------------------------------------
 * - Atualização Completa do TableManager para suportar filtros avançados
 * na aba Histórico (Ação, Usuário, Imóvel, Setor, Dono).
 * - Mantidas todas as lógicas anteriores (Scanner, Baixa, Edição, Compras).
 * -------------------------------------------------------------------------
 */

$(document).ready(function() {
    "use strict";

    console.log(">>> Gerenciador de Estoque Iniciado (V26.25)...");

    // =========================================================================
    // 1. CONFIGURAÇÕES
    // =========================================================================
    const Config = {
        urls: {
            tabela: window.URL_TABELA_ESTOQUE,
            historico: window.URL_ABA_HISTORICO_ESTOQUE,
            simulacao: window.URL_ABA_SIMULACAO,
            filtroOpcoes: window.URL_FILTRO_OPCOES,
            categorias: window.URL_CATEGORIAS,
            locais: window.URL_GET_LOCALIZACOES,
            getComodos: window.URL_GET_COMODOS,
            lerNota: window.URL_LER_NOTA,
            getCompraItens: window.URL_GET_COMPRA_ITENS,
            getCompraJson: window.URL_GET_COMPRA_JSON,
            editarCompra: window.URL_EDITAR_COMPRA,
            lancarFinanceiro: window.URL_LANCAR_FINANCEIRO,
            excluirCompra: window.URL_EXCLUIR_COMPRA,
            getDestinatarios: window.URL_GET_DESTINATARIOS_JSON || '/estoque/ajax/destinatarios/',
            dtLang: window.DATATABLES_LANGUAGE_URL || '//cdn.datatables.net/plug-ins/1.13.11/i18n/pt-BR.json'
        },
        dtStandard: {
            responsive: true, destroy: true, retrieve: true,
            language: { url: window.DATATABLES_LANGUAGE_URL || '//cdn.datatables.net/plug-ins/1.13.11/i18n/pt-BR.json' },
            pageLength: 25, lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Todos"]],
            autoWidth: false, order: [[0, 'desc']]
        }
    };

    const Utils = {
        parseBrToFloat: (val) => {
            if (!val) return 0;
            let strVal = val.toString().replace(/[R$\s]/g, '').trim();
            if (strVal === '') return 0;
            if (strVal.includes(',')) strVal = strVal.replace(/\./g, '').replace(',', '.');
            return parseFloat(strVal) || 0;
        },
        formatMoneyATM: (v) => {
            if (!v) return ""; v = v.toString().replace(/\D/g, "");
            return (parseFloat(v)/100).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        },
        formatQuantityATM: (v, isDecimal = true) => {
            if (!v) return ""; v = v.toString().replace(/\D/g, "");
            if (!isDecimal) return v;
            return (parseFloat(v)/1000).toFixed(3).replace('.', ',');
        },
        isDecimalUnit: (unitStr) => {
            if (!unitStr) return false;
            const u = unitStr.toUpperCase().trim();
            return ['KG', 'L', 'M', 'LT', 'ML', 'GR', 'GRAMA', 'LITRO', 'METRO'].some(x => u === x || u.startsWith(x));
        },
        showToast: (msg) => {
            const toastEl = document.getElementById('successToast');
            if(toastEl){ $('#successToast .toast-body').text(msg); const toast = new bootstrap.Toast(toastEl); toast.show(); } else { alert(msg); }
        },
        getModal: (id) => {
            const el = document.getElementById(id); return el ? new bootstrap.Modal(el) : null;
        },
        normalizeSefazUrl: (input) => {
            let clean = input.trim().replace(/\s/g, '');
            if (/^\d{44}$/.test(clean)) return `https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaPublica.aspx?chave=${clean}`;
            if (clean.startsWith('www.')) return 'https://' + clean;
            return clean;
        }
    };

    $('.form-select').each(function() { if (!$(this).hasClass('select2-hidden-accessible')) $(this).select2({ theme: 'bootstrap-5', width: '100%' }); });

    // =========================================================================
    // 2. SCANNER MANAGER
    // =========================================================================
    window.ScannerManager = {
        scannerInstance: null, dadosImportados: null,
        initInputListener: function() {
            const $input = $('#urlNotaInput'); const $statusBox = $('#status-leitura-container'); const $btnBuscar = $('#btn-buscar-nota');
            if ($input.length === 0) return;
            $input.off('input paste').on('input paste', function() {
                let val = $(this).val().replace(/\s/g, ''); 
                if(val.length === 0) { $input.removeClass('is-valid is-invalid text-success'); $statusBox.addClass('d-none'); return; }
                if (/^\d{44}$/.test(val)) { 
                    $input.addClass('is-valid text-success').removeClass('is-invalid'); 
                    $statusBox.removeClass('d-none').addClass('alert-light border').text('Chave válida! Conectando...'); 
                    window.ScannerManager.fetchNotaData(Utils.normalizeSefazUrl(val)); 
                }
            });
            $btnBuscar.off('click').on('click', function(e) { e.preventDefault(); window.ScannerManager.processManualUrl(); });
        },
        processManualUrl: function() {
            const rawInput = $('#urlNotaInput').val(); if (!rawInput) { alert("Cole o link."); return; }
            this.fetchNotaData(Utils.normalizeSefazUrl(rawInput));
        },
        fetchNotaData: function(url) {
            const $spinner = $('#status-spinner'); $spinner.removeClass('d-none');
            $.ajax({ url: Config.urls.lerNota, data: { url: url },
                success: (data) => {
                    $spinner.addClass('d-none');
                    if (data.success) {
                        this.dadosImportados = data;
                        setTimeout(() => { this.populateManualTab(data); this.buildTriageTable(data); new bootstrap.Tab(document.querySelector('#manual-tab')).show(); }, 1000);
                    } else { alert(data.erro); }
                }, error: () => { $spinner.addClass('d-none'); alert('Erro conexão'); }
            });
        },
        populateManualTab: function(data) {
            $('#id_supermercado').val(data.mercado); $('#id_cidade').val(data.cidade); $('#id_data_compra').val(data.data_emissao); $('#id_valor_total').val(Utils.formatMoneyATM(data.valor_total.toFixed(2).replace('.', '')));
        },
        buildTriageTable: function(data) {
            const $tbody = $('#tbody-triagem'); $('#area-triagem-container').removeClass('d-none'); $tbody.empty();
            data.itens.forEach((item, idx) => {
                let html = `<tr id="row-${idx}" data-idx="${idx}"><td>${item.nome}</td><td><input type="number" class="form-control form-control-sm item-qtd" value="${item.quantidade}"></td><td><select class="form-select form-select-sm select-setor" onchange="ScannerManager.changeSetor(${idx})"><option value="HISTORICO">Histórico</option><option value="CASA">Casa</option><option value="PET">Pet</option><option value="USUARIO">Pessoal</option></select></td><td><select class="form-select form-select-sm select-destino d-none" disabled></select></td></tr>`;
                $tbody.append(html);
            });
        },
        changeSetor: function(idx) {
            const row = $(`#row-${idx}`); const setor = row.find('.select-setor').val(); const destino = row.find('.select-destino'); const opts = this.dadosImportados.opcoes_destino;
            destino.empty().addClass('d-none').prop('disabled', true);
            if (setor === 'HISTORICO') return;
            let lista = (setor === 'CASA') ? opts.comodos : (setor === 'PET') ? opts.pets : opts.usuarios;
            destino.append(`<option value="">Selecione...</option>`);
            lista.forEach(o => { destino.append(new Option(o.nome || o.nome_pet || o.username, o.id)); });
            destino.removeClass('d-none').prop('disabled', false);
        },
        collectTriageData: function() {
            if (!this.dadosImportados) return null;
            let r = [];
            $('#tbody-triagem tr').each(function() {
                const idx = $(this).data('idx'); const i = ScannerManager.dadosImportados.itens[idx];
                r.push({ nome: i.nome, preco_unitario: i.preco_unitario, unidade: i.unidade, quantidade: $(this).find('.item-qtd').val(), destino_tipo: $(this).find('.select-setor').val(), destino_id: $(this).find('.select-destino').val() });
            });
            return JSON.stringify(r);
        }
    };

    // =========================================================================
    // 3. PURCHASE MANAGER
    // =========================================================================
    const PurchaseManager = {
        allAccountOptions: [], 
        init: function() { 
            this.setupFinanceFilter();

            // 1. LANÇAR FINANCEIRO
            $(document).on('click', '.btn-lancar-despesa', function(e) { 
                e.preventDefault(); 
                $('#valor-despesa-modal').text('R$ ' + parseFloat($(this).data('valor')).toFixed(2).replace('.', ',')); 
                $('#formLancarDespesa').data('id', $(this).data('id')); 
                Utils.getModal('modalLancarDespesa').show(); 
            });

            $('#formLancarDespesa').off('submit').on('submit', function(e) { 
                e.preventDefault(); 
                const id = $(this).data('id');
                const btn = $(this).find('button[type="submit"]');
                btn.prop('disabled',true).html('Salvando...');
                
                $.ajax({ 
                    url: Config.urls.lancarFinanceiro + id + '/', 
                    type: 'POST', 
                    data: $(this).serialize(), 
                    success: (res) => { 
                        Utils.getModal('modalLancarDespesa').hide(); 
                        if(res.success){ location.reload(); } 
                    },
                    complete: () => btn.prop('disabled',false).html('Confirmar Lançamento')
                }); 
            });

            // 2. EXCLUIR COMPRA
            $(document).on('click', '.btn-excluir-compra', function(e) { 
                e.preventDefault(); 
                const id = $(this).data('id');
                $('#formConfirmacao')
                    .data('id', id)
                    .data('type', 'compra')
                    .attr('action', Config.urls.excluirCompra + id + '/'); 
                $('#modalConfirmarTexto').text('Excluir compra? Todos os itens associados serão perdidos.'); 
                Utils.getModal('modalConfirmarExclusao').show(); 
            });

            // 3. DETALHES COMPRA
            $(document).on('click', '.btn-detalhes-compra', function(e) {
                e.preventDefault();
                const id = $(this).data('id');
                $('#tbody-detalhes-compra').html('<tr><td colspan="4" class="text-center">Carregando...</td></tr>');
                Utils.getModal('modalDetalhesCompra').show();

                $.ajax({
                    url: Config.urls.getCompraItens + id + '/',
                    success: (res) => {
                        $('#detalhe-mercado').text(res.supermercado); 
                        $('#detalhe-data').text(res.data);
                        let html = '';
                        if(res.itens && res.itens.length > 0){
                            res.itens.forEach(i => {
                                html += `<tr>
                                    <td>${i.nome}<br><small class="text-muted">${i.local}</small></td>
                                    <td>${i.quantidade} ${i.unidade}</td>
                                    <td>R$ ${parseFloat(i.valor_unit).toFixed(2).replace('.',',')}</td>
                                    <td class="fw-bold">R$ ${parseFloat(i.total).toFixed(2).replace('.',',')}</td>
                                </tr>`;
                            });
                        } else {
                            html = '<tr><td colspan="4" class="text-center">Nenhum item registrado.</td></tr>';
                        }
                        $('#tbody-detalhes-compra').html(html);
                    }
                });
            });

            // 4. EDITAR COMPRA (CABEÇALHO)
            $(document).on('click', '.btn-editar-compra', function(e) { 
                e.preventDefault(); 
                let id = $(this).data('id'); 
                $.ajax({ 
                    url: Config.urls.getCompraJson + id + '/', 
                    success: (d) => { 
                        $('#id_compra_editar').val(id); 
                        $('#edit_supermercado').val(d.supermercado); 
                        $('#edit_cidade').val(d.cidade); 
                        $('#edit_data_compra').val(d.data_compra); 
                        Utils.getModal('modalEditarCompra').show(); 
                    }
                }); 
            });

            // Submit Edição Compra
            $('#formEditarCompra').off('submit').on('submit', function(e) { 
                e.preventDefault(); 
                const id = $('#id_compra_editar').val();
                const btn = $(this).find('button[type="submit"]');
                const btnOriginal = btn.html();
                
                btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Salvando...');

                $.ajax({ 
                    url: Config.urls.editarCompra + id + '/', 
                    type: 'POST', 
                    data: $(this).serialize(), 
                    success: (res) => { 
                        if(res.success) location.reload(); 
                    },
                    error: (xhr) => {
                        btn.prop('disabled', false).html(btnOriginal);
                        if (xhr.status === 400 && xhr.responseJSON && xhr.responseJSON.errors) {
                            let msg = "Erro na validação:\n";
                            $.each(xhr.responseJSON.errors, function(field, errors) {
                                msg += `- ${field.toUpperCase()}: ${errors[0].message}\n`;
                            });
                            alert(msg);
                        } else {
                            alert("Erro ao salvar alterações. Verifique os dados.");
                        }
                    }
                }); 
            });
        },

        setupFinanceFilter: function() { 
            const $f=$('#id_filtro_usuario_despesa'); 
            const $c=$('#id_conta_despesa'); 
            if(!this.allAccountOptions.length) {
                $c.find('option').each((i,e)=>{ 
                    if($(e).val()) this.allAccountOptions.push({val:$(e).val(), text:$(e).text()}); 
                }); 
            }
            $f.on('change', ()=>{ 
                $c.empty().append('<option value="">Selecione...</option>'); 
                let u=$f.val(); 
                this.allAccountOptions.forEach(o => { 
                    if(u==='TODOS'||o.text.toUpperCase().startsWith(u+' -')) $c.append(new Option(o.text, o.val)); 
                }); 
            }); 
        }
    };

    // =========================================================================
    // 4. MANAGERS (TABLE & UI)
    // =========================================================================
    const UIManager = {
        loadOwnerOptions: function() {
            const s=$('#filtro-setor').val(), i=$('#filtro-imovel-global').val(), $el=$('#filtro-owner');
            $el.prop('disabled',true).html('<option>Carregando...</option>');
            if(!s||s==='TODOS'){ $el.html('<option value="">-</option>'); return; }
            $.ajax({url:Config.urls.filtroOpcoes, data:{setor:s, imovel_id:i}, success:(d)=>{
                $el.html('<option value="">Todos</option>'); if(d.opcoes) d.opcoes.forEach(o=>$el.append(new Option(o.text, o.id))); $el.prop('disabled',false);
            }});
        },
        updateButtons: function(abaForcada=null) {
            let setor=$('#filtro-setor').val()||'TODOS', aba=abaForcada||$('.nav-link.active').attr('id')||'geral-tab';
            $('#container-botoes button').addClass('d-none');
            if(aba==='compras-tab') $('#btn-acao-compra').removeClass('d-none');
            else if(['geral-tab','geral-tab-pane'].includes(aba)){
                if(['CASA','TODOS'].includes(setor)) $('#btn-acao-casa').removeClass('d-none');
                if(['PET','TODOS'].includes(setor)) $('#btn-acao-pet').removeClass('d-none');
                if(['USUARIO','TODOS'].includes(setor)) $('#btn-acao-user').removeClass('d-none');
            }
        }
    };

    const TableManager = {
        getImovelId: function() { var el = document.getElementById('filtro-imovel-global'); return el ? el.value : 'TODOS'; },
        
        reloadPrincipal: function() {
            const $c = $('#tabela-container'); 
            if($c.children().length === 0) $c.html('<div class="text-center p-5"><div class="spinner-border text-primary"></div></div>');
            
            $.ajax({ url: Config.urls.tabela, data: { setor: $('#filtro-setor').val(), owner_id: $('#filtro-owner').val(), data_filtro: $('#filtro_data_estoque').val(), imovel_id: this.getImovelId(), template_sufixo: '_tabela_estoque_unificada.html' },
                success: function(html) { $c.html(html); setTimeout(() => { try{ if($('#tabela-principal').length) $('#tabela-principal').DataTable({ ...Config.dtStandard, columnDefs: [{ targets: 'no-sort', orderable: false }] }); }catch(e){} }, 50); }
            });
        },
        
        loadHistorico: function(force=false) { 
            const container = $('#historico-estoque-container');
            const params = {
                imovel_id: this.getImovelId(),
                setor: $('#filtro-setor').val(),       
                owner_id: $('#filtro-owner').val(),    
                acao: $('#filtro-historico-acao').val(), 
                usuario_log: $('#filtro-historico-user').val() 
            };
            const queryString = $.param(params);

            if(container.children().length <= 1 || force) {
                container.html('<div class="text-center p-5"><div class="spinner-border text-secondary"></div><p class="text-muted small">Filtrando histórico...</p></div>');
                container.load(`${Config.urls.historico}?${queryString}`, () => { 
                    try { $('#tb-historico-ajax').DataTable({...Config.dtStandard, order: [[0, 'desc']]}); } catch(e){} 
                }); 
            }
        },
        
        loadSimulacao: function() { $('#simulacao-container').load(`${Config.urls.simulacao}?imovel_id=${this.getImovelId()}`, ()=>{ $('.form-select').select2({theme:'bootstrap-5', width:'100%'}); }); },
        initCompras: function() { if ($('#tabela-listas-compra').length) try{ $('#tabela-listas-compra').DataTable({...Config.dtStandard}); }catch(e){} }
    };
    
    // =========================================================================
    // 5. CORE LOGIC (VISUAL & RULES)
    // =========================================================================
    const VisualLogic = {
        loadComodos: function(imovelId, $modalContext) {
            var $comodo = $modalContext.find('select[name="comodo"]'), $local = $modalContext.find('select[name="localizacao"]');
            $comodo.empty().append('<option value="">Carregando...</option>').prop('disabled', true);
            $local.empty().append('<option value="">-</option>').prop('disabled', true);
            if (imovelId && imovelId !== 'TODOS') {
                $.ajax({ url: Config.urls.getComodos, data: { imovel_id: imovelId }, success: function(d) {
                    $comodo.empty().append('<option value="">Selecione...</option>'); d.forEach(i => $comodo.append(new Option(i.nome, i.id))); $comodo.prop('disabled', false);
                }});
            } else { $comodo.empty().append('<option>Selecione o Imóvel</option>'); }
        },
        loadLocais: function(comodoId, $modalContext) {
            var $local = $modalContext.find('select[name="localizacao"]');
            $local.empty().append('<option>Carregando...</option>').prop('disabled', true);
            if (comodoId) {
                $.ajax({ url: Config.urls.locais, data: { comodo_id: comodoId }, success: (d) => { 
                    $local.empty().append('<option value="">Selecione...</option>'); d.forEach(l => $local.append(new Option(l.nome, l.id))); $local.prop('disabled', false);
                }});
            } else { $local.empty().append('<option>Selecione o cômodo</option>'); }
        },
        bindSmartModal: function() {
            $('#modalAdicionarCasa').on('show.bs.modal', function () {
                var g = $('#filtro-imovel-global').val(), $s = $(this).find('select[name="imovel"]'), $w = $(this).find('#wrapper-imovel-modal');
                if (g && g !== 'TODOS') { $w.hide(); $s.val(g); VisualLogic.loadComodos(g, $(this).find('.modal-body')); } else { $w.show(); $s.val(''); }
                VisualLogic.bindUnitLogic(this);
            });
            $('#modalAdicionarPet, #modalAdicionarUsuario').on('show.bs.modal', function() { VisualLogic.bindUnitLogic(this); });
        },
        bindCascades: function() {
            $(document).on('change', 'select[name="imovel"]', function() { VisualLogic.loadComodos($(this).val(), $(this).closest('.modal-body')); });
            $(document).on('change', 'select[name="comodo"]', function() { VisualLogic.loadLocais($(this).val(), $(this).closest('.modal-body')); });
            
            const loadCats = (setor, $select) => {
                $select.html('<option>Carregando...</option>');
                $.ajax({ url: Config.urls.categorias, data: { setor: setor }, success: (d) => {
                    $select.html('<option value="">Selecione...</option>'); d.forEach(c => $select.append(new Option(c.nome_categoria, c.id)));
                }});
            };
            $('#modalAdicionarCasa').on('show.bs.modal', function() { loadCats('CASA', $(this).find('select[name="categoria"]')); });
            $('#modalAdicionarPet').on('show.bs.modal', function() { loadCats('PET', $(this).find('select[name="categoria"]')); });
            $('#modalAdicionarUsuario').on('show.bs.modal', function() { loadCats('USUARIO', $(this).find('select[name="categoria"]')); });
        },
        bindUnitLogic: function(modal) {
            const $m = $(modal), $u = $m.find('select[name="unidade"]'), $q = $m.find('input[name="quantidade"]'), $p = $m.find('input[name="preco_unitario"]');
            let $pw = $m.find('.wrapper-preco-box'); if(!$pw.length) $pw = $p.closest('.col-6');
            const $span = $m.find('.span-unidade');
            
            if ($pw.find('.simulador-preco-container').length === 0) $pw.append('<div class="simulador-preco-container text-success small fw-bold mt-1 d-none"></div>');
            const $sim = $pw.find('.simulador-preco-container');

            const update = () => {
                const txt = $u.find('option:selected').text().toUpperCase();
                let sigla = "UN"; if(txt.includes('-')) sigla = txt.split('-')[0].trim();
                if($span.length) $span.text(sigla);

                const isDecimal = Utils.isDecimalUnit(txt);
                
                if (!isDecimal) { $pw.hide(); $q.attr('step', '1'); let v = parseFloat($q.val().replace(',','.'))||0; if(v>0 && v%1!==0) $q.val(Math.floor(v)); } 
                else { $pw.show(); $q.attr('step', '0.001'); }
                calc();
            };
            const calc = () => {
                if ($pw.is(':hidden')) { $sim.addClass('d-none'); return; }
                let q = Utils.parseBrToFloat($q.val()), p = Utils.parseBrToFloat($p.val()), t = q * p;
                if (t > 0) $sim.removeClass('d-none').html(`<i class="fas fa-calculator"></i> Total: R$ ${t.toFixed(2).replace('.', ',')}`); else $sim.addClass('d-none');
            };
            $u.off('change').on('change', update); $q.off('input').on('input', calc); $p.off('input').on('input', function() { $(this).val(Utils.formatMoneyATM($(this).val())); calc(); });
            setTimeout(update, 200);
        },
        bindRepositionHub: function() {
            $(document).on('change', '#id_setor_destino', function() {
                var s = $(this).val(), i = $('#filtro-imovel-global').val(), $d = $('#id_destinatarios');
                $.ajax({ url: Config.urls.getDestinatarios, data: { setor: s, imovel_id: i }, success: function(res) {
                    $d.empty(); res.destinatarios.forEach(o => $d.append(new Option(o.label, o.id))); $d.prop('disabled', false);
                }});
            });
        }
    };

    // =========================================================================
    // 6. FORM HANDLERS (CRUD)
    // =========================================================================
    const FormHandler = {
        init: function() {
            // A. Money Input
            $('#id_valor_total').removeAttr('readonly').off('input').on('input', function() {
                let val = $(this).val().replace(/\D/g, ''); 
                if (val === '') { $(this).val(''); return; }
                $(this).val(Utils.formatMoneyATM(val));
            });

            // B. Submit Geral (Formulários AJAX)
            $(document).on('submit', '.form-ajax, #formAdicionarCompra', function(e) {
                e.preventDefault(); 
                const form = $(this);
                const modal = form.closest('.modal'); 
                const isCompra = form.attr('id') === 'formAdicionarCompra';

                let formData = new FormData(this);

                if (isCompra) {
                    if (!formData.get('supermercado')) { alert("Por favor, informe o Local da Compra."); return; }
                    if (window.ScannerManager) {
                        const jsonTriagem = window.ScannerManager.collectTriageData();
                        if (jsonTriagem) formData.set('itens_triagem_json', jsonTriagem);
                    }
                }

                ['quantidade', 'estoque_minimo', 'estoque_ideal', 'preco_unitario', 'valor_total'].forEach(f => { 
                    if(formData.has(f)) formData.set(f, Utils.parseBrToFloat(formData.get(f))); 
                });
                
                const btnSubmit = form.find('button[type="submit"]');
                const btnOriginal = btnSubmit.html();
                btnSubmit.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Processando...');

                $.ajax({ 
                    type: 'POST', url: form.attr('action'), data: formData, processData: false, contentType: false,
                    success: function(res) { 
                        btnSubmit.prop('disabled', false).html(btnOriginal);
                        if(res.success) { 
                            if(modal.length) modal.modal('hide'); 
                            form[0].reset(); 
                            Utils.showToast(res.message || "Sucesso!"); 
                            if (isCompra) { setTimeout(() => window.location.reload(), 1000); } 
                            else { TableManager.reloadPrincipal(); }
                        } else { alert('Erro: ' + (res.message || JSON.stringify(res.errors))); } 
                    },
                    error: function(xhr) {
                        btnSubmit.prop('disabled', false).html(btnOriginal);
                        alert('Erro de comunicação com o servidor.');
                    }
                });
            });

            // C. Edição Item (3 Modais)
            $(document).on('click', '.btn-editar-item-casa, .btn-editar-item-pet, .btn-editar-item-usuario', function() {
                 const id = $(this).data('id'); 
                 let modalId, formId;
                 if ($(this).hasClass('btn-editar-item-casa')) { modalId = 'modalEditarItemCasa'; formId = '#formEditarItemCasa'; } 
                 else if ($(this).hasClass('btn-editar-item-pet')) { modalId = 'modalEditarItemPet'; formId = '#formEditarItemPet'; } 
                 else { modalId = 'modalEditarItemUsuario'; formId = '#formEditarItemUsuario'; }

                 const form = $(formId);
                 form.attr('action', `/estoque/ajax/item/${id}/editar/`); 
                 $.ajax({ url: `/estoque/ajax/item/${id}/json/`, success: (d) => { 
                     form.find('input[name="nome_item"]').val(d.nome_item);
                     form.find('input[name="quantidade"]').val(Utils.formatQuantityATM(d.quantidade.toString()));
                     form.find('input[name="estoque_minimo"]').val(Utils.formatQuantityATM(d.estoque_minimo.toString()));
                     form.find('input[name="estoque_ideal"]').val(Utils.formatQuantityATM(d.estoque_ideal.toString()));
                     if(d.categoria_id) form.find('select[name="categoria"]').val(d.categoria_id);

                     if (modalId === 'modalEditarItemCasa') {
                         form.find('input[name="preco_unitario"]').val(Utils.formatMoneyATM(d.preco_unitario.toString()));
                         if(d.unidade_id) form.find('select[name="unidade"]').val(d.unidade_id);
                         if(d.comodo_id) form.find('select[name="comodo"]').html(`<option value="${d.comodo_id}" selected>Atual</option>`);
                         if(d.localizacao_id) form.find('select[name="localizacao"]').html(`<option value="${d.localizacao_id}" selected>Atual</option>`);
                     } else if (modalId === 'modalEditarItemPet') {
                         form.find('input[name="preco_unitario"]').val(Utils.formatMoneyATM(d.preco_unitario.toString()));
                         if(d.unidade_id) form.find('select[name="unidade"]').val(d.unidade_id);
                         if(d.pet_id) form.find('select[name="pet_id"]').val(d.pet_id);
                     } else if (modalId === 'modalEditarItemUsuario') {
                         if(d.usuario_id) form.find('select[name="usuario_id"]').val(d.usuario_id);
                     }
                     const modalEl = document.getElementById(modalId);
                     const modalObj = new bootstrap.Modal(modalEl);
                     modalObj.show();
                     VisualLogic.bindUnitLogic(modalEl);
                     form.find('select[name="unidade"]').trigger('change');
                 }});
            });

            // D. Dar Baixa
            $(document).on('click', '.btn-dar-baixa', function() {
                const id = $(this).data('id'); 
                const form = $('#formDarBaixa');
                const unidadeBtn = $(this).data('unidade');

                form.attr('action', `/estoque/ajax/item/${id}/baixa/`);
                $('#baixa-input-qtd').val('').data('is-decimal', false); 
                $('#baixa-display-atual').text('...');
                $('#baixa-display-final').text('...');
                $('#btn-confirma-baixa').prop('disabled', true);
                $('#msg-erro-baixa').addClass('d-none');

                $.ajax({ url: `/estoque/ajax/item/${id}/json/`, success: function(data) {
                    $('#baixa-nome-item').text(data.nome_item);
                    const estoqueAtual = parseFloat(data.quantidade);
                    $('#hidden-estoque-atual').val(estoqueAtual);
                    const unidade = unidadeBtn || data.unidade_sigla || 'UN';
                    const isDecimal = Utils.isDecimalUnit(unidade);
                    
                    $('#baixa-input-qtd').data('is-decimal', isDecimal);
                    $('#baixa-span-unidade').text(unidade);
                    
                    let txtAtual = isDecimal ? estoqueAtual.toFixed(3).replace(/\.?0+$/, '') : Math.floor(estoqueAtual);
                    $('#baixa-display-atual').text(txtAtual + ' ' + unidade);
                    $('#baixa-display-final').text(txtAtual + ' ' + unidade);

                    if(isDecimal) $('#baixa-input-qtd').attr('step', '0.001').attr('placeholder', '0,000');
                    else $('#baixa-input-qtd').attr('step', '1').attr('placeholder', '0');

                    Utils.getModal('modalDarBaixa').show();
                    setTimeout(() => $('#baixa-input-qtd').focus(), 500);
                }});
            });

            $('#baixa-input-qtd').on('input', function() { FormHandler.recalcBaixa(); });
            
            // E. Exclusão de Item
            $(document).on('click', '.btn-excluir-item', function() { 
                const id = $(this).data('id'); $('#formConfirmacao').data('id', id).data('type', 'item').attr('action', `/estoque/ajax/item/${id}/deletar/`);
                $('#modalConfirmarTexto').text('Excluir item?'); Utils.getModal('modalConfirmarExclusao').show(); 
            });

            // Submit Confirmação (Genérico - Item ou Compra)
            $('#formConfirmacao').on('submit', function(e) { 
                e.preventDefault(); 
                
                const urlDestino = $(this).attr('action');
                const tipo = $(this).data('type');

                $.ajax({ 
                    type: 'POST', 
                    url: urlDestino, 
                    headers: {'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val()}, 
                    data: $(this).serialize(), 
                    success: (res) => { 
                        Utils.getModal('modalConfirmarExclusao').hide(); 
                        if(res.success) { 
                            Utils.showToast('Excluído com sucesso.'); 
                            if (tipo === 'compra') location.reload(); 
                            else TableManager.reloadPrincipal(); 
                        } else alert('Erro: ' + res.message); 
                    } 
                }); 
            });
        },

        recalcBaixa: function() {
            const inputEl = $('#baixa-input-qtd');
            let inputVal = parseFloat(inputEl.val()) || 0;
            const isDecimal = inputEl.data('is-decimal'); 

            if (!isDecimal && inputVal % 1 !== 0) { inputVal = Math.floor(inputVal); }

            const estoqueAtual = parseFloat($('#hidden-estoque-atual').val()) || 0;
            const btn = $('#btn-confirma-baixa');
            const msgErro = $('#msg-erro-baixa');
            const displayFinal = $('#baixa-display-final');
            const unidade = $('#baixa-span-unidade').text();

            const saldoFinal = estoqueAtual - inputVal;
            let txtFinal = isDecimal ? saldoFinal.toFixed(3).replace(/\.?0+$/, '') : Math.floor(saldoFinal);
            displayFinal.text(txtFinal + ' ' + unidade);

            if (inputVal <= 0) {
                btn.prop('disabled', true); msgErro.addClass('d-none');
                displayFinal.removeClass('text-danger').addClass('text-success');
            } else if (saldoFinal < 0) {
                btn.prop('disabled', true); msgErro.removeClass('d-none');
                displayFinal.removeClass('text-success').addClass('text-danger');
            } else {
                btn.prop('disabled', false); msgErro.addClass('d-none');
                displayFinal.removeClass('text-danger').addClass('text-success');
            }
        },

        adjustBaixa: function(valor) {
            const input = document.getElementById('baixa-input-qtd');
            let atual = parseFloat(input.value) || 0;
            let novo = atual + valor;
            if(novo < 0) novo = 0;
            input.value = novo;
            this.recalcBaixa(); 
        }
    };

    window.ajustarBaixa = function(v) { FormHandler.adjustBaixa(v); };

    // =========================================================================
    // 7. BOOT
    // =========================================================================
    try {
        TableManager.reloadPrincipal(); UIManager.updateButtons(); UIManager.loadOwnerOptions();
        
        // Ouvintes Universais (Atualizam Tabela E Histórico dependendo da aba ativa)
        $('#filtro-setor, #filtro-owner, #filtro-imovel-global').on('change', function() {
            const activeTab = $('.nav-link.active').attr('id');
            if (activeTab === 'historico-estoque-tab') TableManager.loadHistorico(true);
            else TableManager.reloadPrincipal();
            
            UIManager.updateButtons(); 
            if(this.id !== 'filtro-owner') UIManager.loadOwnerOptions(); // Recarrega o combo de cômodos se mudar setor/imovel
        });

        // Ouvintes Exclusivos do Histórico (Novos Filtros)
        $('#filtro-historico-acao, #filtro-historico-user').on('change', function() {
            TableManager.loadHistorico(true);
        });

        $('#filtro_data_estoque').on('change', function() { TableManager.reloadPrincipal(); });
        
        $('#btn-limpar-data-estoque').on('click', function() { $('#filtro_data_estoque').val(''); $('#filtro-setor').val('TODOS').trigger('change'); });
        
        $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function(e) {
            const novaAbaId = $(e.target).attr('id'); UIManager.updateButtons(novaAbaId);
            if (novaAbaId === 'geral-tab') TableManager.reloadPrincipal();
            else if (novaAbaId === 'historico-estoque-tab') TableManager.loadHistorico(true);
            else if (novaAbaId === 'simulacao-tab') TableManager.loadSimulacao();
            if (novaAbaId === 'compras-tab') TableManager.initCompras();
        });
        
        VisualLogic.bindCascades(); VisualLogic.bindSmartModal(); VisualLogic.bindRepositionHub(); 
        FormHandler.init(); window.ScannerManager.initInputListener(); PurchaseManager.init();
    } catch(e) { console.error("Erro no Boot:", e); }
});